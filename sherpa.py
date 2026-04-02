#!/usr/bin/env python3
"""
SHERPA — Scout & Harvest Engine for Recon, Prep & Augmentation
Phase 202 | VETKA Project

Lightweight recon agent that enriches pending tasks with research
from free browser AI services. Does NOT write production code.

Usage:
    python sherpa.py --setup          # First run: log into services manually
    python sherpa.py                  # Run recon loop
    python sherpa.py --once           # Process one task and exit
    python sherpa.py --dry-run        # Show what would be processed
    python sherpa.py --service grok   # Use specific service only
"""

import asyncio
import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
RECON_DIR = PROJECT_ROOT / "docs" / "sherpa_recon"
CONFIG_PATH = PROJECT_ROOT / "config" / "sherpa.yaml"
LOG_DIR = PROJECT_ROOT / "logs"
PID_FILE = PROJECT_ROOT / "data" / "sherpa.pid"

RECON_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── PID Guard (only one Sherpa at a time) ──────────────────────────────
import os
import signal


def _is_pid_alive(pid: int) -> bool:
    """Check if process with given PID is still running."""
    try:
        os.kill(pid, 0)  # Signal 0 = check existence
        return True
    except (OSError, ProcessLookupError):
        return False


def acquire_guard() -> bool:
    """Acquire PID lock. Returns True if lock acquired, False if another Sherpa is running."""
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            if _is_pid_alive(old_pid):
                return False  # Another Sherpa is running
            # Stale PID file — process died without cleanup
        except (ValueError, OSError):
            pass  # Corrupted PID file — overwrite

    PID_FILE.write_text(str(os.getpid()))
    return True


def release_guard():
    """Release PID lock."""
    try:
        if PID_FILE.exists():
            stored_pid = int(PID_FILE.read_text().strip())
            if stored_pid == os.getpid():
                PID_FILE.unlink()
    except (ValueError, OSError):
        pass

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] sherpa: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "sherpa.log"),
    ],
)
log = logging.getLogger("sherpa")


# ── Feedback Collector (MARKER_202.FEEDBACK) ──────────────────────────
FEEDBACK_FILE = PROJECT_ROOT / "data" / "sherpa_feedback.jsonl"
FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)


class FeedbackCollector:
    """Auto-collect per-task feedback to JSONL. Scores services from history."""

    def __init__(self):
        self.session_start = datetime.now().isoformat()
        self.session_entries: list = []
        self._scores: dict = {}

    def load_scores(self) -> dict:
        """Read last 50 entries, calculate per-service reliability scores."""
        entries = []
        if FEEDBACK_FILE.exists():
            try:
                lines = FEEDBACK_FILE.read_text().strip().split("\n")
                for line in lines[-50:]:
                    if line.strip():
                        entries.append(json.loads(line))
            except (json.JSONDecodeError, OSError):
                pass

        svc_stats: dict = {}
        for entry in entries:
            if entry.get("type") == "session_summary":
                continue
            svc = entry.get("service", "")
            if not svc:
                continue
            if svc not in svc_stats:
                svc_stats[svc] = {"total": 0, "success": 0, "total_chars": 0}
            svc_stats[svc]["total"] += 1
            if entry.get("success"):
                svc_stats[svc]["success"] += 1
                svc_stats[svc]["total_chars"] += entry.get("response_chars", 0)

        self._scores = {}
        for svc, s in svc_stats.items():
            if s["total"] > 0:
                rel = s["success"] / s["total"]
                avg_c = s["total_chars"] / max(s["success"], 1)
                self._scores[svc] = round(0.7 * rel + 0.3 * min(avg_c / 3000, 1.0), 3)
        return self._scores

    def get_service_ranking(self) -> list:
        return sorted(self._scores.items(), key=lambda x: x[1], reverse=True)

    def log_task(self, task_id: str, service: str, response_chars: int,
                 time_seconds: float, success: bool, error_type: str = "") -> None:
        entry = {
            "ts": datetime.now().isoformat(), "task_id": task_id, "service": service,
            "response_chars": response_chars, "time_seconds": round(time_seconds, 1),
            "success": success, "error_type": error_type,
        }
        self.session_entries.append(entry)
        try:
            with open(FEEDBACK_FILE, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def save_session_summary(self) -> None:
        if not self.session_entries:
            return
        total = len(self.session_entries)
        successes = sum(1 for e in self.session_entries if e.get("success"))
        summary = {
            "ts": datetime.now().isoformat(), "type": "session_summary",
            "session_start": self.session_start, "tasks_total": total,
            "tasks_success": successes, "tasks_failed": total - successes,
            "services_used": list(set(e.get("service", "") for e in self.session_entries)),
        }
        try:
            with open(FEEDBACK_FILE, "a") as f:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
            log.info(f"Session summary: {successes}/{total} successful")
        except OSError:
            pass


# ── Service Protocols (MARKER_202.PROTOCOLS) ──────────────────────────
PROTOCOLS_DIR = PROJECT_ROOT / "data" / "sherpa_protocols"
PROTOCOLS_DIR.mkdir(parents=True, exist_ok=True)

CONSECUTIVE_FAILURES_DISABLE = 3


class ServiceProtocol:
    """Auto-generated per-service protocol from feedback. Self-healing."""

    @staticmethod
    def generate_all() -> dict:
        """Read feedback, generate protocol YAML per service."""
        if not FEEDBACK_FILE.exists():
            return {}
        entries: dict = {}
        try:
            for line in FEEDBACK_FILE.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get("type") == "session_summary":
                    continue
                svc = entry.get("service", "")
                if svc:
                    entries.setdefault(svc, []).append(entry)
        except (json.JSONDecodeError, OSError):
            return {}

        protocols = {}
        for svc_name, svc_entries in entries.items():
            if len(svc_entries) < 5:
                continue
            successes = [e for e in svc_entries if e.get("success")]
            failures = [e for e in svc_entries if not e.get("success")]
            total = len(svc_entries)
            times = [e.get("time_seconds", 0) for e in successes if e.get("time_seconds")]
            avg_time = round(sum(times) / len(times), 1) if times else 0
            chars = [e.get("response_chars", 0) for e in successes]
            avg_chars = round(sum(chars) / len(chars)) if chars else 0
            error_types = {}
            for e in failures:
                et = e.get("error_type", "unknown")
                error_types[et] = error_types.get(et, 0) + 1
            recent = svc_entries[-CONSECUTIVE_FAILURES_DISABLE:]
            consecutive_fails = sum(1 for e in reversed(recent) if not e.get("success"))
            auto_disabled = consecutive_fails >= CONSECUTIVE_FAILURES_DISABLE
            protocol = {
                "service": svc_name, "generated_at": datetime.now().isoformat(),
                "interactions": total, "reliability_score": round(len(successes) / total, 3),
                "avg_response_time_s": avg_time, "avg_response_chars": avg_chars,
                "auto_disabled": auto_disabled,
                "disable_reason": f"{consecutive_fails} consecutive failures" if auto_disabled else None,
                "common_errors": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)),
            }
            try:
                with open(PROTOCOLS_DIR / f"{svc_name}.yaml", "w") as f:
                    yaml.dump(protocol, f, default_flow_style=False, allow_unicode=True)
                protocols[svc_name] = protocol
            except OSError:
                pass
        return protocols

    @staticmethod
    def is_service_disabled(service_name: str) -> bool:
        proto_path = PROTOCOLS_DIR / f"{service_name}.yaml"
        if not proto_path.exists():
            return False
        try:
            with open(proto_path) as f:
                return (yaml.safe_load(f) or {}).get("auto_disabled", False)
        except (yaml.YAMLError, OSError):
            return False


