import builtins
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_project_digest.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("update_project_digest", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_get_mcp_status_when_requests_missing(monkeypatch):
    module = _load_module()
    original_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ModuleNotFoundError("No module named 'requests'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    status = module.get_mcp_status()

    assert status["status"] == "degraded"
    assert "requests" in status["error"]
