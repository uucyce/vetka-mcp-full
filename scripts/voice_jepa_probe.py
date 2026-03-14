#!/usr/bin/env python3
"""Gradient probe for JEPA-assisted voice condensation.

Usage:
  python scripts/voice_jepa_probe.py --source docs --min-words 10 --max-words 160 --step 10
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.progressive_tts_service import ProgressiveTtsService

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def read_sentences(root: Path, max_files: int = 120) -> list[str]:
    files = [p for p in root.rglob("*") if p.suffix.lower() in {".md", ".txt", ".py", ".ts", ".tsx", ".rtf"}]
    random.shuffle(files)
    out: list[str] = []
    for p in files[:max_files]:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for s in SENT_SPLIT.split(txt):
            s = " ".join(s.split()).strip()
            if len(s) >= 25:
                out.append(s)
            if len(out) >= 3000:
                return out
    return out


def build_text(pool: list[str], target_words: int) -> str:
    if not pool:
        return ""
    chunks = []
    words = 0
    i = 0
    while words < target_words and i < 200:
        s = random.choice(pool)
        chunks.append(s)
        words += len(s.split())
        i += 1
    text = " ".join(chunks).strip()
    return text


def run_probe(source: Path, min_words: int, max_words: int, step: int, runs_per_bucket: int) -> dict:
    pool = read_sentences(source)
    svc = ProgressiveTtsService()

    rows = []
    for target in range(min_words, max_words + 1, step):
        for run_i in range(runs_per_bucket):
            text = build_text(pool, target)
            sents = [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]
            reduced, trace = svc._condense_sentences_with_jepa(
                text=text,
                sentences=sents,
                session_key=f"probe-{target}",
            )
            rows.append(
                {
                    "target_words": target,
                    "run": run_i,
                    "input_words": len(text.split()),
                    "input_sentences": len(sents),
                    "output_sentences": len(reduced),
                    "trigger_raw": bool(trace.get("trigger_raw")),
                    "triggered": bool(trace.get("triggered")),
                    "provider_mode": str(trace.get("provider_mode") or ""),
                    "latency_ms": float(trace.get("latency_ms") or 0.0),
                    "reduction_ratio": float(trace.get("reduction_ratio") or 0.0),
                    "error": trace.get("error"),
                }
            )

    triggered = [r for r in rows if r["triggered"]]
    lat = sorted([r["latency_ms"] for r in triggered if r["latency_ms"] > 0.0])

    def pct(v: list[float], p: float) -> float:
        if not v:
            return 0.0
        idx = max(0, min(len(v) - 1, int((len(v) - 1) * p)))
        return round(v[idx], 3)

    return {
        "config": {
            "min_words": min_words,
            "max_words": max_words,
            "step": step,
            "runs_per_bucket": runs_per_bucket,
        },
        "rows": rows,
        "summary": {
            "total_runs": len(rows),
            "triggered_runs": len(triggered),
            "trigger_rate": round(len(triggered) / max(1, len(rows)), 4),
            "latency_ms_p50": pct(lat, 0.5),
            "latency_ms_p95": pct(lat, 0.95),
            "avg_reduction_ratio": round(
                sum(r["reduction_ratio"] for r in triggered) / max(1, len(triggered)),
                4,
            ),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="docs")
    ap.add_argument("--min-words", type=int, default=10)
    ap.add_argument("--max-words", type=int, default=160)
    ap.add_argument("--step", type=int, default=10)
    ap.add_argument("--runs-per-bucket", type=int, default=5)
    ap.add_argument("--out", default="docs/157_ph/voice_jepa_probe_latest.json")
    args = ap.parse_args()

    report = run_probe(
        source=Path(args.source),
        min_words=args.min_words,
        max_words=args.max_words,
        step=args.step,
        runs_per_bucket=args.runs_per_bucket,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    print(f"saved={out}")


if __name__ == "__main__":
    main()
