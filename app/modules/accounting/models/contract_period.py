"""Backward-compatible re-export. Canonical definition in common module."""
from app.modules.common.models.contract_period import ContractPeriod  # noqa: F401

__all__ = ["ContractPeriod"]
