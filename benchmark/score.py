from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def load(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: {exc}") from exc
    if not rows:
        raise SystemExit(f"No benchmark rows in {path}")
    return rows


def ratio(rows: list[dict], numerator: str, denominator: str) -> float:
    top = sum(float(row.get(numerator, 0)) for row in rows)
    bottom = sum(float(row.get(denominator, 0)) for row in rows)
    return top / bottom if bottom else 0.0


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * quantile))))
    return ordered[index]


def summarize(rows: list[dict]) -> dict:
    latencies = [float(row["latency_ms"]) for row in rows]
    return {
        "pages": len(rows),
        "languages": {lang: sum(row.get("language") == lang for row in rows) for lang in ("ja", "ko")},
        "detection": ratio(rows, "detected_regions", "expected_regions"),
        "ocr": ratio(rows, "ocr_correct", "ocr_chars"),
        "glossary": sum(bool(row.get("glossary_ok")) for row in rows) / len(rows),
        "translation": statistics.fmean(float(row.get("translation_score", 0)) for row in rows),
        "cleaning": ratio(rows, "clean_regions", "expected_regions"),
        "layout": ratio(rows, "layout_regions", "detected_regions"),
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "crashes": sum(bool(row.get("crash")) for row in rows),
    }


parser = argparse.ArgumentParser()
parser.add_argument("results", type=Path)
parser.add_argument("--baseline", type=Path)
args = parser.parse_args()
summary = summarize(load(args.results))
payload = {"current": summary}
if args.baseline:
    baseline = summarize(load(args.baseline))
    payload["baseline"] = baseline
    payload["delta"] = {
        key: summary[key] - baseline[key]
        for key in ("detection", "ocr", "glossary", "translation", "cleaning", "layout", "p50_ms", "p95_ms", "crashes")
    }
print(json.dumps(payload, ensure_ascii=False, indent=2))

