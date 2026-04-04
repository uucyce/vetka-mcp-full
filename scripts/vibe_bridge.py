#!/usr/bin/env python3
"""
scripts/vibe_bridge.py — SYNAPSE: Playwright bridge for Vibe agent prompt injection
Phase 206.7 | ARCH: docs/200_taskboard_forever/ROADMAP_SYNAPSE_206.md
MARKER_206.VIBE_BRIDGE

V1: Stub skeleton with connect/find_input/type/submit structure.
    All methods raise NotImplementedError — wired by SYNAPSE-206.7+.
V2: Full Playwright write support (future).

Usage:
    python scripts/vibe_bridge.py --role Alpha --prompt "claim tb_xxx"
    python scripts/vibe_bridge.py --role Alpha --prompt "claim tb_xxx" --url http://localhost:5173
    echo "multi-line prompt" | python scripts/vibe_bridge.py --role Alpha --prompt -

Graceful fallback: if playwright is not installed, prints install instructions and exits 1.
"""

import argparse
import sys


# ── Playwright availability check ─────────────────────────────────────────────

def _check_playwright() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _playwright_install_hint():
    print(
        "[VibeBridge] ERROR: playwright not installed.\n"
        "Install: pip install playwright && playwright install chromium",
        file=sys.stderr,
    )


# ── VibeBridge class ──────────────────────────────────────────────────────────

class VibeBridge:
    """Playwright bridge for injecting prompts into a running Vibe agent session.

    V1 stub — structure only, NotImplementedError on all operations.
    Wire actual selectors in V2 once Vibe DOM structure is confirmed.
    """

    # Known Vibe chat input selectors (candidates for V2 implementation).
    # Add more as Vibe UI evolves.
    CHAT_INPUT_SELECTORS = [
        "textarea[placeholder*='message']",
        "textarea[placeholder*='Message']",
        "div[contenteditable='true']",
        "[data-testid='chat-input']",
        ".chat-input textarea",
    ]
    SUBMIT_SELECTORS = [
        "button[type='submit']",
        "button[aria-label*='Send']",
        "button[aria-label*='send']",
        "[data-testid='send-button']",
    ]

    def __init__(self, role: str, url: str | None = None):
        self.role = role
        self.url = url
        self._browser = None
        self._page = None

    def connect(self, cdp_port: int = 9222) -> None:
        """Connect to running Chrome via CDP (--remote-debugging-port).

        V1 stub — raises NotImplementedError.
        V2: use playwright.chromium.connect_over_cdp(f'http://localhost:{cdp_port}')
        """
        raise NotImplementedError(
            "VibeBridge.connect() not implemented yet (SYNAPSE-206.7 V2). "
            "Chrome must be launched with --remote-debugging-port=9222 for CDP access."
        )

    def find_input(self):
        """Locate the chat input element in the Vibe UI.

        V1 stub — raises NotImplementedError.
        V2: try CHAT_INPUT_SELECTORS in order, return first visible match.
        """
        raise NotImplementedError(
            "VibeBridge.find_input() not implemented yet (SYNAPSE-206.7 V2)."
        )

    def type_prompt(self, prompt: str) -> None:
        """Type prompt text into the chat input.

        V1 stub — raises NotImplementedError.
        V2: page.fill(selector, prompt) or input_element.type(prompt)
        """
        raise NotImplementedError(
            "VibeBridge.type_prompt() not implemented yet (SYNAPSE-206.7 V2)."
        )

    def submit(self) -> None:
        """Submit the typed prompt (click Send or press Enter).

        V1 stub — raises NotImplementedError.
        V2: try SUBMIT_SELECTORS → click, fallback to page.keyboard.press('Enter')
        """
        raise NotImplementedError(
            "VibeBridge.submit() not implemented yet (SYNAPSE-206.7 V2)."
        )

    def close(self) -> None:
        """Disconnect Playwright without closing the user's browser."""
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
        self._browser = None
        self._page = None

    def inject(self, prompt: str) -> None:
        """Full pipeline: connect → find_input → type → submit.

        V1: raises NotImplementedError (stub).
        V2: wires the full pipeline.
        """
        try:
            self.connect()
            self.find_input()
            self.type_prompt(prompt)
            self.submit()
        finally:
            self.close()


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="VibeBridge: inject a prompt into a running Vibe agent session via Playwright"
    )
    parser.add_argument("--role", required=True, help="Agent callsign (e.g. Alpha)")
    parser.add_argument(
        "--prompt", required=True,
        help="Prompt text to inject, or '-' to read from stdin"
    )
    parser.add_argument(
        "--url", default=None,
        help="Vibe URL (optional, defaults to SYNAPSE_VIBE_URL env var)"
    )
    parser.add_argument(
        "--cdp-port", type=int, default=9222,
        help="Chrome DevTools Protocol port (default: 9222)"
    )
    args = parser.parse_args()

    # Resolve prompt
    if args.prompt == "-":
        prompt = sys.stdin.read().strip()
    else:
        prompt = args.prompt

    if not prompt:
        print("[VibeBridge] ERROR: prompt is empty", file=sys.stderr)
        sys.exit(1)

    # Check Playwright availability
    if not _check_playwright():
        _playwright_install_hint()
        sys.exit(1)

    # Resolve URL
    import os
    url = args.url or os.environ.get("SYNAPSE_VIBE_URL")

    bridge = VibeBridge(role=args.role, url=url)
    try:
        bridge.inject(prompt)
        print(f"[VibeBridge] {args.role} ← prompt injected successfully")
    except NotImplementedError as e:
        # V1 stub — expected, not an error
        print(f"[VibeBridge] STUB: {e}", file=sys.stderr)
        print(
            "[VibeBridge] V1 stub only — full Playwright injection not yet implemented.",
            file=sys.stderr,
        )
        sys.exit(2)  # exit 2 = stub, not a hard error
    except Exception as e:
        print(f"[VibeBridge] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
