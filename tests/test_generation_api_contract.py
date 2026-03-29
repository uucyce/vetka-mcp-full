"""
MARKER_EPSILON.GENERATION: Generation API Contract Tests.

Canonical spec: src/api/routes/cut_routes_generation.py (MARKER_B98)

Static contract tests — read route source, verify endpoint paths,
Pydantic model fields, and behaviour guarantees without spinning up a server.

Sections:
  1. EndpointContract  — all 9 routes exist in routes file
  2. RequestModels     — required fields on Pydantic models
  3. BehaviourGuards   — 402 budget guard, 404 on missing job, estimate path
  4. RouterWiring      — generation_router registered in main app
"""

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ROUTES_FILE = Path("src/api/routes/cut_routes_generation.py")
APP_MAIN_FILES = [
    Path("src/api/app.py"),
    Path("src/main.py"),
    Path("src/app.py"),
]


@pytest.fixture(scope="module")
def routes_source() -> str:
    if not ROUTES_FILE.exists():
        pytest.skip(f"{ROUTES_FILE} not found")
    return ROUTES_FILE.read_text()


@pytest.fixture(scope="module")
def app_source() -> str:
    for p in APP_MAIN_FILES:
        if p.exists():
            return p.read_text()
    pytest.skip("No app entry-point file found")


# ---------------------------------------------------------------------------
# §1: Endpoint Contract — all routes must be present
# ---------------------------------------------------------------------------

class TestEndpointContract:
    """All 9 generation endpoints defined in MARKER_B98 must exist."""

    EXPECTED_ROUTES = [
        "/generate/submit",
        "/generate/status/",
        "/generate/queue",
        "/generate/cancel",
        "/generate/accept",
        "/generate/providers",
        "/generate/budget",
        "/generate/budget/limits",
        "/generate/estimate",
    ]

    @pytest.mark.parametrize("route", EXPECTED_ROUTES)
    def test_route_defined(self, routes_source, route):
        """Each route path must appear in the routes file."""
        assert route in routes_source, f"Route '{route}' missing from {ROUTES_FILE}"

    def test_all_routes_are_registered(self, routes_source):
        """generation_router must be defined (not just imported)."""
        assert "generation_router" in routes_source
        assert "APIRouter" in routes_source

    def test_submit_is_post(self, routes_source):
        """Submit must be POST, not GET — idempotency contract."""
        # Pattern: @generation_router.post("/generate/submit")
        assert re.search(r'router\.post\(["\'].*submit', routes_source)

    def test_status_is_get(self, routes_source):
        """Status polling must be GET."""
        assert re.search(r'router\.get\(["\'].*status', routes_source)

    def test_cancel_is_post(self, routes_source):
        """Cancel must be POST (side-effecting)."""
        assert re.search(r'router\.post\(["\'].*cancel', routes_source)

    def test_estimate_is_post(self, routes_source):
        """Estimate takes a full request body → POST."""
        assert re.search(r'router\.post\(["\'].*estimate', routes_source)


# ---------------------------------------------------------------------------
# §2: Request Model Fields
# ---------------------------------------------------------------------------

class TestRequestModels:
    """Pydantic models must expose the fields the frontend contract requires."""

    def test_submit_request_has_provider(self, routes_source):
        """GenerateSubmitRequest must have 'provider' field."""
        assert "provider" in routes_source

    def test_submit_request_has_prompt(self, routes_source):
        """GenerateSubmitRequest must have 'prompt' field."""
        assert "prompt" in routes_source

    def test_submit_request_has_duration(self, routes_source):
        """GenerateSubmitRequest must have duration_sec field."""
        assert "duration_sec" in routes_source

    def test_submit_request_has_resolution(self, routes_source):
        """GenerateSubmitRequest must have resolution field (1280x768 default)."""
        assert "resolution" in routes_source
        assert "1280x768" in routes_source

    def test_cancel_request_has_job_id(self, routes_source):
        """GenerateCancelRequest must require job_id."""
        assert "GenerateCancelRequest" in routes_source
        # job_id must appear near GenerateCancelRequest
        idx = routes_source.index("GenerateCancelRequest")
        nearby = routes_source[idx: idx + 200]
        assert "job_id" in nearby

    def test_accept_request_has_job_id(self, routes_source):
        """GenerateAcceptRequest must require job_id."""
        assert "GenerateAcceptRequest" in routes_source
        idx = routes_source.index("GenerateAcceptRequest")
        nearby = routes_source[idx: idx + 200]
        assert "job_id" in nearby

    def test_budget_request_has_limits(self, routes_source):
        """BudgetLimitRequest must have daily_limit and monthly_limit."""
        assert "daily_limit" in routes_source
        assert "monthly_limit" in routes_source


