"""Backward-compatible re-export. Canonical definition in common module."""
from app.modules.common.models.contract_type_config import ContractTypeConfig  # noqa: F401

__all__ = ["ContractTypeConfig"]
