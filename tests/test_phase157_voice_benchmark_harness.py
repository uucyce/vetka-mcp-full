import json
import subprocess
from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 157 contracts changed")

ROOT = Path(__file__).resolve().parents[1]


def test_voice_benchmark_harness_dry_run_outputs_files():
    script = ROOT / "scripts/voice_mode_benchmark.py"
    assert script.exists()

    proc = subprocess.run(
        ["python3", str(script), "--dry-run", "--runs-per-prompt", "1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout
    assert "A_qwen_only" in out
    assert "B_api_tts" in out
    assert "C_api_jepa_tts" in out
    assert "D_ollama_tts" in out
    assert "E_ollama_jepa_tts" in out
    assert "F_mimo_short" in out

    bench_dir = ROOT / "docs/157_ph/benchmarks"
    files = sorted(bench_dir.glob("phase157_voice_ab_test_dry_*.json"))
    md_files = sorted(bench_dir.glob("phase157_voice_ab_test_dry_*.md"))
    assert files, "dry-run json benchmark file was not created"
    assert md_files, "dry-run markdown benchmark report was not created"

    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    assert payload.get("dry_run") is True
    assert "rows" in payload and isinstance(payload["rows"], list)
    assert "summary" in payload and "modes" in payload["summary"]
