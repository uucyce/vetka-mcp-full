import json
from pathlib import Path


PULSE_PROCESSED = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/pulse/data/processed")
TRAIN_MANIFEST = PULSE_PROCESSED / "jepa_training_manifest.jsonl"
EVAL_SUBSET = PULSE_PROCESSED / "jepa_eval_subset.jsonl"
CALIB_PACK = PULSE_PROCESSED / "jepa_calibration_pack.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _coverage(rows: list[dict], field: str) -> float:
    if not rows:
        return 0.0
    filled = sum(1 for r in rows if r.get(field) is not None)
    return float(filled) / float(len(rows))


def test_phase158_pulse_dataset_quality_gate():
    assert TRAIN_MANIFEST.exists(), f"missing: {TRAIN_MANIFEST}"
    assert EVAL_SUBSET.exists(), f"missing: {EVAL_SUBSET}"
    assert CALIB_PACK.exists(), f"missing: {CALIB_PACK}"

    train = _load_jsonl(TRAIN_MANIFEST)
    eval_rows = _load_jsonl(EVAL_SUBSET)
    calib = _load_jsonl(CALIB_PACK)

    assert len(train) >= 300, f"train rows too low: {len(train)}"
    assert len(eval_rows) >= 250, f"eval rows too low: {len(eval_rows)}"
    assert len(calib) >= 100, f"calibration rows too low: {len(calib)}"

    for label, rows in (("train", train), ("eval", eval_rows), ("calib", calib)):
        bpm_cov = _coverage(rows, "bpm_ref")
        key_cov = _coverage(rows, "key_ref")
        scale_cov = _coverage(rows, "scale_ref")
        assert bpm_cov >= 0.95, f"{label}.bpm_ref coverage too low: {bpm_cov:.3f}"
        assert key_cov >= 0.95, f"{label}.key_ref coverage too low: {key_cov:.3f}"
        assert scale_cov >= 0.95, f"{label}.scale_ref coverage too low: {scale_cov:.3f}"

    by_dataset: dict[str, int] = {}
    for row in train:
        ds = str(row.get("dataset") or "unknown")
        by_dataset[ds] = by_dataset.get(ds, 0) + 1
    assert len(by_dataset) >= 2, f"dataset diversity too low: {by_dataset}"
    assert min(by_dataset.values()) >= 50, f"minor dataset too small: {by_dataset}"
