#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_URL = os.getenv("CATALOG_RESEARCH_SERVICE_URL") or "http://127.0.0.1:8765"
DEFAULT_TOKEN = os.getenv("CATALOG_RESEARCH_SERVICE_TOKEN") or ""
DEFAULT_SAMPLES = Path(__file__).with_name("fixtures") / "catalog_research_benchmark_samples.json"


def _post_json(url: str, payload: dict[str, Any], token: str, timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            **({"authorization": f"Bearer {token}"} if token else {}),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _score(result: dict[str, Any]) -> dict[str, Any]:
    spec = result.get("hardware_spec") or {}
    eosl = result.get("eosl") or {}
    interfaces = result.get("interfaces") or []

    spec_url = bool(spec.get("spec_url"))
    size_unit = spec.get("size_unit") is not None
    eosl_dates = bool(eosl.get("eos_date") or eosl.get("eosl_date"))
    eosl_url = bool(eosl.get("source_url"))
    iface_any = len(interfaces) > 0
    iface_structured = any((item.get("count") and item.get("interface_type")) for item in interfaces if isinstance(item, dict))

    filled = sum([spec_url, size_unit, eosl_dates, eosl_url, iface_any, iface_structured])
    return {
        "spec_url": spec_url,
        "size_unit": size_unit,
        "eosl_dates": eosl_dates,
        "eosl_url": eosl_url,
        "interfaces_any": iface_any,
        "interfaces_structured": iface_structured,
        "filled_signals": filled,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Benchmark catalog research output quality.")
    ap.add_argument("--samples", default=str(DEFAULT_SAMPLES))
    ap.add_argument("--service-url", default=DEFAULT_URL)
    ap.add_argument("--token", default=DEFAULT_TOKEN)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--output", default="")
    args = ap.parse_args()

    samples = json.loads(Path(args.samples).read_text())
    if args.max > 0:
        samples = samples[: args.max]

    rows: list[dict[str, Any]] = []
    lookup_url = args.service_url.rstrip("/") + "/lookup-hardware"
    for sample in samples:
        payload = {
            "vendor": sample["vendor"],
            "name": sample["name"],
            "classification": sample.get("classification"),
            "reference_url": sample.get("reference_url") or "",
        }
        started = time.time()
        try:
            result = _post_json(lookup_url, payload, args.token, args.timeout)
            elapsed = round(time.time() - started, 2)
            metrics = _score(result)
            rows.append({
                "vendor": sample["vendor"],
                "name": sample["name"],
                "classification": sample.get("classification"),
                "focus": sample.get("focus") or [],
                "elapsed_sec": elapsed,
                "confidence": result.get("confidence"),
                "metrics": metrics,
                "result": result,
                "error": None,
            })
            print(f"OK   {sample['vendor']} {sample['name']}  {elapsed}s  signals={metrics['filled_signals']}")
        except Exception as exc:
            elapsed = round(time.time() - started, 2)
            rows.append({
                "vendor": sample["vendor"],
                "name": sample["name"],
                "classification": sample.get("classification"),
                "focus": sample.get("focus") or [],
                "elapsed_sec": elapsed,
                "confidence": None,
                "metrics": None,
                "result": None,
                "error": str(exc),
            })
            print(f"ERR  {sample['vendor']} {sample['name']}  {elapsed}s  {exc}", file=sys.stderr)

    successes = [row for row in rows if not row["error"]]
    summary = {
        "total": len(rows),
        "success": len(successes),
        "failed": len(rows) - len(successes),
        "avg_elapsed_sec": round(sum(r["elapsed_sec"] for r in rows) / len(rows), 2) if rows else 0,
        "coverage": {
            "spec_url": sum(1 for r in successes if r["metrics"]["spec_url"]),
            "size_unit": sum(1 for r in successes if r["metrics"]["size_unit"]),
            "eosl_dates": sum(1 for r in successes if r["metrics"]["eosl_dates"]),
            "eosl_url": sum(1 for r in successes if r["metrics"]["eosl_url"]),
            "interfaces_any": sum(1 for r in successes if r["metrics"]["interfaces_any"]),
            "interfaces_structured": sum(1 for r in successes if r["metrics"]["interfaces_structured"]),
        },
    }

    report = {"service_url": args.service_url, "samples": rows, "summary": summary}
    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
