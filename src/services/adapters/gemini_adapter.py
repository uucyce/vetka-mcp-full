"""
Gemini adapter for Google AI Studio automation via Playwright.

Automates:
- Navigate to aistudio.google.com
- Login with Gmail credentials (from config)
- Send prompt to chat
- Wait for response (streaming)
- Extract code blocks from DOM
- Handle errors (rate limit, captcha)

MARKER_196.BP1.3: Gemini adapter implementation
"""

import asyncio
import logging
import os
import re
import time
from typing import Optional, Dict, List, Any

from src.services.adapters.base_adapter import (
    BaseAdapter,
    AdapterResult,
    AdapterStatus,
)

logger = logging.getLogger("vetka.gemini_adapter")

GEMINI_URL = "https://aistudio.google.com/prompts/new_chat"
GEMINI_LOGIN_URL = "https://accounts.google.com"

GEMINI_SELECTORS = {
    "prompt_input": "textarea[aria-label='Ask a question']",
    "prompt_input_alt": "div[contenteditable='true']",
    "send_button": "button[aria-label='Send']",
    "send_button_alt": "button:has-text('Send')",
    "response_area": "div[role='main']",
    "response_message": "div[role='main'] p, div[role='main'] pre, div[role='main'] code",
    "streaming_indicator": "div[role='main'] .streaming, div[role='main'] [class*='typing']",
    "code_block": "pre, code, div[class*='code-block']",
    "error_message": "div[role='alert'], .error-message, [class*='error']",
    "rate_limit": "Rate limit",
    "new_chat_button": "button[aria-label='New chat']",
    "model_selector": "button[aria-label='Model']",
}


