"""
Screenshot and OCR tool — captures screen and/or extracts text via Vision OCR.

@status: active
@phase: 198
@depends: base_tool, subprocess, pathlib, os
@used_by: vetka_mcp_bridge (vetka_screenshot)
"""
import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from .base_tool import BaseMCPTool

logger = logging.getLogger("VETKA_MCP")

# Resolve project root (src/mcp/tools/ → 3 levels up)
_TOOL_DIR = Path(__file__).resolve().parents[3]
VISION_OCR_BIN = _TOOL_DIR / "scripts" / "vision_ocr"


class ScreenshotTool(BaseMCPTool):
    """Capture screen and/or OCR text from display. Non-interactive — for agent use."""

    @property
    def name(self) -> str:
        return "vetka_screenshot"

    @property
    def description(self) -> str:
        return (
            "Capture screen and/or OCR text from display. "
            "Non-interactive — for agent use. "
            "Returns OCR text and/or JPEG path."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["ocr", "jpeg", "both"],
                    "default": "both",
                    "description": "ocr=text only, jpeg=image only, both=text+image"
                },
                "region": {
                    "type": "string",
                    "enum": ["full", "active"],
                    "default": "full",
                    "description": "full=all screens, active=frontmost window"
                },
                "monitor": {
                    "type": "integer",
                    "description": "Specific display number (1, 2, ...) — screencapture -D flag"
                },
                "quality": {
                    "type": "integer",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "JPEG compression quality (1-100)"
                }
            },
            "required": []
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        mode = arguments.get("mode", "both")
        region = arguments.get("region", "full")
        monitor = arguments.get("monitor")
        quality = arguments.get("quality", 50)

        pid = os.getpid()
        ts = int(time.time())
        png_path = Path(f"/tmp/vetka_screenshot_{pid}_{ts}.png")
        jpg_path = Path(f"/tmp/vetka_screenshot_{pid}_{ts}.jpg")

        png_created = False
        jpg_created = False

        try:
            # ----------------------------------------------------------------
            # Step 1: Capture screenshot to PNG
            # ----------------------------------------------------------------
            capture_cmd = ["/usr/sbin/screencapture", "-x"]

            if region == "active":
                # Get frontmost window bounds via osascript
                script = (
                    'tell application "System Events" to tell (first process whose frontmost is true) '
                    'to tell front window to get {position, size}'
                )
                try:
                    bounds_result = subprocess.run(
                        ["/usr/bin/osascript", "-e", script],
                        capture_output=True, text=True, timeout=5
                    )
                    if bounds_result.returncode == 0:
                        # Parse output: "x, y, w, h" (may be split across "position" and "size")
                        raw = bounds_result.stdout.strip().replace("{", "").replace("}", "")
                        nums = [n.strip() for n in raw.split(",") if n.strip().lstrip("-").isdigit()]
                        if len(nums) >= 4:
                            x, y, w, h = nums[0], nums[1], nums[2], nums[3]
                            capture_cmd += ["-R", f"{x},{y},{w},{h}"]
                        # If parsing fails, fall through to full capture
                except Exception as e:
                    logger.debug(f"[ScreenshotTool] osascript bounds failed: {e}, falling back to full capture")

            if monitor is not None:
                capture_cmd += ["-D", str(monitor)]

            capture_cmd.append(str(png_path))

            capture_result = subprocess.run(
                capture_cmd,
                capture_output=True, text=True, timeout=10
            )
            if capture_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"screencapture failed: {capture_result.stderr or capture_result.stdout}",
                    "result": None
                }
            png_created = True

            # ----------------------------------------------------------------
            # Step 2: Convert PNG → JPEG (if needed)
            # ----------------------------------------------------------------
            image_path_for_ocr = str(png_path)
            result_image_path: Optional[str] = None
            result_image_kb: Optional[int] = None

            if mode in ("jpeg", "both"):
                sips_result = subprocess.run(
                    [
                        "/usr/bin/sips",
                        "-s", "format", "jpeg",
                        "-s", "formatOptions", str(quality),
                        str(png_path),
                        "--out", str(jpg_path)
                    ],
                    capture_output=True, text=True, timeout=15
                )
                if sips_result.returncode == 0 and jpg_path.exists():
                    jpg_created = True
                    result_image_path = str(jpg_path)
                    result_image_kb = jpg_path.stat().st_size // 1024
                    image_path_for_ocr = str(jpg_path)
                else:
                    logger.warning(f"[ScreenshotTool] sips conversion failed: {sips_result.stderr}")
                    # Fall back to PNG for OCR
                    image_path_for_ocr = str(png_path)

            # ----------------------------------------------------------------
            # Step 3: OCR (if needed)
            # ----------------------------------------------------------------
            ocr_text: Optional[str] = None

            if mode in ("ocr", "both"):
                if not VISION_OCR_BIN.exists():
                    return {
                        "success": False,
                        "error": f"vision_ocr binary not found at {VISION_OCR_BIN}",
                        "result": None
                    }
                ocr_result = subprocess.run(
                    [str(VISION_OCR_BIN), image_path_for_ocr],
                    capture_output=True, text=True, timeout=30
                )
                if ocr_result.returncode == 0:
                    ocr_text = ocr_result.stdout.strip()
                else:
                    logger.warning(f"[ScreenshotTool] OCR failed: {ocr_result.stderr}")
                    ocr_text = None

            # ----------------------------------------------------------------
            # Step 4: Cleanup
            # ----------------------------------------------------------------
            # Always delete temp PNG
            if png_created and png_path.exists():
                try:
                    png_path.unlink()
                except Exception:
                    pass

            # Delete JPEG if mode=ocr
            if mode == "ocr" and jpg_created and jpg_path.exists():
                try:
                    jpg_path.unlink()
                except Exception:
                    pass
                result_image_path = None
                result_image_kb = None

            # ----------------------------------------------------------------
            # Step 5: Build result
            # ----------------------------------------------------------------
            result: Dict[str, Any] = {
                "region": region,
                "mode": mode,
            }
            if ocr_text is not None:
                result["text"] = ocr_text
                result["char_count"] = len(ocr_text)
            if result_image_path is not None:
                result["image_path"] = result_image_path
                result["image_size_kb"] = result_image_kb

            return {"success": True, "result": result, "error": None}

        except subprocess.TimeoutExpired as e:
            return {"success": False, "error": f"Command timed out: {e}", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
        finally:
            # Ensure PNG is always cleaned up on any exception path
            if png_created and png_path.exists():
                try:
                    png_path.unlink()
                except Exception:
                    pass
