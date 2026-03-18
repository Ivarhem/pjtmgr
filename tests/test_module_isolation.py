"""Module isolation test: verify import boundaries using AST analysis.

Rules (target state):
- core imports nothing from modules.*
- modules.common imports nothing from modules.accounting or modules.infra
- modules.accounting may import from modules.common but not modules.infra
- modules.infra may import from modules.common but not modules.accounting

During migration (Tasks 3-6), known violations are tracked and excluded.
They will be resolved in Tasks 4-6 and then removed from the exclusion set.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path

# Allowed import prefixes per source area
_ALLOWED: dict[str, list[str]] = {
    "app/core/": [
        "app.core.",
        "app.core",  # bare 'from app.core import X'
    ],
    "app/modules/common/": [
        "app.core.",
        "app.modules.common.",
    ],
    "app/modules/accounting/": [
        "app.core.",
        "app.modules.common.",
        "app.modules.accounting.",
    ],
    "app/modules/infra/": [
        "app.core.",
        "app.modules.common.",
        "app.modules.infra.",
    ],
}

# Known violations to be resolved in later migration tasks.
# Format: "relative/path.py" — the entire file is exempted.
# Remove entries as violations are fixed in Tasks 4-6.
_KNOWN_VIOLATION_FILES: set[str] = {
    # core/ -> modules.*: app_factory wires all modules (Task 4: module registry)
    "app/core/app_factory.py",
    # core/pages.py imports common.services (Task 4: split pages into modules)
    "app/core/pages.py",
    # core/auth/ imports common/accounting models (Task 5: auth interface extraction)
    "app/core/auth/authorization.py",
    "app/core/auth/dependencies.py",
    "app/core/auth/router.py",
    "app/core/auth/service.py",
    # core/startup/ imports module services (Task 4: module-aware bootstrap)
    "app/core/startup/bootstrap.py",
    # common -> accounting cross-deps (Task 5: dependency inversion)
    "app/modules/common/routers/users.py",
    "app/modules/common/services/customer.py",
    "app/modules/common/services/user.py",
    "app/modules/common/services/_customer_helpers.py",
}

# These are always allowed (standard lib, third-party, or top-level app)
_GLOBAL_ALLOWED_PREFIXES = (
    "app.core.",
    "app.modules.",
    "app.main",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _collect_python_files(directory: Path) -> list[Path]:
    """Recursively collect .py files, skipping __pycache__."""
    result = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                result.append(Path(root) / f)
    return result


def _extract_app_imports(filepath: Path) -> list[tuple[int, str]]:
    """Parse a Python file and return (line_number, module_path) for app.* imports."""
    source = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("app."):
                imports.append((node.lineno, node.module))
    return imports


def _get_area(filepath: Path) -> str | None:
    """Determine which area a file belongs to based on its path."""
    rel = filepath.relative_to(PROJECT_ROOT).as_posix()
    for area in _ALLOWED:
        if rel.startswith(area):
            return area
    return None


def test_module_boundaries() -> None:
    """Ensure no module imports from a forbidden peer module (excluding known violations)."""
    violations: list[str] = []

    for area, allowed_prefixes in _ALLOWED.items():
        area_path = PROJECT_ROOT / area
        if not area_path.exists():
            continue

        for pyfile in _collect_python_files(area_path):
            rel_path = pyfile.relative_to(PROJECT_ROOT).as_posix()
            if rel_path in _KNOWN_VIOLATION_FILES:
                continue
            for lineno, module_path in _extract_app_imports(pyfile):
                # Check if import is allowed for this area
                if not any(module_path.startswith(prefix) for prefix in allowed_prefixes):
                    violations.append(
                        f"{rel_path}:{lineno} imports '{module_path}' "
                        f"(area '{area}' only allows: {allowed_prefixes})"
                    )

    if violations:
        msg = "Module isolation violations found:\n" + "\n".join(f"  - {v}" for v in violations)
        raise AssertionError(msg)


def test_known_violations_still_exist() -> None:
    """Ensure known violation files still exist (remove from set when fixed)."""
    for filepath in _KNOWN_VIOLATION_FILES:
        assert (PROJECT_ROOT / filepath).exists(), (
            f"Known violation file '{filepath}' no longer exists. "
            f"Remove it from _KNOWN_VIOLATION_FILES."
        )


def test_no_old_flat_imports() -> None:
    """Ensure no file uses the old flat import paths (app.models.X, app.services.X, etc.)."""
    old_prefixes = (
        "app.models.",
        "app.schemas.",
        "app.services.",
        "app.routers.",
        "app.auth.",
        "app.startup.",
        "app.config",
        "app.database",
        "app.exceptions",
        "app.app_factory",
    )

    # Exclude docs/inframgr-reference and alembic versions
    exclude_dirs = {"docs", "alembic", ".venv", "__pycache__", ".git"}

    violations: list[str] = []
    search_dirs = [PROJECT_ROOT / "app", PROJECT_ROOT / "tests"]

    for search_dir in search_dirs:
        for pyfile in _collect_python_files(search_dir):
            rel_path = pyfile.relative_to(PROJECT_ROOT).as_posix()
            for lineno, module_path in _extract_app_imports(pyfile):
                if any(module_path.startswith(p) or module_path == p for p in old_prefixes):
                    violations.append(f"{rel_path}:{lineno} uses old import '{module_path}'")

    if violations:
        msg = "Old flat import paths still in use:\n" + "\n".join(f"  - {v}" for v in violations)
        raise AssertionError(msg)


def test_core_modules_importable() -> None:
    """Verify key modules are importable (syntax check)."""
    import importlib

    modules = [
        "app.core.config",
        "app.core.exceptions",
        "app.core.base_model",
        "app.core._normalize",
        "app.core.auth.constants",
        "app.core.auth.password",
        "app.core.auth.middleware",
        "app.modules.common.schemas.user",
        "app.modules.common.schemas.customer",
        "app.modules.accounting.schemas.contract",
        "app.modules.accounting.schemas.report",
    ]
    for mod in modules:
        importlib.import_module(mod)