class GeminiAdapter(BaseAdapter):
    """
    Adapter for Google AI Studio (Gemini) via Playwright.

    Usage:
        adapter = GeminiAdapter(page, config={
            "email": "user@gmail.com",
            "session_path": ".gemini_session.json",
        })
        result = await adapter.execute("Write a Python function to...")
    """

    SERVICE_NAME = "Gemini (Google AI Studio)"
    URL = GEMINI_URL

    def __init__(self, browser, config: Optional[Dict] = None):
        super().__init__(browser, config)
        self._email = self.config.get("email", "")
        self._session_path = self.config.get(
            "session_path",
            os.path.expanduser("~/.vetka/sessions/gemini_session.json"),
        )
        self._max_retries = self.config.get("max_retries", 3)
        self._response_timeout = self.config.get("response_timeout_ms", 120000)

    async def navigate_and_login(self) -> bool:
        """Navigate to AI Studio and ensure logged in."""
        try:
            page = self._get_page()
            if not page:
                logger.error("No page available for Gemini adapter")
                self.status = AdapterStatus.ERROR
                return False

            # Try to restore session first
            if await self._restore_session(page, self._session_path):
                logger.info("Restored Gemini session from cache")
                self.status = AdapterStatus.NAVIGATING
                await page.goto(self.URL, wait_until="domcontentloaded", timeout=30000)
                await self._wait_for_load(page)

                if not self._detect_captcha(page):
                    return True
                else:
                    self._notify_captcha(self.SERVICE_NAME)
                    logger.warning("Captcha detected after session restore")
                    return False

            # Fresh login flow
            self.status = AdapterStatus.NAVIGATING
            logger.info("Navigating to Google AI Studio...")
            await page.goto(self.URL, wait_until="domcontentloaded", timeout=30000)

            # Check if already logged in
            if await self._is_logged_in(page):
                logger.info("Already logged in to AI Studio")
                await self._save_session(page, self._session_path)
                return True

            # Need to login
            self.status = AdapterStatus.LOGGING_IN
            logger.info("Login required for AI Studio")

            if self._email:
                await self._login_with_email(page)
            else:
                logger.info(
                    "No email configured — waiting for manual login "
                    "(session will be saved for next run)"
                )
                await self._wait_for_manual_login(page)

            if self._detect_captcha(page):
                self._notify_captcha(self.SERVICE_NAME)
                return False

            await self._save_session(page, self._session_path)
            return True

        except Exception as e:
            logger.error(f"Navigation/login failed: {e}")
            self.status = AdapterStatus.ERROR
            return False

    async def send_prompt(self, prompt: str) -> bool:
        """Send a prompt to the Gemini chat interface."""
        try:
            page = self._get_page()
            if not page:
                self.status = AdapterStatus.ERROR
                return False

            self.status = AdapterStatus.SENDING

            # Start new chat if needed
            await self._start_new_chat(page)

            # Find input field
            input_el = await self._find_prompt_input(page)
            if not input_el:
                logger.error("Could not find prompt input field")
                self.status = AdapterStatus.ERROR
                return False

            # Type prompt with human-like delay
            logger.info(f"Sending prompt ({len(prompt)} chars)...")
            await input_el.fill(prompt)
            await asyncio.sleep(0.5)

            # Click send
            send_btn = await self._find_send_button(page)
            if send_btn:
                await send_btn.click()
            else:
                # Fallback: press Enter
                await input_el.press("Enter")

            await asyncio.sleep(1)
            self.status = AdapterStatus.WAITING_RESPONSE
            return True

        except Exception as e:
            logger.error(f"Failed to send prompt: {e}")
            self.status = AdapterStatus.ERROR
            return False

    async def wait_for_response(self, timeout_ms: int = 120000) -> bool:
        """Wait for Gemini to finish generating response."""
        try:
            page = self._get_page()
            if not page:
                self.status = AdapterStatus.ERROR
                return False

            start = time.monotonic()
            poll_interval = 0.5
            last_content = ""
            stable_count = 0
            max_stable = 6

            while True:
                elapsed_ms = (time.monotonic() - start) * 1000
                if elapsed_ms > timeout_ms:
                    logger.error("Response timeout")
                    self.status = AdapterStatus.ERROR
                    return False

                # Check for errors
                if await self._check_error(page):
                    return False

                # Check for captcha
                if self._detect_captcha(page):
                    self._notify_captcha(self.SERVICE_NAME)
                    self.status = AdapterStatus.CAPTCHA
                    return False

                # Get current response content
                current_content = await self._get_response_text(page)

                # Check if response is still streaming
                is_streaming = await self._is_streaming(page)

                if current_content and not is_streaming:
                    # Content stable — check if it stopped changing
                    if current_content == last_content:
                        stable_count += 1
                        if stable_count >= max_stable:
                            logger.info(
                                f"Response complete "
                                f"({len(current_content)} chars, "
                                f"{elapsed_ms / 1000:.1f}s)"
                            )
                            return True
                    else:
                        stable_count = 0
                        last_content = current_content

                await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Wait for response failed: {e}")
            self.status = AdapterStatus.ERROR
            return False

    async def extract_response(self) -> AdapterResult:
        """Extract response text and code blocks from the page."""
        try:
            page = self._get_page()
            if not page:
                return AdapterResult(
                    success=False, error="No page available", status=AdapterStatus.ERROR
                )

            self.status = AdapterStatus.EXTRACTING

            # Get full response text
            raw_text = await self._get_response_text(page)
            if not raw_text:
                return AdapterResult(
                    success=False,
                    error="No response text found",
                    status=AdapterStatus.ERROR,
                )

            # Extract code blocks
            code_blocks = await self._extract_code_blocks(page)

            # Fallback: parse code blocks from raw text (markdown)
            if not code_blocks:
                code_blocks = self._parse_markdown_code_blocks(raw_text)

            return AdapterResult(
                success=True,
                raw_text=raw_text,
                code_blocks=code_blocks,
                status=AdapterStatus.IDLE,
            )

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return AdapterResult(
                success=False, error=str(e), status=AdapterStatus.ERROR
            )

    # ---- Private helpers ----

    def _get_page(self):
        """Get Playwright page from browser context."""
        if hasattr(self.browser, "pages") and self.browser.pages:
            return self.browser.pages[-1]
        if hasattr(self.browser, "goto"):
            return self.browser
        return None

    async def _is_logged_in(self, page) -> bool:
        """Check if already authenticated to AI Studio."""
        try:
            await page.wait_for_selector(
                GEMINI_SELECTORS["prompt_input"],
                timeout=5000,
            )
            return True
        except Exception:
            pass
        try:
            await page.wait_for_selector(
                GEMINI_SELECTORS["prompt_input_alt"],
                timeout=5000,
            )
            return True
        except Exception:
            return False

    async def _wait_for_load(self, page):
        """Wait for page to be fully interactive."""
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

    async def _login_with_email(self, page):
        """Perform Gmail login flow."""
        try:
            await page.goto(
                GEMINI_LOGIN_URL, wait_until="domcontentloaded", timeout=30000
            )

            # Enter email
            email_input = await page.wait_for_selector(
                "input[type='email']", timeout=10000
            )
            if email_input:
                await email_input.fill(self._email)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)

                # If password field appears, we need password from config
                password_input = page.query_selector("input[type='password']")
                if password_input:
                    password = self.config.get("password", "")
                    if password:
                        await password_input.fill(password)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(3)
                    else:
                        logger.warning(
                            "Password required but not configured — "
                            "waiting for manual input"
                        )
                        await self._wait_for_manual_login(page)

            # Navigate back to AI Studio
            await page.goto(self.URL, wait_until="domcontentloaded", timeout=30000)
            await self._wait_for_load(page)

        except Exception as e:
            logger.error(f"Login flow failed: {e}")

    async def _wait_for_manual_login(self, page, timeout_s: int = 120):
        """Wait for user to manually login."""
        logger.info(f"Waiting up to {timeout_s}s for manual login...")
        start = time.monotonic()
        while time.monotonic() - start < timeout_s:
            if await self._is_logged_in(page):
                logger.info("Manual login detected")
                return
            await asyncio.sleep(2)
        logger.error("Manual login timeout")

    async def _start_new_chat(self, page):
        """Start a new chat session."""
        try:
            new_chat = page.query_selector(GEMINI_SELECTORS["new_chat_button"])
            if new_chat:
                await new_chat.click()
                await asyncio.sleep(1)
        except Exception:
            pass

    async def _find_prompt_input(self, page):
        """Find the prompt input element."""
        for selector in [
            GEMINI_SELECTORS["prompt_input"],
            GEMINI_SELECTORS["prompt_input_alt"],
            "textarea",
            "div[contenteditable]",
        ]:
            try:
                el = await page.wait_for_selector(selector, timeout=3000)
                if el:
                    return el
            except Exception:
                continue
        return None

    async def _find_send_button(self, page):
        """Find the send/submit button."""
        for selector in [
            GEMINI_SELECTORS["send_button"],
            GEMINI_SELECTORS["send_button_alt"],
            "button[type='submit']",
        ]:
            el = page.query_selector(selector)
            if el:
                return el
        return None

    async def _get_response_text(self, page) -> str:
        """Get the full response text from the page."""
        try:
            # Try main response area
            response_area = page.query_selector(GEMINI_SELECTORS["response_area"])
            if response_area:
                text = await response_area.inner_text()
                return text.strip()

            # Fallback: get all text from response messages
            messages = page.query_selector_all(GEMINI_SELECTORS["response_message"])
            if messages:
                texts = []
                for msg in messages[-10:]:
                    t = await msg.inner_text()
                    if t.strip():
                        texts.append(t.strip())
                return "\n".join(texts)

        except Exception as e:
            logger.error(f"Failed to get response text: {e}")

        return ""

    async def _is_streaming(self, page) -> bool:
        """Check if response is still being generated."""
        try:
            # Look for streaming indicators
            streaming = page.query_selector(GEMINI_SELECTORS["streaming_indicator"])
            if streaming:
                return True

            # Check for cursor/typing animation
            typing = await page.evaluate("""
                () => {
                    const els = document.querySelectorAll('[class*="typing"], [class*="cursor"], [class*="streaming"]');
                    return els.length > 0;
                }
            """)
            if typing:
                return True

            return False
        except Exception:
            return False

    async def _check_error(self, page) -> bool:
        """Check for error messages in the response."""
        try:
            # Check for rate limit
            body_text = await page.inner_text("body")
            if "Rate limit" in body_text or "rate limit" in body_text:
                logger.warning("Rate limit detected")
                self.status = AdapterStatus.RATE_LIMITED
                return True

            # Check for error elements
            error_el = page.query_selector(GEMINI_SELECTORS["error_message"])
            if error_el:
                error_text = await error_el.inner_text()
                logger.error(f"Error detected: {error_text}")
                self.status = AdapterStatus.ERROR
                return True

        except Exception:
            pass

        return False

    async def _extract_code_blocks(self, page) -> List[Dict[str, str]]:
        """Extract code blocks from the DOM."""
        blocks = []
        try:
            # Look for <pre> and <code> elements
            code_elements = page.query_selector_all("pre, code")
            for el in code_elements:
                text = await el.inner_text()
                if len(text.strip()) < 10:
                    continue

                # Try to detect language from class or parent
                lang = "text"
                class_attr = await el.get_attribute("class") or ""
                for lang_hint in [
                    "python",
                    "typescript",
                    "javascript",
                    "rust",
                    "go",
                    "java",
                    "cpp",
                    "c",
                    "html",
                    "css",
                    "json",
                    "yaml",
                    "bash",
                    "shell",
                    "sql",
                ]:
                    if lang_hint in class_attr.lower():
                        lang = lang_hint
                        break

                blocks.append({"language": lang, "code": text.strip()})

        except Exception as e:
            logger.error(f"Failed to extract code blocks from DOM: {e}")

        return blocks

    @staticmethod
    def _parse_markdown_code_blocks(text: str) -> List[Dict[str, str]]:
        """Parse markdown code blocks from raw text."""
        blocks = []
        pattern = re.compile(r"```(\w+)?\s*\n(.*?)```", re.DOTALL)
        for match in pattern.finditer(text):
            lang = match.group(1) or "text"
            code = match.group(2).strip()
            if len(code) > 10:
                blocks.append({"language": lang, "code": code})
        return blocks