# ── Config ─────────────────────────────────────────────────────────────
@dataclass
class ServiceConfig:
    name: str
    url: str
    profile_dir: str
    input_selector: str = "textarea"
    send_selector: str = 'button[type="submit"], button:has-text("Send")'
    response_selector: str = "[data-message-author-role='assistant'], .response, .message"
    cooldown_seconds: int = 120
    enabled: bool = True


@dataclass
class SherpaConfig:
    taskboard_url: str = "http://localhost:5000"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:latest"
    services: List[ServiceConfig] = field(default_factory=list)
    agent_name: str = "sherpa"
    agent_type: str = "mycelium"
    headless: bool = True
    cooldown_between_tasks: int = 120
    max_tasks_per_run: int = 50
    phase_types: List[str] = field(default_factory=lambda: ["research"])

    @classmethod
    def load(cls, path: Path) -> "SherpaConfig":
        if not path.exists():
            log.warning(f"Config not found at {path}, using defaults")
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        services = [ServiceConfig(**s) for s in data.get("services", [])]
        cfg = cls(
            taskboard_url=data.get("taskboard_url", cls.taskboard_url),
            ollama_url=data.get("ollama_url", cls.ollama_url),
            ollama_model=data.get("ollama_model", cls.ollama_model),
            services=services,
            agent_name=data.get("agent_name", cls.agent_name),
            agent_type=data.get("agent_type", cls.agent_type),
            headless=data.get("headless", cls.headless),
            cooldown_between_tasks=data.get("cooldown_between_tasks", 120),
            max_tasks_per_run=data.get("max_tasks_per_run", 50),
            phase_types=data.get("phase_types", ["research"]),
        )
        return cfg


# ── TaskBoard Client ───────────────────────────────────────────────────
class TaskBoardClient:
    """HTTP client for VETKA TaskBoard API."""

    def __init__(self, base_url: str, agent_name: str, agent_type: str):
        self.base = base_url.rstrip("/")
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.http = httpx.AsyncClient(timeout=30.0)

    async def get_pending_tasks(self, limit: int = 20) -> List[Dict]:
        """Get pending tasks list."""
        resp = await self.http.get(
            f"{self.base}/api/tasks",
            params={"status": "pending", "limit": limit},
        )
        if resp.status_code == 200:
            data = resp.json()
            tasks = data.get("tasks", []) if isinstance(data, dict) else data
            return tasks if isinstance(tasks, list) else []
        log.warning(f"list pending failed: {resp.status_code}")
        return []

    async def claim_task(self, task_id: str) -> Optional[Dict]:
        """Claim a specific task by ID."""
        body = {"agent_name": self.agent_name, "agent_type": self.agent_type}
        resp = await self.http.post(f"{self.base}/api/tasks/{task_id}/claim", json=body)
        if resp.status_code == 200:
            return resp.json()
        log.warning(f"claim {task_id} failed: {resp.status_code}")
        return None

    async def get_task(self, task_id: str) -> Optional[Dict]:
        """Get full task details."""
        resp = await self.http.get(f"{self.base}/api/tasks/{task_id}")
        if resp.status_code == 200:
            return resp.json()
        return None

    async def update_task(self, task_id: str, updates: Dict) -> bool:
        """Update task fields (recon_docs, implementation_hints, etc.)."""
        resp = await self.http.patch(f"{self.base}/api/tasks/{task_id}", json=updates)
        return resp.status_code == 200

    async def release_task(self, task_id: str, reason: str = "Sherpa recon complete") -> bool:
        """Release task back to pending (cancel claim without cancelling task)."""
        resp = await self.http.post(
            f"{self.base}/api/tasks/{task_id}/cancel", json={"reason": reason}
        )
        return resp.status_code == 200

    async def set_sherpa_status(self, status: str, tasks_enriched: int = 0) -> bool:
        """MARKER_202.SHERPA_SIGNAL: Update Sherpa status in TaskBoard settings.

        Uses PATCH /api/debug/task-board/settings (the actual endpoint).
        Non-fatal — logs warning on failure, never blocks.
        """
        try:
            resp = await self.http.patch(
                f"{self.base}/api/debug/task-board/settings",
                json={"sherpa_status": status, "sherpa_tasks_enriched": tasks_enriched},
            )
            if resp.status_code != 200:
                log.debug(f"sherpa_status update returned {resp.status_code} (non-fatal)")
            return resp.status_code == 200
        except Exception as e:
            log.debug(f"sherpa_status update failed (non-fatal): {e}")
            return False

    async def notify_commanders(self, message: str) -> None:
        """MARKER_202.SHERPA_SIGNAL: Notify via task update (implementation_hints append).

        No generic /api/taskboard/action endpoint exists. Instead, log to sherpa.log
        and update status — Commanders check sherpa_status via settings endpoint.
        """
        log.info(f"[SIGNAL] {message}")

    async def close(self):
        await self.http.aclose()


# ── Codebase Search ────────────────────────────────────────────────────
def search_codebase(query: str, allowed_paths: List[str] = None, limit: int = 10) -> List[Dict[str, str]]:
    """Search codebase using ripgrep. Returns list of {path, line, content}."""
    results = []
    search_dirs = []

    if allowed_paths:
        for p in allowed_paths:
            full = PROJECT_ROOT / p
            if full.exists():
                search_dirs.append(str(full))
    if not search_dirs:
        search_dirs = [
            str(PROJECT_ROOT / "src"),
            str(PROJECT_ROOT / "client" / "src"),
        ]

    # Split query into keywords, search for each
    keywords = query.split()[:3]  # Max 3 keywords
    for kw in keywords:
        if len(kw) < 3:
            continue
        for search_dir in search_dirs:
            try:
                proc = subprocess.run(
                    ["rg", "-l", "-i", "--max-count", "3", kw, search_dir],
                    capture_output=True, text=True, timeout=10,
                )
                for line in proc.stdout.strip().split("\n"):
                    if line and line not in [r["path"] for r in results]:
                        results.append({"path": line, "keyword": kw})
                        if len(results) >= limit:
                            return results
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
    return results


def read_file_snippet(filepath: str, max_lines: int = 50) -> str:
    """Read first N lines of a file."""
    try:
        p = Path(filepath)
        if not p.exists() or p.stat().st_size > 500_000:  # Skip >500KB
            return ""
        lines = p.read_text(errors="replace").split("\n")[:max_lines]
        return "\n".join(lines)
    except Exception:
        return ""


