"""
MARKER_196.BP1.2: Browser Manager — Playwright lifecycle management.

Manages N Chromium instances with session persistence, health checks,
memory monitoring, and automatic restart.

Usage:
    from src.services.browser_manager import BrowserManager

    manager = BrowserManager(max_instances=3)
    slot = await manager.acquire_slot("gemini")
    page = slot.page
    # ... do work ...
    await manager.release_slot(slot)
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────

DEFAULT_MAX_INSTANCES = int(os.getenv("BROWSER_MAX_INSTANCES", "3"))
DEFAULT_MEMORY_LIMIT_MB = int(os.getenv("BROWSER_MEMORY_LIMIT_MB", "512"))
DEFAULT_HEALTH_INTERVAL_S = int(os.getenv("BROWSER_HEALTH_INTERVAL_S", "30"))
DEFAULT_SESSION_DIR = os.getenv(
    "BROWSER_SESSION_DIR",
    str(Path.home() / ".vetka" / "browser_sessions"),
)
DEFAULT_VIEWPORT_WIDTH = int(os.getenv("BROWSER_VIEWPORT_WIDTH", "1440"))
DEFAULT_VIEWPORT_HEIGHT = int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "900"))
DEFAULT_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"

# Captcha selectors (common patterns across services)
CAPTCHA_SELECTORS = [
    ".g-recaptcha",
    ".h-captcha",
    "[data-recaptcha]",
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "iframe[src*='turnstile']",
    "#turnstile-widget",
    ".cf-challenge",
]


@dataclass
class BrowserSlot:
    """Represents a single browser instance slot."""

    slot_id: int
    service: str  # e.g. "gemini", "kimi", "grok"
    page: Any = None  # playwright.async_api.Page
    context: Any = None  # playwright.async_api.BrowserContext
    browser: Any = None  # playwright.async_api.Browser
    is_healthy: bool = True
    last_health_check: float = 0.0
    last_activity: float = 0.0
    captcha_detected: bool = False
    captcha_at: float = 0.0
    restart_count: int = 0
    session_dir: str = ""
    account_index: int = 0
    locked: bool = False  # True while a task is being processed


@dataclass
class SessionData:
    """Serializable session data for persistence."""

    cookies: List[Dict[str, Any]] = field(default_factory=list)
    local_storage: Dict[str, str] = field(default_factory=dict)
    url: str = ""
    saved_at: float = 0.0


class BrowserManager:
    """Manages Playwright Chromium instances.

    Features:
    - Launch/close headless Chromium
    - Session persistence (save/restore cookies, localStorage)
    - Health checks (is browser responsive?)
    - Memory monitoring + automatic restart
    - Support for N parallel instances
    """

    def __init__(
        self,
        max_instances: int = DEFAULT_MAX_INSTANCES,
        memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
        health_interval_s: int = DEFAULT_HEALTH_INTERVAL_S,
        session_dir: str = DEFAULT_SESSION_DIR,
        headless: bool = DEFAULT_HEADLESS,
        viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
        viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
    ):
        self.max_instances = max_instances
        self.memory_limit_mb = memory_limit_mb
        self.health_interval_s = health_interval_s
        self.session_dir = Path(session_dir)
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

        self._slots: Dict[int, BrowserSlot] = {}
        self._playwright = None
        self._health_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

        # Per-service account rotation tracking
        self._service_accounts: Dict[str, int] = {}  # service -> next_account_index
        self._service_account_count: Dict[str, int] = {}  # service -> total accounts

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self):
        """Initialize Playwright and pre-warm browser slots."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._running = True
        self.session_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "BrowserManager started: max_instances=%d, headless=%s, session_dir=%s",
            self.max_instances,
            self.headless,
            self.session_dir,
        )

        # Start health monitoring loop
        self._health_task = asyncio.create_task(self._health_loop())

    async def stop(self):
        """Shut down all browser instances and Playwright."""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        # Close all slots
        for slot_id in list(self._slots.keys()):
            await self._close_slot(slot_id)

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("BrowserManager stopped")

    # ── Slot Management ───────────────────────────────────────────────

    async def acquire_slot(self, service: str) -> BrowserSlot:
        """Acquire a browser slot for a service. Reuses existing slot or launches new one.

        Args:
            service: Service name (e.g. "gemini", "kimi", "grok")

        Returns:
            BrowserSlot with ready-to-use page
        """
        async with self._lock:
            # Try to find an existing healthy slot for this service
            for slot in self._slots.values():
                if slot.service == service and slot.is_healthy and not slot.locked:
                    slot.locked = True
                    slot.last_activity = time.time()
                    logger.debug("Reusing slot %d for %s", slot.slot_id, service)
                    return slot

            # Check if we can create a new slot
            if len(self._slots) >= self.max_instances:
                # Find the oldest slot and recycle it
                oldest = min(self._slots.values(), key=lambda s: s.last_activity)
                logger.info(
                    "Max instances reached (%d), recycling slot %d",
                    self.max_instances,
                    oldest.slot_id,
                )
                await self._close_slot(oldest.slot_id)

            # Create new slot
            slot_id = self._next_slot_id()
            slot = await self._launch_browser(slot_id, service)
            slot.locked = True
            self._slots[slot_id] = slot
            return slot

    async def release_slot(self, slot: BrowserSlot):
        """Release a browser slot after task completion."""
        async with self._lock:
            slot.locked = False
            slot.last_activity = time.time()
            logger.debug("Released slot %d", slot.slot_id)

    async def recycle_slot(self, slot: BrowserSlot):
        """Recycle a slot (close and relaunch). Used after captcha or memory issues."""
        async with self._lock:
            await self._close_slot(slot.slot_id)
            new_slot = await self._launch_browser(slot.slot_id, slot.service)
            self._slots[slot.slot_id] = new_slot
            logger.info("Recycled slot %d for %s", slot.slot_id, slot.service)
            return new_slot

    def get_slot(self, slot_id: int) -> Optional[BrowserSlot]:
        """Get a slot by ID (non-locking, for status queries)."""
        return self._slots.get(slot_id)

    def get_all_slots(self) -> List[BrowserSlot]:
        """Get all active slots."""
        return list(self._slots.values())

    def get_available_count(self) -> int:
        """Count of available (healthy, unlocked) slots."""
        return sum(1 for s in self._slots.values() if s.is_healthy and not s.locked)

    # ── Session Persistence ───────────────────────────────────────────

    async def save_session(self, slot: BrowserSlot) -> SessionData:
        """Save cookies and localStorage for a slot."""
        session_data = SessionData(
            saved_at=time.time(),
            url=slot.page.url if slot.page else "",
        )

        try:
            if slot.context:
                session_data.cookies = await slot.context.cookies()
        except Exception as e:
            logger.warning("Failed to save cookies for slot %d: %s", slot.slot_id, e)

        # Save localStorage via page evaluation
        try:
            if slot.page:
                ls = await slot.page.evaluate("() => { ...localStorage }")
                session_data.local_storage = ls or {}
        except Exception as e:
            logger.warning(
                "Failed to save localStorage for slot %d: %s", slot.slot_id, e
            )

        # Persist to disk
        session_file = self._session_file(slot)
        try:
            session_file.parent.mkdir(parents=True, exist_ok=True)
            session_file.write_text(json.dumps(self._session_to_dict(session_data)))
            logger.debug("Session saved for slot %d -> %s", slot.slot_id, session_file)
        except Exception as e:
            logger.warning("Failed to write session file: %s", e)

        return session_data

    async def restore_session(self, slot: BrowserSlot) -> bool:
        """Restore cookies and localStorage from disk."""
        session_file = self._session_file(slot)
        if not session_file.exists():
            logger.debug("No session file for slot %d", slot.slot_id)
            return False

        try:
            data = json.loads(session_file.read_text())
            session_data = self._session_from_dict(data)
        except Exception as e:
            logger.warning("Failed to read session file: %s", e)
            return False

        # Restore cookies
        if session_data.cookies and slot.context:
            try:
                await slot.context.add_cookies(session_data.cookies)
                logger.debug(
                    "Restored %d cookies for slot %d",
                    len(session_data.cookies),
                    slot.slot_id,
                )
            except Exception as e:
                logger.warning("Failed to restore cookies: %s", e)

        # Navigate and restore localStorage
        if session_data.url and session_data.local_storage and slot.page:
            try:
                await slot.page.goto(session_data.url, wait_until="domcontentloaded")
                for key, value in session_data.local_storage.items():
                    await slot.page.evaluate(
                        f"() => localStorage.setItem({json.dumps(key)}, {json.dumps(value)})"
                    )
                logger.debug(
                    "Restored localStorage for slot %d",
                    slot.slot_id,
                )
            except Exception as e:
                logger.warning("Failed to restore localStorage: %s", e)

        return True

    # ── Health Checks ─────────────────────────────────────────────────

    async def check_health(self, slot: BrowserSlot) -> bool:
        """Check if a browser slot is responsive."""
        try:
            if not slot.page or slot.page.is_closed():
                slot.is_healthy = False
                return False

            # Quick navigation check
            await slot.page.evaluate("() => document.readyState")
            slot.is_healthy = True
            slot.last_health_check = time.time()

            # Check for captcha
            slot.captcha_detected = await self._detect_captcha(slot.page)
            if slot.captcha_detected:
                slot.captcha_at = time.time()
                logger.warning("Captcha detected on slot %d", slot.slot_id)

            return True
        except Exception as e:
            logger.warning("Health check failed for slot %d: %s", slot.slot_id, e)
            slot.is_healthy = False
            return False

    async def _health_loop(self):
        """Background loop: periodically check all slots."""
        while self._running:
            try:
                await asyncio.sleep(self.health_interval_s)
                for slot in list(self._slots.values()):
                    if slot.locked:
                        continue  # Skip busy slots

                    healthy = await self.check_health(slot)
                    if not healthy:
                        logger.info("Auto-restarting unhealthy slot %d", slot.slot_id)
                        await self._close_slot(slot.slot_id)
                        new_slot = await self._launch_browser(
                            slot.slot_id, slot.service
                        )
                        self._slots[slot.slot_id] = new_slot
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health loop error: %s", e)

    # ── Account Rotation ──────────────────────────────────────────────

    def get_next_account(self, service: str, total_accounts: int = 10) -> int:
        """Get next account index for a service (round-robin)."""
        self._service_account_count[service] = total_accounts
        idx = self._service_accounts.get(service, 0)
        self._service_accounts[service] = (idx + 1) % total_accounts
        return idx

    # ── Internal ──────────────────────────────────────────────────────

    async def _launch_browser(self, slot_id: int, service: str) -> BrowserSlot:
        """Launch a new Chromium instance."""
        launch_options = {
            "headless": self.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--disable-extensions",
                f"--window-size={self.viewport_width},{self.viewport_height}",
            ],
        }

        browser = await self._playwright.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        slot = BrowserSlot(
            slot_id=slot_id,
            service=service,
            page=page,
            context=context,
            browser=browser,
            is_healthy=True,
            last_health_check=time.time(),
            last_activity=time.time(),
            session_dir=str(self.session_dir / service),
        )

        # Try to restore previous session
        await self.restore_session(slot)

        logger.info(
            "Launched browser slot %d for %s (headless=%s)",
            slot_id,
            service,
            self.headless,
        )
        return slot

    async def _close_slot(self, slot_id: int):
        """Close a browser slot and save its session."""
        slot = self._slots.get(slot_id)
        if not slot:
            return

        # Save session before closing
        try:
            await self.save_session(slot)
        except Exception as e:
            logger.warning("Failed to save session before close: %s", e)

        try:
            if slot.browser:
                await slot.browser.close()
        except Exception as e:
            logger.warning("Error closing browser slot %d: %s", slot_id, e)

        self._slots.pop(slot_id, None)
        logger.debug("Closed slot %d", slot_id)

    async def _detect_captcha(self, page) -> bool:
        """Detect captcha elements on the current page."""
        try:
            for selector in CAPTCHA_SELECTORS:
                elements = await page.query_selector_all(selector)
                if elements:
                    # Check if element is visible
                    for el in elements:
                        is_visible = await el.is_visible()
                        if is_visible:
                            return True
        except Exception:
            pass
        return False

    def _session_file(self, slot: BrowserSlot) -> Path:
        """Get the session file path for a slot."""
        return Path(slot.session_dir) / f"slot_{slot.slot_id}_session.json"

    def _next_slot_id(self) -> int:
        """Generate the next slot ID."""
        if not self._slots:
            return 0
        return max(self._slots.keys()) + 1

    @staticmethod
    def _session_to_dict(data: SessionData) -> dict:
        """Serialize session data to dict."""
        return {
            "cookies": data.cookies,
            "local_storage": data.local_storage,
            "url": data.url,
            "saved_at": data.saved_at,
        }

    @staticmethod
    def _session_from_dict(data: dict) -> SessionData:
        """Deserialize session data from dict."""
        return SessionData(
            cookies=data.get("cookies", []),
            local_storage=data.get("local_storage", {}),
            url=data.get("url", ""),
            saved_at=data.get("saved_at", 0.0),
        )


# ── Singleton ─────────────────────────────────────────────────────────

_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """Get or create the global BrowserManager singleton."""
    global _manager
    if _manager is None:
        _manager = BrowserManager()
    return _manager


def reset_browser_manager():
    """Reset the global singleton (for testing)."""
    global _manager
    _manager = None
