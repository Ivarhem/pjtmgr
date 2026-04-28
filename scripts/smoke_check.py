#!/usr/bin/env python3
"""Lightweight runtime smoke checks for PJT Manager.

This script intentionally avoids mutating data. It can run inside the app
container or on a host with project dependencies installed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        fail(f"{' '.join(cmd)} failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout.strip()


def check_imports() -> None:
    sys.path.insert(0, str(ROOT))
    from app.main import app  # noqa: WPS433

    route_paths = {getattr(route, "path", "") for route in app.routes}
    required = {"/api/v1/health", "/api/v1/auth/bootstrap"}
    missing = sorted(required - route_paths)
    if missing:
        fail(f"missing routes: {', '.join(missing)}")
    ok(f"app imports and registers {len(route_paths)} routes")


def check_alembic() -> None:
    heads = run(["alembic", "heads"])
    current = run(["alembic", "current"])
    if "0082" not in heads:
        fail(f"expected Alembic head 0082, got: {heads}")
    if "0082" not in current:
        fail(f"database is not at head 0082, current: {current}")
    ok("Alembic head/current at 0082")


def check_http(base_url: str) -> None:
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/v1/health", timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") != "ok" or payload.get("db") != "ok":
        fail(f"unhealthy payload: {payload}")
    ok(f"health endpoint OK at {base_url}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9000")
    parser.add_argument("--skip-http", action="store_true")
    parser.add_argument("--skip-alembic", action="store_true")
    args = parser.parse_args()

    check_imports()
    if not args.skip_alembic:
        check_alembic()
    if not args.skip_http:
        check_http(args.base_url)


if __name__ == "__main__":
    main()
