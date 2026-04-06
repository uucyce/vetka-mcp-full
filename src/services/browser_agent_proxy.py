"""
MARKER_196.BP1.1: Browser Agent Proxy — Main Orchestrator.

Polls TaskBoard Gateway API for pending tasks, assigns them to browser slots,
routes to service adapters, extracts code responses, commits and pushes.

Architecture:
    TaskBoard (SQLite) → Qwen Orchestrator → Playwright (Chromium × N)
                                                    ↓
                                        Gemini / Kimi / Grok / ...

Usage:
    from src.services.browser_agent_proxy import BrowserAgentProxy

    proxy = BrowserAgentProxy(gateway_url="http://localhost:5001")
    await proxy.start()
    # Runs polling loop — processes tasks automatically
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yaml

from src.services.browser_manager import (
    BrowserManager,
    BrowserSlot,
    get_browser_manager,
)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────

# MARKER_BP1.5.WIRING: Config file path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "browser_agents.yaml"

DEFAULT_GATEWAY_URL = os.getenv("VETKA_GATEWAY_URL", "http://localhost:5001")
DEFAULT_POLL_INTERVAL_S = int(os.getenv("BROWSER_POLL_INTERVAL_S", "10"))
DEFAULT_MAX_RETRIES = int(os.getenv("BROWSER_MAX_RETRIES", "3"))
DEFAULT_REQUEST_TIMEOUT_S = int(os.getenv("BROWSER_REQUEST_TIMEOUT_S", "60"))
DEFAULT_AGENT_NAME = os.getenv("BROWSER_AGENT_NAME", "browser-proxy-qwen")
DEFAULT_AGENT_TYPE = os.getenv("BROWSER_AGENT_TYPE", "local_qwen")
DEFAULT_PROJECT_ID = os.getenv("BROWSER_PROJECT_ID", "MCC")

# Service → adapter mapping (adapters are loaded lazily)
SERVICE_ADAPTERS = {
    "gemini": "adapters.gemini_adapter:GeminiAdapter",
    "kimi": "adapters.kimi_adapter:KimiAdapter",
    "grok": "adapters.grok_adapter:GrokAdapter",
    "perplexity": "adapters.perplexity_adapter:PerplexityAdapter",
    "mistral": "adapters.mistral_adapter:MistralAdapter",
}

# Code block extraction patterns
CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
PRE_CODE_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.DOTALL)


@dataclass
class TaskResult:
    """Result from processing a task through a browser service."""

    success: bool
    task_id: str
    service: str
    extracted_code: Dict[str, str] = field(default_factory=dict)  # path → code
    commit_hash: Optional[str] = None
    error: Optional[str] = None
    duration_s: float = 0.0


class BrowserAgentProxy:
    """Main orchestrator that connects TaskBoard to browser-based AI services.

    Responsibilities:
    - Poll TaskBoard Gateway API for pending tasks
    - Assign tasks to available browser slots
    - Call browser manager to launch Chromium
    - Route task to appropriate service adapter
    - Receive extracted code, commit, push
    - Update TaskBoard status to need_qa
    """

    def __init__(
        self,
        gateway_url: str = DEFAULT_GATEWAY_URL,
        poll_interval_s: int = DEFAULT_POLL_INTERVAL_S,
        max_retries: int = DEFAULT_MAX_RETRIES,
        agent_name: str = DEFAULT_AGENT_NAME,
        agent_type: str = DEFAULT_AGENT_TYPE,
        project_id: str = DEFAULT_PROJECT_ID,
        browser_manager: Optional[BrowserManager] = None,
        config_path: Optional[Path] = None,
    ):
        self.gateway_url = gateway_url.rstrip("/")
        self.poll_interval_s = poll_interval_s
        self.max_retries = max_retries
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.project_id = project_id

        # MARKER_BP1.5.WIRING: Load config from browser_agents.yaml
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        self._apply_config_overrides()

        self.browser_manager = browser_manager or get_browser_manager()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._adapters: Dict[str, Any] = {}
        self._processed_tasks: set = set()  # Avoid double-processing

        # Stats
        self.tasks_processed = 0
        self.tasks_failed = 0
        self.total_duration_s = 0.0

    # ── Config Loading (MARKER_BP1.5.WIRING) ─────────────────────────

    def _load_config(self) -> Dict[str, Any]:
        """Load browser_agents.yaml configuration."""
        if not self.config_path.exists():
            logger.warning(
                "Config not found at %s, using env var defaults",
                self.config_path,
            )
            return {}

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info("Loaded browser agent config from %s", self.config_path)
        return config

    def _apply_config_overrides(self):
        """Apply config values from browser_agents.yaml, overriding env defaults."""
        if not self.config:
            return

        # TaskBoard gateway URL
        tb_cfg = self.config.get("taskboard", {})
        if tb_cfg.get("gateway_url"):
            self.gateway_url = tb_cfg["gateway_url"].rstrip("/")

        # Polling interval
        polling = tb_cfg.get("polling", {})
        if polling.get("interval"):
            self.poll_interval_s = polling["interval"]
            logger.info("Poll interval from config: %ds", self.poll_interval_s)

        # Agent identity
        agent_cfg = tb_cfg.get("agent", {})
        if agent_cfg.get("name"):
            self.agent_name = agent_cfg["name"]
        if agent_cfg.get("agent_type"):
            self.agent_type = agent_cfg["agent_type"]
        if agent_cfg.get("api_key"):
            api_key = agent_cfg["api_key"]
            if api_key.startswith("${") and api_key.endswith("}"):
                env_var = api_key[2:-1]
                api_key = os.environ.get(env_var, "")
            if api_key:
                self._auth_token = api_key
            else:
                logger.warning(
                    "Browser proxy API key not set (env var %s empty)", env_var
                )

        # Browser settings
        browser_cfg = self.config.get("browser", {})
        if browser_cfg.get("max_instances"):
            logger.info(
                "Max browser instances from config: %d", browser_cfg["max_instances"]
            )

        # Rate limiting
        global_cfg = self.config.get("global", {})
        rate_limit = global_cfg.get("rate_limit", {})
        if rate_limit.get("max_requests_per_hour"):
            logger.info(
                "Rate limit from config: %d req/hour",
                rate_limit["max_requests_per_hour"],
            )

    def get_service_accounts(self, service: str) -> List[Dict[str, Any]]:
        """Get account list for a service from config."""
        services = self.config.get("services", {})
        svc = services.get(service, {})
        return svc.get("accounts", [])

    def get_service_url(self, service: str) -> Optional[str]:
        """Get service URL from config."""
        services = self.config.get("services", {})
        svc = services.get(service, {})
        return svc.get("url")

    def get_service_adapter_path(self, service: str) -> Optional[str]:
        """Get adapter file path from config."""
        services = self.config.get("services", {})
        svc = services.get(service, {})
        return svc.get("adapter")

    @property
    def _auth_token(self) -> Optional[str]:
        """Get API key for Gateway API auth."""
        return getattr(self, "_auth_token_value", None) or os.environ.get(
            "BROWSER_PROXY_API_KEY"
        )

    @_auth_token.setter
    def _auth_token(self, value: str):
        self._auth_token_value = value

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self):
        """Start the orchestrator: init HTTP client, browser manager, polling loop."""
        self._http_client = httpx.AsyncClient(
            base_url=self.gateway_url,
            timeout=DEFAULT_REQUEST_TIMEOUT_S,
        )
        self._running = True

        # Start browser manager
        await self.browser_manager.start()

        # Start polling loop
        self._poll_task = asyncio.create_task(self._poll_loop())

        logger.info(
            "BrowserAgentProxy started: gateway=%s, poll_interval=%ds, agent=%s",
            self.gateway_url,
            self.poll_interval_s,
            self.agent_name,
        )

    async def stop(self):
        """Stop the orchestrator gracefully."""
        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        await self.browser_manager.stop()

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        logger.info(
            "BrowserAgentProxy stopped: processed=%d, failed=%d",
            self.tasks_processed,
            self.tasks_failed,
        )

    # ── Polling Loop ──────────────────────────────────────────────────

    async def _poll_loop(self):
        """Main polling loop: fetch pending tasks and process them."""
        while self._running:
            try:
                tasks = await self._fetch_pending_tasks()
                for task in tasks:
                    task_id = task.get("id")
                    if task_id in self._processed_tasks:
                        continue

                    logger.info("Processing task %s: %s", task_id, task.get("title"))
                    result = await self.process_task(task)
                    self._processed_tasks.add(task_id)

                    if result.success:
                        self.tasks_processed += 1
                        await self._update_task_status(task_id, "need_qa", result)
                    else:
                        self.tasks_failed += 1
                        logger.error("Task %s failed: %s", task_id, result.error)

                # Limit polling frequency
                await asyncio.sleep(self.poll_interval_s)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Poll loop error: %s", e)
                await asyncio.sleep(self.poll_interval_s * 2)  # Back off on error

    # ── Gateway API Client ────────────────────────────────────────────

    async def _fetch_pending_tasks(self) -> List[Dict[str, Any]]:
        """Fetch pending tasks from the TaskBoard Gateway API."""
        try:
            headers = self._gateway_auth_headers()
            resp = await self._http_client.get(
                "/api/gateway/tasks",
                params={"status": "pending", "limit": 20},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("tasks", [])
        except Exception as e:
            logger.warning("Failed to fetch pending tasks: %s", e)
            return []

    def _gateway_auth_headers(self) -> Dict[str, str]:
        """Build auth headers for Gateway API requests."""
        headers = {"Content-Type": "application/json"}
        token = self._auth_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        result: TaskResult,
    ):
        """Update task status via the Gateway API complete endpoint.

        MARKER_BP1.5.WIRING: Uses /api/gateway/tasks/{id}/complete to set
        status to need_qa after code extraction and git commit.
        """
        try:
            headers = self._gateway_auth_headers()
            body = {
                "status": status,
                "result_summary": self._format_result_summary(result),
                "result_status": "success" if result.success else "failure",
                "commit_hash": result.commit_hash,
            }
            resp = await self._http_client.patch(
                f"/api/taskboard/{task_id}",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            logger.info("Task %s updated to status: %s", task_id, status)
        except Exception as e:
            logger.warning("Failed to update task %s: %s", task_id, e)

    # ── Task Processing ───────────────────────────────────────────────

    async def process_task(self, task: Dict[str, Any]) -> TaskResult:
        """Process a single task through the browser pipeline.

        Steps:
        1. Determine target service from task tags/description
        2. Acquire a browser slot
        3. Load the appropriate adapter
        4. Navigate to service and send prompt
        5. Extract code from response
        6. Commit code to git
        7. Return result
        """
        task_id = task.get("id", "unknown")
        start_time = time.time()

        # Step 1: Determine service
        service = self._resolve_service(task)
        if not service:
            return TaskResult(
                success=False,
                task_id=task_id,
                service="unknown",
                error="Could not determine target service from task",
                duration_s=time.time() - start_time,
            )

        # Step 2: Acquire browser slot
        try:
            slot = await self.browser_manager.acquire_slot(service)
        except Exception as e:
            return TaskResult(
                success=False,
                task_id=task_id,
                service=service,
                error=f"Failed to acquire browser slot: {e}",
                duration_s=time.time() - start_time,
            )

        try:
            # Step 3: Load adapter
            adapter = await self._get_adapter(service)
            if not adapter:
                return TaskResult(
                    success=False,
                    task_id=task_id,
                    service=service,
                    error=f"No adapter available for service: {service}",
                    duration_s=time.time() - start_time,
                )

            # Step 4: Execute via adapter
            extracted_code = await adapter.execute(slot, task)

            # Step 5: Commit if code was extracted
            commit_hash = None
            if extracted_code:
                commit_hash = await self._commit_code(task_id, extracted_code, service)

            return TaskResult(
                success=True,
                task_id=task_id,
                service=service,
                extracted_code=extracted_code,
                commit_hash=commit_hash,
                duration_s=time.time() - start_time,
            )
        except Exception as e:
            logger.error("Error processing task %s: %s", task_id, e, exc_info=True)
            return TaskResult(
                success=False,
                task_id=task_id,
                service=service,
                error=str(e),
                duration_s=time.time() - start_time,
            )
        finally:
            # Always release the slot
            await self.browser_manager.release_slot(slot)

    # ── Service Resolution ────────────────────────────────────────────

    def _resolve_service(self, task: Dict[str, Any]) -> Optional[str]:
        """Determine which AI service to use based on task metadata."""
        tags = task.get("tags", []) or []
        description = (task.get("description") or "").lower()
        title = (task.get("title") or "").lower()

        # Check tags first
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in SERVICE_ADAPTERS:
                return tag_lower

        # Check description/title for service mentions
        text = f"{title} {description}"
        for service in SERVICE_ADAPTERS:
            if service in text:
                return service

        # Default to first available service
        if SERVICE_ADAPTERS:
            return next(iter(SERVICE_ADAPTERS))

        return None

    # ── Adapter Loading ───────────────────────────────────────────────

    async def _get_adapter(self, service: str) -> Optional[Any]:
        """Lazy-load a service adapter."""
        if service in self._adapters:
            return self._adapters[service]

        adapter_path = SERVICE_ADAPTERS.get(service)
        if not adapter_path:
            logger.warning("No adapter configured for service: %s", service)
            return None

        try:
            module_path, class_name = adapter_path.split(":")
            import importlib

            module = importlib.import_module(module_path)
            adapter_cls = getattr(module, class_name)
            adapter = adapter_cls(gateway_url=self.gateway_url)
            self._adapters[service] = adapter
            logger.info("Loaded adapter for %s", service)
            return adapter
        except Exception as e:
            logger.error("Failed to load adapter for %s: %s", service, e)
            return None

    # ── Code Extraction ───────────────────────────────────────────────

    @staticmethod
    async def extract_code_from_page(page) -> Dict[str, str]:
        """Extract code blocks from a browser page.

        Tries multiple strategies:
        1. DOM parsing: <pre>, <code>, markdown code blocks
        2. Text content analysis for fenced code blocks
        """
        extracted = {}

        # Strategy 1: DOM parsing
        try:
            pre_elements = await page.query_selector_all("pre")
            for i, pre in enumerate(pre_elements):
                text = await pre.inner_text()
                if text.strip():
                    # Try to detect language from class
                    lang_class = await pre.get_attribute("class") or ""
                    lang = "text"
                    for l in ["python", "typescript", "javascript", "rust", "go"]:
                        if l in lang_class.lower():
                            lang = l
                            break
                    extracted[f"extracted_{i}.{lang}"] = text.strip()
        except Exception as e:
            logger.warning("DOM extraction failed: %s", e)

        # Strategy 2: Full page text + regex
        if not extracted:
            try:
                full_text = await page.inner_text("body")
                extracted = extract_code_blocks(full_text)
            except Exception as e:
                logger.warning("Text extraction failed: %s", e)

        return extracted

    # ── Git Operations ────────────────────────────────────────────────

    async def _commit_code(
        self,
        task_id: str,
        code_files: Dict[str, str],
        service: str,
    ) -> Optional[str]:
        """Write extracted code to files and commit via git.

        MARKER_BP1.5.WIRING: Commits with task ID in message for auto-close,
        then pushes to remote.
        """
        if not code_files:
            return None

        try:
            # Write files to the project directory
            written = []
            for filepath, content in code_files.items():
                # Ensure path is relative and safe
                safe_path = self._sanitize_path(filepath)
                full_path = Path.cwd() / safe_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                written.append(safe_path)
                logger.info("Wrote %s (%d bytes)", safe_path, len(content))

            # Git add + commit
            add_result = subprocess.run(
                ["git", "add"] + written,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if add_result.returncode != 0:
                logger.warning("git add failed: %s", add_result.stderr)

            # MARKER_BP1.5.WIRING: Include task ID for auto-close
            commit_msg = (
                f"phase196.BP1.5: Browser proxy wiring — {service} code extraction "
                f"[task:{task_id}]"
            )
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if commit_result.returncode != 0:
                logger.warning("git commit failed: %s", commit_result.stderr)
                return None

            # Get commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            commit_hash = hash_result.stdout.strip()

            # Push to remote
            try:
                push_result = subprocess.run(
                    ["git", "push"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if push_result.returncode != 0:
                    logger.warning("git push failed: %s", push_result.stderr)
                else:
                    logger.info("Pushed commit %s", commit_hash[:12])
            except subprocess.TimeoutExpired:
                logger.warning("git push timed out")

            return commit_hash

        except Exception as e:
            logger.error("Git commit failed: %s", e)
            return None

    @staticmethod
    def _sanitize_path(filepath: str) -> str:
        """Sanitize a file path to prevent directory traversal."""
        # Remove leading slashes and traversal
        clean = filepath.lstrip("/").replace("\\", "/")
        parts = []
        for part in clean.split("/"):
            if part and part != ".." and part != ".":
                parts.append(part)
        return "/".join(parts)

    @staticmethod
    def _format_result_summary(result: TaskResult) -> str:
        """Format a human-readable result summary."""
        if result.success:
            files = (
                ", ".join(result.extracted_code.keys())
                if result.extracted_code
                else "no files"
            )
            return (
                f"Browser proxy ({result.service}): extracted {len(result.extracted_code)} file(s) "
                f"[{files}], commit={result.commit_hash or 'none'}, "
                f"duration={result.duration_s:.1f}s"
            )
        return f"Browser proxy ({result.service}): FAILED — {result.error}"


# ── Code Extraction Helpers ───────────────────────────────────────────


def extract_code_blocks(text: str) -> Dict[str, str]:
    """Extract fenced code blocks from text.

    Returns dict of filename → code content.
    """
    blocks = {}

    # Markdown fenced code blocks
    for i, match in enumerate(CODE_BLOCK_RE.finditer(text)):
        lang = match.group(1) or "text"
        code = match.group(2).strip()
        if code:
            ext = _lang_to_ext(lang)
            blocks[f"block_{i}.{ext}"] = code

    # <pre> tags
    for i, match in enumerate(PRE_CODE_RE.finditer(text)):
        code = match.group(1).strip()
        if code:
            blocks[f"pre_{i}.text"] = code

    return blocks


def _lang_to_ext(lang: str) -> str:
    """Map language name to file extension."""
    mapping = {
        "python": "py",
        "py": "py",
        "typescript": "ts",
        "ts": "ts",
        "tsx": "tsx",
        "javascript": "js",
        "js": "js",
        "rust": "rs",
        "go": "go",
        "html": "html",
        "css": "css",
        "json": "json",
        "yaml": "yaml",
        "yml": "yml",
        "bash": "sh",
        "shell": "sh",
        "sql": "sql",
        "java": "java",
        "c": "c",
        "cpp": "cpp",
        "ruby": "rb",
    }
    return mapping.get(lang.lower(), lang)


# ── Standalone Entry Point ────────────────────────────────────────────


async def run_proxy(
    gateway_url: str = DEFAULT_GATEWAY_URL,
    poll_interval_s: int = DEFAULT_POLL_INTERVAL_S,
):
    """Run the browser proxy as a standalone process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    proxy = BrowserAgentProxy(
        gateway_url=gateway_url,
        poll_interval_s=poll_interval_s,
    )

    await proxy.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await proxy.stop()


if __name__ == "__main__":
    asyncio.run(run_proxy())
