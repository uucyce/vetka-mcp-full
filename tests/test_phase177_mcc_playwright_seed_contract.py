from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'mcc_seed_playwright_fixture.py'
STORE = ROOT / 'client/src/store/useMCCStore.ts'
MCC = ROOT / 'client/src/components/mcc/MyceliumCommandCenter.tsx'
FIXTURE = ROOT / 'tests/mcc/fixtures/playwright_mcc_graph_repo'


def test_playwright_seed_script_reuses_or_creates_fixture_project():
    text = SCRIPT.read_text()
    assert 'FIXTURE_ROOT = ROOT / "tests" / "mcc" / "fixtures" / "playwright_mcc_graph_repo"' in text
    assert 'projects/list' in text
    assert 'projects/activate' in text
    assert 'project/init' in text
    assert '"sandbox_path": sandbox_path' in text
    assert '"browser_url": browser_url' in text


def test_mcc_init_accepts_project_id_override_from_browser_query():
    store_text = STORE.read_text()
    mcc_text = MCC.read_text()
    assert 'initMCC: (projectIdOverride?: string) => Promise<void>;' in store_text
    assert "const projectId = String(projectIdOverride || '').trim();" in store_text
    assert "`${API_BASE}/mcc/init?project_id=${encodeURIComponent(projectId)}`" in store_text
    assert "new URLSearchParams(window.location.search).get('project_id')" in mcc_text
    assert 'initMCC(bootProjectId).then(() => {' in mcc_text


def test_playwright_fixture_repo_has_nested_descendants():
    assert (FIXTURE / 'pulse/src/music/notes.txt').exists()
    assert (FIXTURE / 'pulse/src/audio/mix.txt').exists()
    assert (FIXTURE / 'pulse/src/tauri/bridge.rs').exists()
    assert (FIXTURE / 'tests/scanners/fixtures/sample.json').exists()