# ── Ollama Client ──────────────────────────────────────────────────────
class OllamaClient:
    """Call local Ollama model for prompt building / response parsing."""

    def __init__(self, base_url: str, model: str):
        self.base = base_url.rstrip("/")
        self.model = model
        self.http = httpx.AsyncClient(timeout=120.0)

    async def chat(self, prompt: str, max_tokens: int = 2048) -> str:
        """Send prompt to local model, get response."""
        try:
            resp = await self.http.post(
                f"{self.base}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": max_tokens},
                },
            )
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content", "")
            log.warning(f"Ollama error: {resp.status_code}")
            return ""
        except Exception as e:
            log.warning(f"Ollama unavailable: {e}")
            return ""

    async def is_available(self) -> bool:
        try:
            resp = await self.http.get(f"{self.base}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.http.aclose()


# ── Sherpa Harness (MARKER_202.HARNESS) ──────────────────────────────
class SherpaHarness:
    """Qwen-powered guard/reflex/memory for intelligent task processing.

    MARKER_202.HARNESS: Makes Sherpa a first-class agent with:
    - Guard: validate task quality before sending to browser AI
    - Reflex: skip known-bad patterns instantly (no LLM call)
    - Memory: read protocols + feedback for service selection
    """

    # Reflex patterns — instant skip, no LLM needed
    SKIP_PATTERNS = [
        "DEBRIEF-IDEA",       # Ideas, not real tasks
        "DEBRIEF-BUG",        # Bug reports, not actionable tasks
        "[AUTO]",             # Auto-decomposed children (handled by local_loop)
        "ETA-IDEA",           # Agent ideas
        "COMMANDER-IDEA",     # Commander ideas
    ]

    # Minimum requirements for a recon-worthy task
    MIN_DESC_LENGTH = 30
    MIN_TITLE_LENGTH = 10

    def __init__(self, ollama: 'OllamaClient', feedback: 'FeedbackCollector'):
        self.ollama = ollama
        self.feedback = feedback
        self._guard_rejects = 0
        self._reflex_skips = 0

    def reflex_check(self, task: dict) -> tuple[bool, str]:
        """Fast pattern matching — skip known-bad tasks instantly.

        Returns: (should_skip, reason)
        """
        title = task.get("title", "")
        tags = task.get("tags", [])

        # Skip pattern match
        for pattern in self.SKIP_PATTERNS:
            if pattern in title:
                self._reflex_skips += 1
                return True, f"reflex:title_pattern:{pattern}"

        # Note: recon_docs check removed — recon_done status handles this
        # Tasks with partial recon should be re-enriched

        # Skip auto-decomposed tasks
        if "auto-decomposed" in tags:
            self._reflex_skips += 1
            return True, "reflex:auto-decomposed"

        return False, ""

    def guard_check(self, task: dict) -> tuple[bool, str]:
        """Validate task quality — is it worth sending to browser AI?

        Returns: (is_valid, reason_if_invalid)
        """
        title = task.get("title", "")
        desc = task.get("description", "") or ""

        # Empty/short description
        if len(desc.strip()) < self.MIN_DESC_LENGTH:
            self._guard_rejects += 1
            return False, f"guard:desc_too_short ({len(desc.strip())} chars)"

        # Empty title
        if len(title.strip()) < self.MIN_TITLE_LENGTH:
            self._guard_rejects += 1
            return False, f"guard:title_too_short ({len(title.strip())} chars)"

        # Check allowed_paths exist on disk
        paths = task.get("allowed_paths", [])
        if paths:
            existing = sum(1 for p in paths if (PROJECT_ROOT / p).exists())
            if existing == 0 and len(paths) > 0:
                self._guard_rejects += 1
                return False, f"guard:no_valid_paths (0/{len(paths)} exist)"

        return True, ""

    def select_service(self, services: list, task: dict) -> 'ServiceConfig':
        """Intelligent service selection based on feedback scores and protocols.

        Uses feedback reliability scores to pick the best available service.
        Falls back to round-robin if no scores available.
        """
        scores = self.feedback._scores
        if not scores:
            return services[0]  # No history — use first

        # Score each available service
        ranked = []
        for svc in services:
            score = scores.get(svc.name, 0.5)  # Default 0.5 for unknown
            # Boost score for services not auto-disabled
            if not ServiceProtocol.is_service_disabled(svc.name):
                ranked.append((svc, score))

        if not ranked:
            return services[0]

        # Sort by score descending, pick best
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[0][0]

    def get_stats(self) -> dict:
        return {
            "guard_rejects": self._guard_rejects,
            "reflex_skips": self._reflex_skips,
        }


# ── Browser Client (Playwright) ───────────────────────────────────────
class BrowserClient:
    """Playwright-based browser for AI service interaction."""

    def __init__(self, services: List[ServiceConfig], headless: bool = True):
        self.services = {s.name: s for s in services}
        self.headless = headless
        self._pw = None
        self._browser = None
        self._contexts: Dict[str, Any] = {}  # service_name -> context
        self._pages: Dict[str, Any] = {}  # service_name -> page

    async def start(self):
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        log.info(f"Browser started (headless={self.headless})")

    async def stop(self):
        for ctx in self._contexts.values():
            try:
                await ctx.close()
            except Exception:
                pass
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        log.info("Browser stopped")

    async def _get_page(self, service_name: str) -> Any:
        """Get or create a persistent page for a service."""
        if service_name in self._pages:
            page = self._pages[service_name]
            if not page.is_closed():
                return page

        svc = self.services.get(service_name)
        if not svc:
            raise ValueError(f"Unknown service: {service_name}")

        profile_path = str(PROJECT_ROOT / svc.profile_dir)
        Path(profile_path).mkdir(parents=True, exist_ok=True)

        ctx = await self._browser.new_context(
            storage_state=self._load_storage_state(profile_path),
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            permissions=["clipboard-read", "clipboard-write"],  # No popup for clipboard
        )
        page = await ctx.new_page()
        self._contexts[service_name] = ctx
        self._pages[service_name] = page
        return page

    def _load_storage_state(self, profile_dir: str) -> Optional[str]:
        """Load saved browser state (cookies, localStorage)."""
        state_file = Path(profile_dir) / "state.json"
        if state_file.exists():
            return str(state_file)
        return None

    async def _save_storage_state(self, service_name: str):
        """Save browser state for next session."""
        svc = self.services.get(service_name)
        ctx = self._contexts.get(service_name)
        if svc and ctx:
            profile_path = PROJECT_ROOT / svc.profile_dir
            profile_path.mkdir(parents=True, exist_ok=True)
            state_file = profile_path / "state.json"
            await ctx.storage_state(path=str(state_file))
            log.info(f"Saved session: {service_name}")

    async def send_prompt(self, service_name: str, prompt: str, timeout_ms: int = 180_000) -> str:
        """Send text prompt to AI service. Simple: fill textarea, press Enter."""
        svc = self.services[service_name]
        page = await self._get_page(service_name)

        # Navigate to a NEW chat
        log.info(f"Navigating to {svc.url}")
        await page.goto(svc.url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(3000)

        # Dismiss popups
        await self._dismiss_popups(page)

        # Snapshot page BEFORE (to filter sidebar from response)
        pre_send_text = await self._get_all_text(page)

        # Find textarea
        input_el = await self._find_input(page, svc)
        if not input_el:
            log.error(f"Cannot find input on {service_name}")
            return ""

        # Click and type
        await input_el.click()
        await page.wait_for_timeout(500)

        # fill() for bulk + type() last chars to trigger React
        log.info(f"Typing prompt ({len(prompt)} chars)...")
        if len(prompt) <= 300:
            await input_el.type(prompt, delay=5)
        else:
            await input_el.fill(prompt[:-30])
            await page.wait_for_timeout(300)
            await input_el.press("End")
            await input_el.type(prompt[-30:], delay=5)
        await page.wait_for_timeout(500)

        # Send: Enter key (works without file attachments)
        log.info("Pressing Enter to send...")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)

        # Wait for response
        log.info("Waiting for AI response...")
        response = await self._wait_and_extract(page, svc, timeout_ms, prompt_text=prompt, pre_text=pre_send_text)

        await self._save_storage_state(service_name)
        return response

    async def _check_message_sent(self, input_el) -> bool:
        """Check if message was sent by verifying textarea is empty."""
        try:
            val = await input_el.input_value()
            return len(val) < 10  # Textarea cleared = sent
        except Exception:
            try:
                val = await input_el.inner_text()
                return len(val) < 10
            except Exception:
                return False  # Can't verify

    async def _js_click_send(self, page) -> bool:
        """Find and click the SEND button (not attach/paperclip) via JS."""
        try:
            clicked = await page.evaluate("""() => {
                const textarea = document.querySelector('textarea, div[contenteditable="true"]');
                if (!textarea) return false;

                // Collect all icon buttons near textarea
                let candidates = [];
                let parent = textarea.parentElement;
                for (let i = 0; i < 5 && parent; i++) {
                    const buttons = parent.querySelectorAll('button, [role="button"]');
                    for (const btn of buttons) {
                        const text = (btn.textContent || '').trim();
                        // Skip labeled buttons (DeepThink, Search, Copy, etc)
                        if (text && text.length > 3) continue;

                        const style = window.getComputedStyle(btn);
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        if (btn.disabled) continue;

                        // Skip attach/upload buttons:
                        // - Has nearby input[type=file]
                        // - Has aria-label with attach/upload/file
                        // - Has paperclip-like class
                        const label = (btn.getAttribute('aria-label') || '').toLowerCase();
                        if (label.includes('attach') || label.includes('upload') || label.includes('file')
                            || label.includes('clip') || label.includes('добавить файл')) continue;
                        const cls = (btn.className || '').toLowerCase();
                        if (cls.includes('attach') || cls.includes('upload') || cls.includes('clip')) continue;
                        // Check if there's an input[type=file] as sibling/child
                        if (btn.querySelector('input[type="file"]')) continue;
                        const nextSib = btn.nextElementSibling;
                        if (nextSib && nextSib.tagName === 'INPUT' && nextSib.type === 'file') continue;

                        if (btn.querySelector('svg')) {
                            candidates.push(btn);
                        }
                    }
                    parent = parent.parentElement;
                }

                // Pick the LAST candidate (send button is usually rightmost/last)
                if (candidates.length > 0) {
                    const sendBtn = candidates[candidates.length - 1];
                    sendBtn.click();
                    return true;
                }
                return false;
            }""")
            if clicked:
                log.info("Sent via JS click")
            return clicked
        except Exception:
            return False

    async def _find_input(self, page, svc: ServiceConfig) -> Optional[Any]:
        """Find the message input field."""
        selectors = [
            svc.input_selector,
            "textarea",
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="Message"]',
            'div[contenteditable="true"]',
            '[role="textbox"]',
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    return el
            except Exception:
                continue
        return None

    async def _click_send(self, page, svc: ServiceConfig) -> bool:
        """Click the send button. Tries multiple strategies."""
        selectors = [
            svc.send_selector,
            'button[aria-label*="Send"]',
            'button[aria-label*="send"]',
            'button[aria-label*="Отправ"]',
            'button[data-testid*="send"]',
            'button:has(svg[data-icon="send"])',
            'button[type="submit"]',
            # DeepSeek — send is a div with role="button" or just a clickable div with SVG
            'div[role="button"]:near(textarea)',
            # Generic: any button/div near textarea with an SVG (icon button)
            '#chat-input ~ button',
            '#chat-input + div button',
            'textarea ~ button',
            'textarea ~ div button',
            # Broad: last interactive element near input area
            '.chat-input-actions button',
            '[class*="send" i]',
            '[class*="Send"]',
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    return True
            except Exception:
                continue
        return False

    async def _upload_files(self, page, file_paths: List[str]) -> int:
        """Upload files as attachments via file input or attach button.

        Strategy:
        1. Find hidden <input type="file"> and use set_input_files (most reliable)
        2. If not found, click attach button and use file chooser event
        3. Upload files one by one (some services don't support multi-select)

        Returns number of successfully uploaded files.
        """
        uploaded = 0
        valid_files = [f for f in file_paths if Path(f).exists() and Path(f).stat().st_size < 5_000_000]

        if not valid_files:
            return 0

        # Strategy 1: Direct file input (works on most services)
        file_input_selectors = [
            'input[type="file"]',
            'input[accept*="."]',
            'input[accept*="text"]',
            'input[accept*="application"]',
        ]
        for sel in file_input_selectors:
            try:
                file_input = page.locator(sel).first
                # File inputs are often hidden, but set_input_files works anyway
                await file_input.set_input_files(valid_files)
                uploaded = len(valid_files)
                log.info(f"Uploaded {uploaded} files via {sel}")
                return uploaded
            except Exception:
                continue

        # Strategy 2: Click attach button → intercept file chooser
        attach_selectors = [
            'button[aria-label*="ttach"]',
            'button[aria-label*="pload"]',
            'button[aria-label*="ile"]',
            'button[aria-label*="Add"]',
            '[data-testid*="attach"]',
            '[data-testid*="upload"]',
            '[data-testid*="file"]',
            'label[for*="file"]',
            'button:has(svg path[d*="M"])',  # Generic icon button (paperclip, +)
        ]
        for sel in attach_selectors:
            try:
                btn = page.locator(sel).first
                if not await btn.is_visible(timeout=1000):
                    continue

                # Listen for file chooser event, then click
                async with page.expect_file_chooser(timeout=5000) as fc_info:
                    await btn.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(valid_files)
                uploaded = len(valid_files)
                log.info(f"Uploaded {uploaded} files via file chooser ({sel})")
                return uploaded
            except Exception:
                continue

        log.warning("Could not find file upload mechanism on this page")
        return 0

    async def _wait_for_uploads_complete(self, page, timeout_s: int = 300):
        """Wait until file uploads finish. Checks if Send button is enabled.

        Simple and reliable: if Send button is visible + not disabled → files are ready.
        Falls back to progressbar check only as secondary signal.
        """
        log.info("Waiting for file uploads to complete...")
        start = time.time()
        stable_count = 0

        while time.time() - start < timeout_s:
            # Primary check: is ANY clickable button near textarea enabled?
            send_ready = await self._is_send_button_ready(page)
            if send_ready:
                stable_count += 1
                if stable_count >= 2:  # Stable for 2 checks
                    log.info(f"Files ready (send button enabled, {int(time.time()-start)}s)")
                    return
            else:
                stable_count = 0
                elapsed = int(time.time() - start)
                if elapsed % 10 == 0:
                    log.info(f"Files still uploading... ({elapsed}s)")

            await page.wait_for_timeout(2000)

        log.warning(f"Upload wait timeout ({timeout_s}s) — proceeding anyway")

    async def _is_send_button_ready(self, page) -> bool:
        """Check if the send/submit button exists and is not disabled."""
        # Look for any visible, non-disabled button that could be "Send"
        try:
            # Use JS to find the send button reliably
            result = await page.evaluate("""() => {
                // Strategy 1: Find buttons/divs with send-like attributes
                const candidates = [
                    ...document.querySelectorAll('button[aria-label*="Send" i]'),
                    ...document.querySelectorAll('button[aria-label*="send" i]'),
                    ...document.querySelectorAll('button[data-testid*="send" i]'),
                    ...document.querySelectorAll('button[type="submit"]'),
                    ...document.querySelectorAll('[role="button"][aria-label*="send" i]'),
                ];

                // Strategy 2: Find the SVG arrow button near textarea (common pattern)
                if (candidates.length === 0) {
                    const textarea = document.querySelector('textarea');
                    if (textarea) {
                        // Look in parent containers for buttons
                        let parent = textarea.parentElement;
                        for (let i = 0; i < 5 && parent; i++) {
                            const buttons = parent.querySelectorAll('button, [role="button"], div[class*="btn"]');
                            for (const btn of buttons) {
                                // Skip if it's DeepThink or Search
                                const text = btn.textContent || '';
                                if (text.includes('DeepThink') || text.includes('Search')) continue;
                                // Has SVG (icon button) or is near end of container
                                if (btn.querySelector('svg') || btn.querySelector('img')) {
                                    candidates.push(btn);
                                }
                            }
                            parent = parent.parentElement;
                        }
                    }
                }

                for (const btn of candidates) {
                    const style = window.getComputedStyle(btn);
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    if (btn.disabled) return false;  // Found but disabled = still uploading
                    if (btn.getAttribute('aria-disabled') === 'true') return false;
                    if (btn.classList.contains('disabled')) return false;
                    // Found visible, enabled send button
                    return true;
                }
                return false;  // No send button found
            }""")
            return result
        except Exception:
            return False

    async def _dismiss_popups(self, page):
        """Try to close common popups."""
        dismiss_selectors = [
            'button:has-text("No thanks")',
            'button:has-text("Maybe later")',
            'button:has-text("Dismiss")',
            'button:has-text("Close")',
            'button:has-text("Got it")',
            'button:has-text("Accept")',
            'button:has-text("Decline")',
            'button[aria-label="Close"]',
            'button[aria-label="Dismiss"]',
            ".modal-close",
            '[data-testid="close-button"]',
        ]
        for sel in dismiss_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=500):
                    await btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                continue

    async def _get_all_text(self, page) -> str:
        """Get all visible text on the page (for diffing before/after)."""
        try:
            return await page.locator("body").inner_text(timeout=5000)
        except Exception:
            return ""

    async def _is_ai_streaming(self, page) -> bool:
        """Check if the AI is still generating a response.

        Looks for streaming indicators in the DOM:
        - Typing cursors / blinking carets
        - Loading spinners
        - "Thinking" / "Generating" labels
        - Stop/Cancel buttons (visible = still generating)
        - Streaming attributes on response elements
        """
        streaming_selectors = [
            # Stop/Cancel button (visible = AI is generating)
            'button:has-text("Stop")',
            'button:has-text("stop")',
            'button[aria-label*="Stop"]',
            'button[aria-label*="Cancel"]',
            'button:has-text("Остановить")',
            # Thinking/loading indicators
            '[class*="thinking" i]',
            '[class*="generating" i]',
            '[class*="streaming" i]',
            '[class*="typing" i]',
            '[data-is-streaming="true"]',
            # Animated elements (spinners, pulsing dots)
            '[class*="loading" i]:not([class*="file"])',
            '[class*="spinner" i]',
            '.animate-pulse',
            '[class*="dot-flashing"]',
            # DeepSeek specific
            '[class*="is-receiving"]',
            # Cursor/caret in response
            '.blinking-cursor',
            '[class*="cursor" i][class*="blink" i]',
        ]
        for sel in streaming_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=300):
                    return True
            except Exception:
                continue
        return False

    async def _wait_and_extract(self, page, svc: ServiceConfig, timeout_ms: int,
                                 prompt_text: str = "", pre_text: str = "") -> str:
        """Wait for AI response to complete, then extract text.

        Adaptive waiting — watches real DOM state:
        1. Wait for FIRST content to appear (something is being generated)
        2. Wait for streaming to STOP (Stop button disappears, no spinners)
        3. Extract final response text
        No hardcoded waits for specific durations.
        """
        log.info("Waiting for response...")
        start = time.time()
        max_wait = timeout_ms / 1000

        # Phase 1: Wait for generation to START (max 30s)
        generation_started = False
        while time.time() - start < min(30, max_wait):
            if await self._is_ai_streaming(page):
                generation_started = True
                log.info("AI is generating...")
                break
            # Also check if response text appeared without streaming indicator
            text = await self._extract_response_text(page, prompt_text, pre_text)
            if text and len(text) > 50:
                generation_started = True
                log.info("Response text detected")
                break
            await page.wait_for_timeout(2000)

        if not generation_started:
            log.warning("No generation detected after 30s — message may not have been sent")
            # Try to extract whatever is on the page anyway
            text = await self._extract_response_text(page, prompt_text, pre_text)
            if text and len(text) > 100:
                return text
            return ""

        # Phase 2: Wait for generation to FINISH
        # Use LIGHTWEIGHT DOM length check — no Copy clicks, no scrolling
        prev_len = 0
        stable_count = 0
        while time.time() - start < max_wait:
            streaming = await self._is_ai_streaming(page)
            # Lightweight: just measure DOM text length, don't extract fully
            curr_len = await self._measure_response_length(page)
            elapsed = int(time.time() - start)

            if streaming:
                stable_count = 0
                if elapsed % 15 == 0:
                    log.info(f"AI still generating... ({curr_len} chars, {elapsed}s)")
            else:
                if curr_len != prev_len:
                    stable_count = 0
                    if elapsed % 10 == 0 and curr_len > 0:
                        log.info(f"Response growing... ({curr_len} chars, {elapsed}s)")
                else:
                    stable_count += 1

                MIN_COMPLETE = 5000  # Don't declare complete under 5K chars

                # COMPLETE = text stopped growing + above minimum
                copy_visible = await self._is_copy_button_visible(page)
                if copy_visible and stable_count >= 3 and curr_len >= MIN_COMPLETE:
                    log.info(f"Response complete ({curr_len} chars, {elapsed}s). Extracting...")
                    break

                # Below minimum but stable — keep waiting, AI might resume
                if copy_visible and stable_count >= 3 and curr_len < MIN_COMPLETE:
                    if stable_count <= 6:  # Wait up to 18s extra for short responses
                        log.info(f"Response short ({curr_len} chars < {MIN_COMPLETE}), waiting for more...")
                    else:
                        log.info(f"Response stuck at {curr_len} chars. Extracting what we have...")
                        break

                # Fallback: no copy button but very stable (7 checks = 21s) + above minimum
                if stable_count >= 7 and curr_len >= MIN_COMPLETE:
                    log.info(f"Response stable without Copy ({curr_len} chars, {elapsed}s). Extracting...")
                    break

                # Very long stable without copy and under minimum — give up after 10 checks (30s)
                if stable_count >= 10 and curr_len > 500:
                    log.info(f"Response stuck at {curr_len} chars after {stable_count} checks. Extracting...")
                    break

            prev_len = curr_len
            await page.wait_for_timeout(3000)

        # Phase 3: ONE full extraction with all strategies
        text = await self._extract_response_text(page, prompt_text, pre_text)
        if text and len(text) > 100:
            elapsed = int(time.time() - start)
            log.info(f"Extracted {len(text)} chars in {elapsed}s")
            return text
        log.error("Extraction failed after response stabilized")
        return ""

    async def _measure_response_length(self, page) -> int:
        """Lightweight DOM length check — no clicks, no scrolling."""
        selectors = [".ds-markdown", ".markdown-body", ".message-content",
                     ".assistant-message", ".prose", "article"]
        for sel in selectors:
            try:
                el = page.locator(sel).last
                if await el.is_visible(timeout=500):
                    text = await el.inner_text(timeout=2000)
                    if text and len(text) > 20:
                        return len(text.strip())
            except Exception:
                continue
        return 0

    async def _is_copy_button_visible(self, page) -> bool:
        """Check if a Copy button is visible — means response is COMPLETE."""
        copy_selectors = [
            'button[aria-label*="Copy" i]',
            'button[data-testid*="copy" i]',
            'button[title*="Copy" i]',
            'button:has-text("Copy")',
            '.copy-btn',
            '[class*="copy" i]:not([class*="copyright"])',
        ]
        for sel in copy_selectors:
            try:
                el = page.locator(sel).last  # Last = for latest response
                if await el.is_visible(timeout=500):
                    return True
            except Exception:
                continue
        return False

    async def _click_copy_button(self, page) -> str:
        """Strategy 0: Click the Copy button and read clipboard.

        Most AI chat services have a copy button under each response.
        This is the most reliable extraction — service formats the
        markdown itself, we just read clipboard.
        """
        copy_selectors = [
            # Common copy button patterns
            'button[aria-label*="Copy"]',
            'button[aria-label*="copy"]',
            'button[data-testid*="copy"]',
            'button[title*="Copy"]',
            'button[title*="copy"]',
            # DeepSeek
            'div.ds-flex button:has(svg)',
            # Grok
            'button:has-text("Copy")',
            # ChatGPT
            'button[data-testid="copy-turn-action-button"]',
            # Claude.ai
            'button[aria-label="Copy Response"]',
            # Kimi
            'button.copy-btn',
            # Generic icon buttons near response
            '[class*="copy"]',
            '[class*="Copy"]',
        ]

        # Find the LAST copy button (for the latest response)
        for sel in copy_selectors:
            try:
                buttons = page.locator(sel)
                count = await buttons.count()
                if count == 0:
                    continue
                btn = buttons.last
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    await page.wait_for_timeout(500)

                    # Read clipboard via JS
                    try:
                        text = await page.evaluate("navigator.clipboard.readText()")
                        if text and len(text) > 50:
                            log.info(f"Copied via clipboard ({len(text)} chars)")
                            return text.strip()
                    except Exception:
                        # Clipboard API may be blocked — try execCommand fallback
                        pass
            except Exception:
                continue

        return ""

    async def _extract_response_text(self, page, prompt_text: str = "", pre_text: str = "") -> str:
        """Extract the latest AI response, filtering out prompt echo."""

        # Strategy 1 (PRIMARY): Use DOM inner_text on response containers
        selectors = [
            # DeepSeek
            ".ds-markdown",
            # Grok
            '[class*="message-bubble"]',
            # ChatGPT
            "[data-message-author-role='assistant']",
            # Claude
            ".font-claude-message",
            # Qwen
            ".message-content",
            # Kimi
            ".assistant-message",
            # Generic markdown containers
            ".markdown-body",
            ".prose",
            # Generic response containers
            ".response-content",
            ".model-response",
            # Generic: article blocks
            "article",
        ]

        best_text = ""
        for sel in selectors:
            try:
                elements = page.locator(sel)
                count = await elements.count()
                if count == 0:
                    continue

                # Try concatenating ALL matching elements (response may span multiple blocks)
                all_texts = []
                for i in range(count):
                    try:
                        el = elements.nth(i)
                        if await el.is_visible(timeout=500):
                            t = await el.inner_text(timeout=3000)
                            t = t.strip()
                            if t and len(t) > 20 and not self._is_prompt_echo(t, prompt_text):
                                all_texts.append(t)
                    except Exception:
                        continue

                if all_texts:
                    combined = "\n\n".join(all_texts)
                    if len(combined) > len(best_text):
                        best_text = combined
                        log.info(f"DOM extraction: {sel} → {len(combined)} chars ({count} elements)")
            except Exception:
                continue

        MIN_RESPONSE = 5000  # responses under 5K chars = likely incomplete

        if best_text and len(best_text) >= MIN_RESPONSE:
            return best_text
        elif best_text:
            log.warning(f"DOM found only {len(best_text)} chars (< {MIN_RESPONSE}), trying deeper extraction...")

        # Strategy 2: Scroll to bottom + find master Copy button
        # Many services have a master Copy at the very bottom of the response
        log.info("DOM selectors insufficient, scrolling to bottom for master Copy...")
        try:
            # Scroll to absolute bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

            # Look for Copy buttons — collect ALL, click the LAST (bottom-most = full response)
            copy_buttons = page.locator(
                'button:has-text("Copy"), button[aria-label*="Copy"], '
                'button[aria-label*="copy"], [data-testid*="copy"]'
            )
            count = await copy_buttons.count()
            if count > 0:
                # Click the LAST Copy button (bottom of response = master copy)
                last_copy = copy_buttons.nth(count - 1)
                if await last_copy.is_visible(timeout=2000):
                    await last_copy.click()
                    await page.wait_for_timeout(500)
                    try:
                        text = await page.evaluate("navigator.clipboard.readText()")
                        if text and len(text) >= MIN_RESPONSE:
                            log.info(f"Master Copy (bottom, #{count}): {len(text)} chars")
                            return text
                        elif text:
                            log.info(f"Master Copy too short ({len(text)} chars), trying concat...")
                    except Exception:
                        pass

            # Concatenate ALL copy button contents
            if count > 1:
                all_copied = []
                for i in range(count):
                    try:
                        btn = copy_buttons.nth(i)
                        if await btn.is_visible(timeout=500):
                            await btn.click()
                            await page.wait_for_timeout(300)
                            text = await page.evaluate("navigator.clipboard.readText()")
                            if text and len(text) > 20:
                                all_copied.append(text)
                    except Exception:
                        continue
                if all_copied:
                    combined = "\n\n".join(all_copied)
                    log.info(f"Concatenated {len(all_copied)} Copy blocks: {len(combined)} chars")
                    return combined
        except Exception as e:
            log.warning(f"Scroll+Copy fallback failed: {e}")

        # Strategy 3: Single clipboard fallback (last resort)
        copied = await self._click_copy_button(page)
        if copied and len(copied) > 100:
            log.info(f"Single clipboard fallback: {len(copied)} chars")
            return copied

        # Strategy 4: Diff approach — compare current page text with pre-send snapshot
        if pre_text:
            try:
                current_text = await self._get_all_text(page)
                new_text = current_text.replace(pre_text, "").strip()
                if prompt_text:
                    new_text = new_text.replace(prompt_text, "").strip()
                if len(new_text) > 100:
                    log.info(f"Diff extraction: {len(new_text)} chars")
                    return new_text
            except Exception:
                pass

        # All strategies exhausted — return best_text even if < MIN_RESPONSE
        if best_text:
            log.warning(f"All strategies < {MIN_RESPONSE} chars. Best: {len(best_text)} chars (INCOMPLETE)")
            return best_text

        return ""

    def _is_prompt_echo(self, text: str, prompt_text: str) -> bool:
        """Check if extracted text is just an echo of our prompt."""
        if not prompt_text:
            return False
        # Check if significant portion of text appears in prompt
        # Take first 200 chars of extracted text and check against prompt
        sample = text[:200].strip()
        return sample in prompt_text or prompt_text[:200].strip() in text[:300]

    async def setup_profiles(self, services: List[str] = None):
        """Interactive setup: open browser for manual login."""
        log.info("=== SHERPA SETUP MODE ===")
        log.info("Browser will open. Log into each service manually.")
        log.info("Press Enter in terminal when done with each service.\n")

        targets = services or list(self.services.keys())
        for svc_name in targets:
            svc = self.services.get(svc_name)
            if not svc:
                continue
            log.info(f"Opening {svc.name} ({svc.url})...")
            page = await self._get_page(svc_name)
            await page.goto(svc.url, wait_until="domcontentloaded")

            input(f"\n>>> Log into {svc.name}, then press Enter here... ")

            await self._save_storage_state(svc_name)
            log.info(f"Session saved for {svc.name}")

        log.info("\n=== Setup complete! Run 'python sherpa.py' to start recon. ===")


