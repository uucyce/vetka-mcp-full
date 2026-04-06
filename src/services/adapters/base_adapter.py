"""
Base adapter interface for browser-based AI service automation.

All adapters (Gemini, Kimi, Grok, etc.) inherit from this class.
MARKER_196.BP1.3: Base adapter interface
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class AdapterStatus(Enum):
    IDLE = "idle"
    NAVIGATING = "navigating"
    LOGGING_IN = "logging_in"
    SENDING = "sending"
    WAITING_RESPONSE = "waiting_response"
    EXTRACTING = "extracting"
    ERROR = "error"
    CAPTCHA = "captcha"
    RATE_LIMITED = "rate_limited"


@dataclass
class AdapterResult:
    """Result from an adapter prompt execution."""

    success: bool
    raw_text: str = ""
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None
    status: AdapterStatus = AdapterStatus.IDLE
    response_time_ms: float = 0.0
    captcha_detected: bool = False
    rate_limited: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    """
    Abstract base class for AI chat service adapters.

    Subclasses must implement:
    - navigate_and_login()
    - send_prompt()
    - wait_for_response()
    - extract_response()
    """

    def __init__(self, browser, config: Optional[Dict] = None):
        """
        Args:
            browser: Playwright BrowserContext or Page instance
            config: Adapter-specific configuration
        """
        self.browser = browser
        self.config = config or {}
        self.status = AdapterStatus.IDLE
        self._session_file: Optional[str] = None

    @abstractmethod
    async def navigate_and_login(self) -> bool:
        """Navigate to service and authenticate. Returns True on success."""
        ...

    @abstractmethod
    async def send_prompt(self, prompt: str) -> bool:
        """Send a prompt to the chat interface. Returns True on success."""
        ...

    @abstractmethod
    async def wait_for_response(self, timeout_ms: int = 120000) -> bool:
        """Wait for the AI response to complete. Returns True on success."""
        ...

    @abstractmethod
    async def extract_response(self) -> AdapterResult:
        """Extract the response text and code blocks from the page."""
        ...

    async def execute(self, prompt: str, timeout_ms: int = 120000) -> AdapterResult:
        """
        Full execution flow: login -> send -> wait -> extract.
        """
        import time

        start = time.monotonic()

        if not await self.navigate_and_login():
            return AdapterResult(
                success=False,
                error="Failed to navigate/login",
                status=self.status,
                response_time_ms=(time.monotonic() - start) * 1000,
            )

        if not await self.send_prompt(prompt):
            return AdapterResult(
                success=False,
                error="Failed to send prompt",
                status=self.status,
                response_time_ms=(time.monotonic() - start) * 1000,
            )

        if not await self.wait_for_response(timeout_ms):
            return AdapterResult(
                success=False,
                error="Response timeout or error",
                status=self.status,
                response_time_ms=(time.monotonic() - start) * 1000,
            )

        result = await self.extract_response()
        result.response_time_ms = (time.monotonic() - start) * 1000
        return result

    def _detect_captcha(self, page) -> bool:
        """Check for common captcha elements."""
        captcha_selectors = [
            ".g-recaptcha",
            ".h-captcha",
            "[data-sitekey]",
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
            "#challenge-running",
        ]
        for selector in captcha_selectors:
            if page.query_selector(selector):
                self.status = AdapterStatus.CAPTCHA
                return True
        return False

    def _notify_captcha(self, service_name: str = "AI Service"):
        """Send macOS notification when captcha is detected."""
        import subprocess

        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "Captcha detected on {service_name}. Please solve it to continue." '
                    f'with title "VETKA Browser Proxy" sound name "Glass"',
                ],
                timeout=5,
            )
        except Exception:
            pass

    async def _save_session(self, page, path: str):
        """Save browser session (cookies + localStorage) for reuse."""
        import json

        cookies = await page.context.cookies()
        local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
        session_data = {
            "cookies": cookies,
            "local_storage": json.loads(local_storage) if local_storage else {},
        }
        import os

        os.makedirs(
            os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True
        )
        with open(path, "w") as f:
            json.dump(session_data, f)
        self._session_file = path

    async def _restore_session(self, page, path: str) -> bool:
        """Restore browser session from saved state."""
        import json
        import os

        if not os.path.exists(path):
            return False
        try:
            with open(path) as f:
                session_data = json.load(f)
            for cookie in session_data.get("cookies", []):
                await page.context.add_cookies([cookie])
            for key, value in session_data.get("local_storage", {}).items():
                await page.evaluate(f"localStorage.setItem('{key}', '{value}')")
            return True
        except Exception:
            return False
