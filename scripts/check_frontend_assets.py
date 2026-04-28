#!/usr/bin/env python3
"""Static frontend safety checks for vendor assets and critical JS files."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def require_file(path: str, min_bytes: int = 1, contains: str | None = None) -> None:
    full = ROOT / path
    if not full.exists():
        fail(f"missing {path}")
    size = full.stat().st_size
    if size < min_bytes:
        fail(f"{path} too small: {size} bytes < {min_bytes}")
    if contains is not None and contains not in full.read_text(errors="ignore"):
        fail(f"{path} does not contain expected marker {contains!r}")
    ok(f"{path} present ({size} bytes)")


def check_template_versions() -> None:
    base = (ROOT / "app/templates/base.html").read_text()
    expected = [
        "/static/vendor/ag-grid/ag-grid-community.min.js?v=32.0.0b",
        "/static/vendor/ag-grid/ag-grid.css",
        "/static/vendor/ag-grid/ag-theme-quartz.css",
        "/api/v1/auth/bootstrap",
    ]
    for marker in expected:
        if marker not in base:
            fail(f"base.html missing {marker}")
    if re.search(r"https?://(?:cdn\.jsdelivr\.net|unpkg\.com|fonts\.googleapis\.com|cdn\.orioncactus\.com)", base):
        fail("base.html still references blocked external CDN/font hosts")
    ok("base.html uses local vendor/bootstrap references")


def node_check(path: str) -> None:
    proc = subprocess.run(["node", "--check", path], cwd=ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        fail(f"node --check {path} failed\n{proc.stdout}\n{proc.stderr}")
    ok(f"node syntax OK: {path}")


def main() -> None:
    require_file("app/static/vendor/ag-grid/ag-grid-community.min.js", 1_000_000, "agGrid")
    require_file("app/static/vendor/ag-grid/ag-grid.css", 10_000)
    require_file("app/static/vendor/ag-grid/ag-theme-quartz.css", 10_000)
    require_file("app/static/vendor/chartjs/chart.umd.js", 100_000, "Chart")
    require_file("app/static/js/utils.js", 10_000)
    check_template_versions()
    for path in [
        "app/static/js/utils.js",
        "app/static/js/infra_assets.js",
        "app/static/js/infra_product_catalog.js",
    ]:
        node_check(path)


if __name__ == "__main__":
    main()