# ── File Collector ─────────────────────────────────────────────────────
def _resolve_doc_path(doc_path: str) -> Optional[Path]:
    """Find actual file on disk from a doc reference."""
    for base in [PROJECT_ROOT, PROJECT_ROOT / "docs", Path("/")]:
        full = base / doc_path
        if full.exists() and full.is_file():
            return full
    return None


def collect_attach_files(task: Dict, code_files: List[Dict[str, str]], max_files: int = 10) -> List[str]:
    """Collect files to attach: architecture docs + recon docs + code files.

    Returns list of absolute file paths ready for upload.
    """
    files = []
    seen = set()

    # 1. Architecture docs (from task — already attached by guard)
    for doc_path in (task.get("architecture_docs", []) or []):
        resolved = _resolve_doc_path(doc_path)
        if resolved and str(resolved) not in seen and resolved.stat().st_size < 2_000_000:
            files.append(str(resolved))
            seen.add(str(resolved))

    # 2. Recon docs (previous research)
    for doc_path in (task.get("recon_docs", []) or []):
        resolved = _resolve_doc_path(doc_path)
        if resolved and str(resolved) not in seen and resolved.stat().st_size < 2_000_000:
            files.append(str(resolved))
            seen.add(str(resolved))

    # 3. Code files found by ripgrep
    for cf in code_files:
        p = Path(cf["path"])
        if p.exists() and str(p) not in seen and p.stat().st_size < 500_000:
            files.append(str(p))
            seen.add(str(p))

    return files[:max_files]