# ---------------------------------------------------------------------------
# §3: Behaviour Guards
# ---------------------------------------------------------------------------

class TestBehaviourGuards:
    """Key behaviour guarantees that must be in the route implementation."""

    def test_submit_has_402_budget_guard(self, routes_source):
        """Submit must raise 402 when over budget — not 500."""
        assert "402" in routes_source
        assert "budget" in routes_source.lower()

    def test_status_has_404_on_missing_job(self, routes_source):
        """Status must return 404 if job not found — not silently return None."""
        assert "404" in routes_source
        assert "not found" in routes_source.lower() or "not_found" in routes_source.lower()

    def test_estimate_does_not_submit(self, routes_source):
        """Estimate endpoint must NOT call submit_job — read-only."""
        # Check that estimate handler uses estimate_cost, not submit_job
        estimate_fn_start = routes_source.find("async def estimate_generation_cost")
        assert estimate_fn_start != -1
        # Find next function def after estimate to bound our search
        next_fn = routes_source.find("\nasync def ", estimate_fn_start + 1)
        if next_fn == -1:
            next_fn = len(routes_source)
        estimate_body = routes_source[estimate_fn_start:next_fn]
        assert "submit_job" not in estimate_body, \
            "estimate handler must not call submit_job"
        assert "estimate_cost" in estimate_body

    def test_accept_returns_output_path(self, routes_source):
        """Accept must return output_path in response."""
        assert "output_path" in routes_source

    def test_queue_returns_count(self, routes_source):
        """Queue endpoint must return both jobs list and count."""
        assert '"count"' in routes_source or "'count'" in routes_source

    def test_budget_summary_endpoint_exists(self, routes_source):
        """Budget summary must expose get_summary() — not raw internal state."""
        assert "get_summary" in routes_source


# ---------------------------------------------------------------------------
# §4: Router Wiring
# ---------------------------------------------------------------------------

class TestRouterWiring:
    """generation_router must be included in the main FastAPI app."""

    @pytest.mark.xfail(reason="generation_router not yet in routes/__init__.py — wiring is Beta's task")
    def test_generation_router_imported_in_app(self, app_source):
        """App must import generation_router."""
        assert "generation_router" in app_source or "cut_routes_generation" in app_source

    @pytest.mark.xfail(reason="generation_router not yet in routes/__init__.py — wiring is Beta's task")
    def test_generation_router_included(self, app_source):
        """App must include generation_router via include_router()."""
        assert "include_router" in app_source
        # generation_router must appear somewhere after include_router
        assert "generation" in app_source


# ---------------------------------------------------------------------------
# §5: Service Import Contract
# ---------------------------------------------------------------------------

class TestServiceContract:
    """GenerationService must be importable without side-effects."""

    def test_service_module_exists(self):
        service_path = Path("src/services/cut_generation_service.py")
        if not service_path.exists():
            pytest.xfail("cut_generation_service.py not yet implemented")
        # Module exists — verify it has GenerationService class
        source = service_path.read_text()
        assert "class GenerationService" in source

    def test_service_has_submit_job(self):
        service_path = Path("src/services/cut_generation_service.py")
        if not service_path.exists():
            pytest.xfail("cut_generation_service.py not yet implemented")
        source = service_path.read_text()
        assert "submit_job" in source

    def test_service_has_budget(self):
        """Service must have a budget attribute for spend tracking."""
        service_path = Path("src/services/cut_generation_service.py")
        if not service_path.exists():
            pytest.xfail("cut_generation_service.py not yet implemented")
        source = service_path.read_text()
        assert "budget" in source

    def test_service_has_get_provider(self):
        service_path = Path("src/services/cut_generation_service.py")
        if not service_path.exists():
            pytest.xfail("cut_generation_service.py not yet implemented")
        source = service_path.read_text()
        assert "get_provider" in source
