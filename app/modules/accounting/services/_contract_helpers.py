"""Contract 도메인 공유 헬퍼.

여러 서비스 모듈(transaction_line, receipt, monthly_forecast)에서
공통으로 사용하는 완료 기간 검사 함수를 모아 둔다.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.modules.accounting.models.contract_period import ContractPeriod


def check_period_not_completed(
    db: Session, contract_id: int, revenue_month: str | None = None
) -> None:
    """해당 사업의 완료된 period에 속하는 월이면 수정 차단."""
    if not revenue_month:
        return
    period = (
        db.query(ContractPeriod)
        .filter(
            ContractPeriod.contract_id == contract_id,
            ContractPeriod.is_completed.is_(True),
            ContractPeriod.start_month <= revenue_month,
            ContractPeriod.end_month >= revenue_month,
        )
        .first()
    )
    if period:
        raise BusinessRuleError("완료된 귀속기간의 데이터는 수정할 수 없습니다.")


def check_periods_not_completed(
    db: Session,
    contract_id: int,
    *months: str | None,
) -> None:
    """현재 월과 변경 대상 월 모두 완료 기간 여부를 검사한다."""
    checked: set[str] = set()
    for month in months:
        if not month or month in checked:
            continue
        checked.add(month)
        check_period_not_completed(db, contract_id, month)
