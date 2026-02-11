# MARKER_138.S2_2_WORKFLOW_ROUTER_TEST
from src.jarvis.workflow_router import JarvisWorkflowRouter


def test_route_fix_intent():
    router = JarvisWorkflowRouter()
    plan = router.route("Fix bug in auth middleware")
    assert plan.workflow == "jarvis_fix"
    assert plan.phase_type == "fix"
    assert plan.preset == "dragon_silver"


def test_route_build_intent_voice_mode():
    router = JarvisWorkflowRouter()
    plan = router.route("Implement new feature", voice_mode=True)
    assert plan.workflow == "jarvis_build"
    assert plan.use_voice_pipeline is True


def test_route_research_intent():
    router = JarvisWorkflowRouter()
    plan = router.route("Research best vector db options")
    assert plan.workflow == "jarvis_research"
    assert plan.reasoning_depth == "high"


def test_route_fallback_chat():
    router = JarvisWorkflowRouter()
    plan = router.route("hello there")
    assert plan.workflow == "jarvis_chat"