# ── Prompt Builder ─────────────────────────────────────────────────────
def build_recon_prompt(task: Dict, code_snippets: List[Dict[str, str]]) -> str:
    """Build full research prompt with docs and code inline.

    Everything in one text block — no file attachments needed.
    DeepSeek/Qwen handle 100K+ tokens in textarea.
    """
    title = task.get("title", "Unknown")
    desc = task.get("description", "")
    hints = task.get("implementation_hints", "")
    arch_docs = task.get("architecture_docs", []) or []
    recon_docs = task.get("recon_docs", []) or []
    allowed_paths = task.get("allowed_paths", []) or []
    contract = task.get("completion_contract", []) or []

    # Read docs content from disk (full content, services handle 100K+ tokens)
    docs_text = ""
    for doc_path in (arch_docs + recon_docs)[:5]:
        resolved = _resolve_doc_path(doc_path)
        if resolved and resolved.stat().st_size < 100_000:
            content = resolved.read_text(errors="replace")
            docs_text += f"\n### {doc_path}\n{content}\n"

    # Read code snippets (full files up to 100 lines)
    snippets_text = ""
    for s in code_snippets[:5]:
        snippet = read_file_snippet(s["path"], max_lines=100)
        if snippet:
            rel = s["path"].replace(str(PROJECT_ROOT) + "/", "")
            snippets_text += f"\n### {rel}\n```\n{snippet}\n```\n"

    contract_text = ""
    if contract:
        contract_text = "\n## Acceptance Criteria\n" + "\n".join(f"- {c}" for c in contract)

    prompt = f"""Research task for VETKA project (video NLE, React + FastAPI + FFmpeg).

## Task: {title}

## Description
{desc}
"""
    if hints:
        prompt += f"\n## Hints\n{hints}\n"
    if allowed_paths:
        prompt += f"\n## Target Paths\n{', '.join(allowed_paths)}\n"
    if contract_text:
        prompt += contract_text
    if docs_text:
        prompt += f"\n## Architecture Docs\n{docs_text}\n"
    if snippets_text:
        prompt += f"\n## Relevant Code\n{snippets_text}\n"

    prompt += """
## Research needed:
1. Files to Modify — specific paths
2. Approach — step-by-step plan
3. Example Code — key changes
4. Risks — edge cases
5. Dependencies — affected modules
"""
    return prompt.strip()

    # Trim if too long (browser inputs have limits)
    if len(prompt) > 12000:
        prompt = prompt[:12000] + "\n\n[Context trimmed for length. Focus on key changes needed.]"

    return prompt.strip()


