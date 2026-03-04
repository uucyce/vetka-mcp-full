from pathlib import Path

from src.search import file_search_service as svc


def test_allowed_search_roots_uses_project_and_parent(tmp_path, monkeypatch):
    workspace_parent = tmp_path / "workspace"
    project_root = workspace_parent / "proj"
    project_root.mkdir(parents=True)

    monkeypatch.chdir(project_root)
    roots = svc._allowed_search_roots("walk")
    root_paths = {p.resolve() for p in roots}
    assert project_root.resolve() in root_paths
    assert workspace_parent.resolve() in root_paths


def test_search_files_filename_walk_mode(tmp_path, monkeypatch):
    project_root = tmp_path / "proj"
    src_dir = project_root / "src"
    src_dir.mkdir(parents=True)
    match_file = src_dir / "hello_world.md"
    match_file.write_text("hello", encoding="utf-8")
    other_file = src_dir / "other.txt"
    other_file.write_text("something else", encoding="utf-8")

    monkeypatch.chdir(project_root)
    # Force fallback provider path without mdfind/fd/rg.
    monkeypatch.setattr(svc, "_detect_provider", lambda: "walk")
    monkeypatch.setattr(svc, "_allowed_search_roots", lambda provider: [project_root.resolve()])

    result = svc.search_files(
        query="hello",
        limit=10,
        mode="filename",
    )

    assert result["success"] is True
    assert result["count"] >= 1
    hits = result["results"]
    assert any("hello_world.md" in h.get("title", "") for h in hits)


def test_search_files_filename_mdfind_falls_back_to_walk(tmp_path, monkeypatch):
    project_root = tmp_path / "proj"
    docs_dir = project_root / "docs"
    docs_dir.mkdir(parents=True)
    match_file = docs_dir / "fallback_hit.md"
    match_file.write_text("x", encoding="utf-8")

    monkeypatch.chdir(project_root)
    monkeypatch.setattr(svc, "_detect_provider", lambda: "mdfind")
    monkeypatch.setattr(svc, "_name_search_mdfind", lambda root, query, limit: [])
    monkeypatch.setattr(svc, "_allowed_search_roots", lambda provider: [project_root.resolve()])

    result = svc.search_files(query="fallback", limit=10, mode="filename")
    assert result["success"] is True
    assert any("fallback_hit.md" in h.get("title", "") for h in result["results"])


def test_rerank_deprioritizes_test_noise_for_descriptive_queries():
    items = [
        {
            "path": "/repo/tests/fixtures/MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md",
            "snippet": "fixture copy",
            "score": 0.95,
        },
        {
            "path": "/repo/docs/157_ph/MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md",
            "snippet": "canonical doc",
            "score": 0.92,
        },
    ]

    ranked = svc._rerank_items(items, "Найди runtime map phase 157")
    top = ranked[0]["path"]
    assert "/docs/157_ph/" in top
