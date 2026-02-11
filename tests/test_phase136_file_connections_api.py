# MARKER_136.FILE_CONNECTIONS_API_TEST
import asyncio

from src.api.handlers.file_connections import build_file_connections
from src.api.routes import files_routes


def test_build_file_connections_imports_and_referenced_by(tmp_path):
    a_py = tmp_path / "a.py"
    b_py = tmp_path / "b.py"
    c_py = tmp_path / "c.py"

    a_py.write_text("import b\n", encoding="utf-8")
    b_py.write_text("VALUE = 1\n", encoding="utf-8")
    c_py.write_text("import a\n", encoding="utf-8")

    result = build_file_connections(
        target_file=str(a_py),
        project_root=str(tmp_path),
        max_connections=50,
    )

    assert result["file"] == str(a_py.resolve())
    connections = result["connections"]
    assert any(c["target"] == str(b_py.resolve()) and c["relation_type"] == "imports" for c in connections)
    assert any(c["target"] == str(c_py.resolve()) and c["relation_type"] == "referenced_by" for c in connections)


def test_build_file_connections_missing_file(tmp_path):
    missing = tmp_path / "missing.py"
    result = build_file_connections(
        target_file=str(missing),
        project_root=str(tmp_path),
        max_connections=20,
    )
    assert result["connections"] == []
    assert "error" in result


def test_route_get_file_connections_with_path_override(monkeypatch, tmp_path):
    target = tmp_path / "demo.py"
    target.write_text("x=1\n", encoding="utf-8")

    def fake_build_file_connections(target_file, project_root, max_connections):  # noqa: ARG001
        return {
            "file": target_file,
            "connections": [{"target": "x.py", "score": 1.0, "relation_type": "imports", "via": "import x"}],
        }

    monkeypatch.setattr(
        "src.api.handlers.file_connections.build_file_connections",
        fake_build_file_connections,
    )

    payload = asyncio.run(
        files_routes.get_file_connections(
            file_id="ignored-id",
            path=str(target),
            max_connections=5,
        )
    )

    assert payload["success"] is True
    assert payload["file"] == str(target.resolve())
    assert len(payload["connections"]) == 1