# ── Recon Report ───────────────────────────────────────────────────────
def save_recon_report(
    task_id: str, task_title: str, service_name: str,
    prompt: str, response: str, code_files: List[Dict],
) -> Path:
    """Save recon results to markdown file."""
    report_path = RECON_DIR / f"sherpa_{task_id}.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# Sherpa Recon: {task_title}

**Task ID:** `{task_id}`
**Source:** {service_name}
**Date:** {timestamp}
**Agent:** Sherpa (Phase 202)

---

## Codebase Files Found
"""
    for cf in code_files[:10]:
        rel = cf["path"].replace(str(PROJECT_ROOT) + "/", "")
        report += f"- `{rel}`\n"

    report += f"""
---

## Research Response

{response}

---

*Generated by Sherpa — Scout & Harvest Engine for Recon, Prep & Augmentation*
"""
    report_path.write_text(report)
    log.info(f"Recon saved: {report_path}")
    return report_path


# ── Main Loop ──────────────────────────────────────────────────────────
async def sherpa_loop(cfg: SherpaConfig, once: bool = False, dry_run: bool = False, service_filter: str = None):
    """Main Sherpa recon loop."""

    tb = TaskBoardClient(cfg.taskboard_url, cfg.agent_name, cfg.agent_type)
    ollama = OllamaClient(cfg.ollama_url, cfg.ollama_model)

    # Filter services
    active_services = [s for s in cfg.services if s.enabled]
    if service_filter:
        active_services = [s for s in active_services if s.name == service_filter]
    if not active_services:
        log.error("No active services configured. Run: python sherpa.py --setup")
        return

    service_idx = 0  # Round-robin index

    # Check Ollama availability
    if await ollama.is_available():
        log.info(f"Ollama available ({cfg.ollama_model})")
    else:
        log.warning("Ollama not running — will use raw prompts without summarization")

    # Start browser
    browser = BrowserClient(active_services, headless=cfg.headless)
    await browser.start()

    tasks_processed = 0
    skipped_ids: set = set()  # Track skipped tasks to avoid infinite loop

    # MARKER_202.FEEDBACK: Init feedback + load service scores
    feedback = FeedbackCollector()
    scores = feedback.load_scores()
    if scores:
        ranking = feedback.get_service_ranking()
        log.info(f"Service ranking: {', '.join(f'{s}={sc}' for s, sc in ranking)}")

    # MARKER_202.PROTOCOLS: Generate/update protocols from feedback history
    protocols = ServiceProtocol.generate_all()
    if protocols:
        log.info(f"Protocols updated for: {', '.join(protocols.keys())}")
        # Filter out auto-disabled services
        disabled = [s.name for s in active_services if ServiceProtocol.is_service_disabled(s.name)]
        if disabled:
            log.warning(f"Auto-disabled services (consecutive failures): {disabled}")
            active_services = [s for s in active_services if s.name not in disabled]
            if not active_services:
                log.error("All services auto-disabled! Clear data/sherpa_protocols/ to reset.")
                return

    # MARKER_202.HARNESS: Initialize Qwen-powered harness
    harness = SherpaHarness(ollama, feedback)

    # MARKER_202.SHERPA_SIGNAL: Announce startup
    await tb.set_sherpa_status("idle")
    await tb.notify_commanders(f"Sherpa active (PID {os.getpid()}), processing tasks")

    try:
        while tasks_processed < cfg.max_tasks_per_run:
            # 1. Get pending tasks list and find first suitable one
            pending = await tb.get_pending_tasks(limit=30)
            if not pending:
                if once:
                    log.info("No pending tasks")
                    break
                log.info(f"No pending tasks. Sleeping {cfg.cooldown_between_tasks}s...")
                await asyncio.sleep(cfg.cooldown_between_tasks)
                continue

            # MARKER_202.HARNESS: Find first task passing reflex+guard checks
            task = None
            task_id = None
            task_title = None
            for candidate in pending:
                cid = candidate.get("id", "")
                if cid in skipped_ids:
                    continue

                # Reflex: instant pattern skip (no LLM)
                should_skip, skip_reason = harness.reflex_check(candidate)
                if should_skip:
                    log.debug(f"Reflex skip {cid}: {skip_reason}")
                    skipped_ids.add(cid)
                    continue

                # Guard: validate task quality
                is_valid, guard_reason = harness.guard_check(candidate)
                if not is_valid:
                    log.warning(f"Guard reject {cid}: {guard_reason}")
                    skipped_ids.add(cid)
                    continue

                # Found a good candidate — claim it
                claimed = await tb.claim_task(cid)
                if claimed:
                    task = candidate
                    task_id = cid
                    task_title = candidate.get("title", "Unknown")
                    break
                else:
                    skipped_ids.add(cid)  # Claim failed (maybe already taken)

            if not task:
                if once:
                    log.info(f"No suitable tasks (skipped {len(skipped_ids)})")
                    break
                log.info(f"All tasks skipped ({len(skipped_ids)}). Sleeping {cfg.cooldown_between_tasks}s...")
                await asyncio.sleep(cfg.cooldown_between_tasks)
                skipped_ids.clear()
                continue

            log.info(f"{'[DRY RUN] ' if dry_run else ''}Processing: {task_id} — {task_title}")

            # 2. Search codebase for relevant code files
            search_query = f"{task.get('title', '')} {task.get('description', '')[:200]}"
            code_files = search_codebase(search_query, task.get("allowed_paths", []))
            log.info(f"Found {len(code_files)} relevant code files")

            # 3. Build prompt with docs + code inline
            prompt = build_recon_prompt(task, code_files)
            log.info(f"Prompt built ({len(prompt)} chars)")

            if dry_run:
                log.info(f"[DRY RUN] Would send to {active_services[service_idx % len(active_services)].name}")
                log.info(f"[DRY RUN] Prompt ({len(prompt)} chars): {prompt[:300]}...")
                await tb.update_task(task_id, {"status": "pending"})
                tasks_processed += 1
                if once:
                    break
                continue

            # 4. Send to browser AI service (harness-selected or round-robin fallback)
            svc = harness.select_service(active_services, task)
            service_idx += 1  # keep incrementing for fallback

            log.info(f"Sending to {svc.name}...")
            await tb.set_sherpa_status("busy", tasks_processed)
            _svc_start = time.time()
            try:
                response = await browser.send_prompt(svc.name, prompt)
            except Exception as e:
                log.error(f"Browser error ({svc.name}): {e}")
                response = ""
                feedback.log_task(task_id, svc.name, 0, time.time() - _svc_start, False, type(e).__name__)

            if not response:
                log.warning(f"No response from {svc.name}, releasing task")
                if not any(e.get("task_id") == task_id for e in feedback.session_entries):
                    feedback.log_task(task_id, svc.name, 0, time.time() - _svc_start, False, "empty_response")
                await tb.update_task(task_id, {"status": "pending"})
                await asyncio.sleep(30)
                continue

            # 5. Optionally summarize with Ollama
            summary_hint = ""
            if await ollama.is_available() and len(response) > 500:
                summary_hint = await ollama.chat(
                    f"Summarize the key actionable points from this research in 3-5 bullet points. "
                    f"Focus on: files to modify, approach, risks.\n\n{response[:3000]}",
                    max_tokens=500,
                )

            # 6. Save recon report
            report_path = save_recon_report(
                task_id, task_title, svc.name, prompt, response, code_files,
            )
            rel_report = str(report_path.relative_to(PROJECT_ROOT))

            # 7. Update task with recon
            updates = {
                "status": "pending",  # Release back to pool, enriched
            }
            # Append to existing recon_docs
            existing_recon = task.get("recon_docs", []) or []
            if isinstance(existing_recon, str):
                existing_recon = [existing_recon]
            existing_recon.append(rel_report)
            updates["recon_docs"] = existing_recon

            # Add summary as implementation hint
            if summary_hint:
                existing_hints = task.get("implementation_hints", "") or ""
                updates["implementation_hints"] = (
                    f"{existing_hints}\n\n[Sherpa Recon {datetime.now().strftime('%Y-%m-%d')}]\n{summary_hint}"
                ).strip()

            await tb.update_task(task_id, updates)
            tasks_processed += 1
            skipped_ids.add(task_id)  # Don't take same task again
            log.info(f"Task {task_id} enriched ({tasks_processed}/{cfg.max_tasks_per_run})")

            # MARKER_202.FEEDBACK: Log success
            feedback.log_task(task_id, svc.name, len(response), time.time() - _svc_start, True)
            await tb.set_sherpa_status("idle", tasks_processed)

            # MARKER_202.PROTOCOLS: Regenerate after every 5 tasks
            if tasks_processed % 5 == 0:
                ServiceProtocol.generate_all()

            if once:
                break

            # 8. Cooldown
            log.info(f"Cooldown {svc.cooldown_seconds}s...")
            await asyncio.sleep(svc.cooldown_seconds)

    except KeyboardInterrupt:
        log.info("Interrupted by user")
    finally:
        # MARKER_202.FEEDBACK: Save session summary
        feedback.save_session_summary()
        # MARKER_202.PROTOCOLS: Final protocol generation
        ServiceProtocol.generate_all()
        # MARKER_202.SHERPA_SIGNAL: Announce shutdown
        await tb.set_sherpa_status("stopped", tasks_processed)
        await tb.notify_commanders(f"Sherpa stopped. {tasks_processed} tasks enriched.")

        await browser.stop()
        await tb.close()
        await ollama.close()
        h_stats = harness.get_stats()
        log.info(f"Sherpa done. processed={tasks_processed} "
                 f"guard_rejects={h_stats['guard_rejects']} reflex_skips={h_stats['reflex_skips']}")


# ── Setup Mode ─────────────────────────────────────────────────────────
async def setup_mode(cfg: SherpaConfig, services: List[str] = None):
    """Interactive profile setup."""
    active = [s for s in cfg.services if s.enabled]
    if services:
        active = [s for s in active if s.name in services]
    browser = BrowserClient(active, headless=False)  # Always visible for setup
    await browser.start()
    await browser.setup_profiles(services)
    await browser.stop()


# ── Entry Point ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Sherpa — Recon agent for VETKA tasks")
    parser.add_argument("--setup", action="store_true", help="Interactive login setup")
    parser.add_argument("--once", action="store_true", help="Process one task and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--service", type=str, help="Use specific service only (e.g. grok)")
    parser.add_argument("--config", type=str, default=str(CONFIG_PATH), help="Config file path")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode")
    args = parser.parse_args()

    cfg = SherpaConfig.load(Path(args.config))
    if args.visible:
        cfg.headless = False

    if args.setup:
        services = [args.service] if args.service else None
        asyncio.run(setup_mode(cfg, services))
    else:
        # PID Guard — only one Sherpa at a time
        if not acquire_guard():
            old_pid = PID_FILE.read_text().strip() if PID_FILE.exists() else "?"
            log.error(f"Another Sherpa is already running (PID {old_pid}). Only one instance allowed.")
            log.error("If the previous Sherpa crashed, delete data/sherpa.pid and retry.")
            sys.exit(1)

        log.info(f"Sherpa guard acquired (PID {os.getpid()})")
        try:
            asyncio.run(sherpa_loop(cfg, once=args.once, dry_run=args.dry_run, service_filter=args.service))
        finally:
            release_guard()
            log.info("Sherpa guard released")


if __name__ == "__main__":
    main()
