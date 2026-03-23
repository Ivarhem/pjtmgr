"""ContractSalesDetail lazy-create tests.

Note: These tests require a PostgreSQL test database with the accounting schema.
"""
from __future__ import annotations

import pytest

from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.schemas.contract import ContractCreate
from app.modules.common.schemas.contract_period import ContractPeriodCreate
from app.modules.accounting.schemas.contract_sales_detail import ContractSalesDetailUpdate


def _make_contract_and_period(db_session) -> tuple[int, int]:
    """Helper: Create a Contract + ContractPeriod, return (contract_id, period_id)."""
    from app.modules.common.services.contract_service import create_contract, create_period

    contract = create_contract(
        db_session,
        ContractCreate(contract_name="SalesDetail Test", contract_type="인프라"),
    )
    period = create_period(
        db_session,
        contract["id"],
        ContractPeriodCreate(period_year=2025),
    )
    return contract["id"], period["id"]


class TestContractSalesDetail:
    def test_get_or_create_creates_when_missing(self, db_session, admin_role_id):
        """SalesDetail 미존재 시 자동 생성."""
        from app.modules.accounting.services.contract_sales_detail import (
            get_or_create_sales_detail,
        )

        _, period_id = _make_contract_and_period(db_session)
        result = get_or_create_sales_detail(db_session, period_id)
        assert result["contract_period_id"] == period_id
        assert result["expected_revenue_amount"] == 0
        assert result["expected_gp_amount"] == 0

    def test_get_or_create_returns_existing(self, db_session, admin_role_id):
        """SalesDetail 존재 시 기존 반환."""
        from app.modules.accounting.services.contract_sales_detail import (
            get_or_create_sales_detail,
            update_sales_detail,
        )

        _, period_id = _make_contract_and_period(db_session)
        # 최초 생성
        first = get_or_create_sales_detail(db_session, period_id)
        # 값 변경 후
        update_sales_detail(
            db_session,
            period_id,
            ContractSalesDetailUpdate(expected_revenue_amount=1_000_000),
        )
        # 다시 조회 시 기존 반환
        second = get_or_create_sales_detail(db_session, period_id)
        assert second["id"] == first["id"]
        assert second["expected_revenue_amount"] == 1_000_000

    def test_update_sales_detail(self, db_session, admin_role_id):
        """SalesDetail 필드 갱신."""
        from app.modules.accounting.services.contract_sales_detail import (
            update_sales_detail,
        )

        _, period_id = _make_contract_and_period(db_session)
        updated = update_sales_detail(
            db_session,
            period_id,
            ContractSalesDetailUpdate(
                expected_revenue_amount=5_000_000,
                expected_gp_amount=2_000_000,
                inspection_day=15,
            ),
        )
        assert updated["expected_revenue_amount"] == 5_000_000
        assert updated["expected_gp_amount"] == 2_000_000
        assert updated["inspection_day"] == 15

    def test_field_names_use_amount_suffix(self, db_session, admin_role_id):
        """expected_revenue_amount, expected_gp_amount 필드명 확인."""
        from app.modules.accounting.services.contract_sales_detail import (
            get_or_create_sales_detail,
        )

        _, period_id = _make_contract_and_period(db_session)
        result = get_or_create_sales_detail(db_session, period_id)
        # Verify the keys use _amount suffix (not _total or bare name)
        assert "expected_revenue_amount" in result
        assert "expected_gp_amount" in result
