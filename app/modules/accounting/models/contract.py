"""Backward-compatible re-export. Canonical definition in common module."""
from app.modules.common.models.contract import Contract  # noqa: F401

__all__ = ["Contract"]
