import logging
import os
import re

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.database import Base, engine
from app.routers import customers, dashboard, contracts, contract_contacts, contract_types, term_configs, excel, reports, users, settings, user_preferences
from app.auth.router import router as auth_router
from app.auth.middleware import AuthMiddleware
from app.exceptions import NotFoundError, BusinessRuleError, DuplicateError, PermissionDeniedError, UnauthorizedError, ValidationError
from app.models import (  # noqa: F401 - 테이블 생성을 위해 모두 import
    User, Customer, CustomerContact, CustomerContactRole, Contract, ContractContact, ContractPeriod, MonthlyForecast, TransactionLine, Receipt, Setting, UserPreference, ContractTypeConfig, TermConfig
)
from app.config import (
    BOOTSTRAP_ADMIN_LOGIN_ID,
    BOOTSTRAP_ADMIN_NAME,
    BOOTSTRAP_ADMIN_PASSWORD,
    DEFAULT_HOME,
    ENV,
    SESSION_SECRET_KEY,
)

# ── 로깅 설정 ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sales")

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MIGRATION_TABLES = {
    "allocations",
    "audit_logs",
    "contract_contacts",
    "contract_periods",
    "customer_contact_roles",
    "customer_contacts",
    "contract_type_configs",
    "contracts",
    "deal_contacts",
    "deal_periods",
    "deal_type_configs",
    "deals",
    "monthly_actuals",
    "monthly_forecasts",
    "payments",
    "receipt_matches",
    "receipts",
    "transaction_lines",
}
_MIGRATION_COLUMNS = {
    "actual_id",
    "allocated_amount",
    "contact_type",
    "customer_contact_id",
    "customer_contact_roles",
    "is_default",
    "name",
    "phone",
    "email",
    "rank",
    "role_type",
    "contract_code",
    "contract_id",
    "contract_name",
    "contract_type",
    "counterparty_id",
    "customer_id",
    "deal_code",
    "deal_id",
    "deal_name",
    "deal_period_id",
    "deal_type",
    "expected_revenue_total",
    "expected_sales_total",
    "match_type",
    "matched_amount",
    "payment_date",
    "payment_id",
    "receipt_id",
    "revenue_amount",
    "sales_amount",
    "transaction_line_id",
}


def _validated_identifier(name: str, *, allowed: set[str]) -> str:
    if name not in allowed or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsupported SQL identifier: {name}")
    return f'"{name}"'

app = FastAPI(title="영업관리 시스템")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def _run_migrations() -> None:
    """기존 테이블에 누락된 컬럼/테이블을 추가하는 경량 마이그레이션."""
    from sqlalchemy import inspect, text

    def _table_names(inspector) -> set[str]:
        return set(inspector.get_table_names())

    def _has_table(inspector, table_name: str) -> bool:
        return table_name in _table_names(inspector)

    def _table_count(conn, table_name: str) -> int:
        safe_table = _validated_identifier(table_name, allowed=_MIGRATION_TABLES)
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {safe_table}")).scalar() or 0)

    def _table_columns(inspector, table_name: str) -> set[str]:
        if not _has_table(inspector, table_name):
            return set()
        return {c["name"] for c in inspector.get_columns(table_name)}

    def _copy_table_rows(
        conn,
        inspector,
        *,
        old_table: str,
        new_table: str,
        column_map: dict[str, str],
        transforms: dict[str, str] | None = None,
    ) -> bool:
        """구 테이블 데이터가 남아 있고 신 테이블이 비어 있으면 복사한다."""
        if not (_has_table(inspector, old_table) and _has_table(inspector, new_table)):
            return False
        old_count = _table_count(conn, old_table)
        new_count = _table_count(conn, new_table)
        if old_count == 0 or new_count > 0:
            return False

        new_columns = _table_columns(inspector, new_table)
        old_columns = _table_columns(inspector, old_table)
        select_exprs: list[str] = []
        insert_cols: list[str] = []

        for new_col, old_col in column_map.items():
            if new_col not in new_columns or old_col not in old_columns:
                continue
            safe_new_col = _validated_identifier(new_col, allowed=_MIGRATION_COLUMNS)
            safe_old_col = _validated_identifier(old_col, allowed=_MIGRATION_COLUMNS)
            expr = (transforms or {}).get(new_col, safe_old_col)
            insert_cols.append(safe_new_col)
            select_exprs.append(f"{expr} AS {safe_new_col}")

        if not insert_cols:
            return False

        safe_new_table = _validated_identifier(new_table, allowed=_MIGRATION_TABLES)
        safe_old_table = _validated_identifier(old_table, allowed=_MIGRATION_TABLES)
        conn.execute(
            text(
                f"INSERT INTO {safe_new_table} ({', '.join(insert_cols)}) "
                f"SELECT {', '.join(select_exprs)} FROM {safe_old_table}"
            )
        )
        conn.commit()
        logger.info(
            "복구 마이그레이션: %s → %s 데이터 %s건 복사",
            old_table,
            new_table,
            old_count,
        )
        return True

    with engine.connect() as conn:
        inspector = inspect(engine)
        table_names = _table_names(inspector)

        # payments → receipts 테이블 리네임
        if "payments" in table_names and "receipts" not in table_names:
            conn.execute(text("ALTER TABLE payments RENAME TO receipts"))
            conn.execute(text("ALTER TABLE receipts RENAME COLUMN payment_date TO receipt_date"))
            conn.commit()
            logger.info("마이그레이션: payments → receipts 테이블/컬럼 리네임")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # allocations → receipt_matches 테이블 리네임
        if "allocations" in table_names and "receipt_matches" not in table_names:
            conn.execute(text("ALTER TABLE allocations RENAME TO receipt_matches"))
            conn.execute(text("ALTER TABLE receipt_matches RENAME COLUMN payment_id TO receipt_id"))
            conn.execute(text("ALTER TABLE receipt_matches RENAME COLUMN allocated_amount TO matched_amount"))
            conn.execute(text("ALTER TABLE receipt_matches RENAME COLUMN allocation_type TO match_type"))
            conn.commit()
            logger.info("마이그레이션: allocations → receipt_matches 테이블/컬럼 리네임")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # receipt_matches 테이블 생성 (신규 DB용)
        if "receipt_matches" not in table_names:
            conn.execute(text("""
                CREATE TABLE receipt_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
                    transaction_line_id INTEGER NOT NULL REFERENCES transaction_lines(id) ON DELETE CASCADE,
                    matched_amount INTEGER NOT NULL,
                    match_type VARCHAR(20) NOT NULL DEFAULT 'auto',
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(receipt_id, transaction_line_id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_receipt_matches_receipt_id ON receipt_matches(receipt_id)"))
            conn.execute(text("CREATE INDEX ix_receipt_matches_transaction_line_id ON receipt_matches(transaction_line_id)"))
            conn.commit()
            logger.info("마이그레이션: receipt_matches 테이블 생성")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # monthly_actuals: counterparty_id → customer_id 컬럼명 변경
        ma_cols = _table_columns(inspector, "monthly_actuals")
        if "counterparty_id" in ma_cols and "customer_id" not in ma_cols:
            conn.execute(text(
                "ALTER TABLE monthly_actuals RENAME COLUMN counterparty_id TO customer_id"
            ))
            conn.commit()
            logger.info("마이그레이션: monthly_actuals.counterparty_id → customer_id 컬럼명 변경")
            inspector = inspect(engine)
            table_names = _table_names(inspector)
            ma_cols = _table_columns(inspector, "monthly_actuals")

        # Phase 2: sales → revenue 용어 변경
        # monthly_actuals.line_type: "sales" → "revenue" 값 변경
        # monthly_forecasts: sales_amount → revenue_amount 컬럼 리네임
        # deal_periods / contract_periods: expected_sales_total → expected_revenue_total 컬럼 리네임
        if "monthly_actuals" in table_names:
            # line_type 값 변경
            conn.execute(text("UPDATE monthly_actuals SET line_type = 'revenue' WHERE line_type = 'sales'"))
            conn.commit()
            logger.info("마이그레이션: monthly_actuals.line_type 'sales' → 'revenue'")

        if "monthly_forecasts" in table_names:
            mf_cols = _table_columns(inspector, "monthly_forecasts")
            if "sales_amount" in mf_cols and "revenue_amount" not in mf_cols:
                conn.execute(text("ALTER TABLE monthly_forecasts RENAME COLUMN sales_amount TO revenue_amount"))
                conn.commit()
                logger.info("마이그레이션: monthly_forecasts.sales_amount → revenue_amount")
                inspector = inspect(engine)
                table_names = _table_names(inspector)

        # deal_periods or contract_periods: expected_sales_total → expected_revenue_total
        for tbl_name in ("deal_periods", "contract_periods"):
            if tbl_name in table_names:
                dp_cols = _table_columns(inspector, tbl_name)
                if "expected_sales_total" in dp_cols and "expected_revenue_total" not in dp_cols:
                    safe_table = _validated_identifier(tbl_name, allowed=_MIGRATION_TABLES)
                    conn.execute(text(
                        f"ALTER TABLE {safe_table} "
                        "RENAME COLUMN expected_sales_total TO expected_revenue_total"
                    ))
                    conn.commit()
                    logger.info(f"마이그레이션: {tbl_name}.expected_sales_total → expected_revenue_total")
                    inspector = inspect(engine)
                    table_names = _table_names(inspector)

        # deal_periods에 customer_id 컬럼 추가 (Period별 매출처) — deal_periods 또는 contract_periods
        for tbl_name in ("deal_periods", "contract_periods"):
            if tbl_name in table_names:
                dp_cols = _table_columns(inspector, tbl_name)
                if "customer_id" not in dp_cols:
                    conn.execute(text(
                        f"ALTER TABLE {_validated_identifier(tbl_name, allowed=_MIGRATION_TABLES)} "
                        "ADD COLUMN customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL"
                    ))
                    conn.commit()
                    logger.info(f"마이그레이션: {tbl_name}.customer_id 컬럼 추가")
                    inspector = inspect(engine)
                    table_names = _table_names(inspector)

        # ── Phase 3: deal → contract 테이블/컬럼 리네임 ──────────────
        # 테이블 리네임: deals → contracts
        if "deals" in table_names and "contracts" not in table_names:
            conn.execute(text("ALTER TABLE deals RENAME TO contracts"))
            conn.commit()
            logger.info("마이그레이션: deals → contracts 테이블 리네임")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # 테이블 리네임: deal_periods → contract_periods
        if "deal_periods" in table_names and "contract_periods" not in table_names:
            conn.execute(text("ALTER TABLE deal_periods RENAME TO contract_periods"))
            conn.commit()
            logger.info("마이그레이션: deal_periods → contract_periods 테이블 리네임")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # 테이블 리네임: deal_contacts → contract_contacts
        if "deal_contacts" in table_names and "contract_contacts" not in table_names:
            conn.execute(text("ALTER TABLE deal_contacts RENAME TO contract_contacts"))
            conn.commit()
            logger.info("마이그레이션: deal_contacts → contract_contacts 테이블 리네임")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # 테이블 리네임: deal_type_configs → contract_type_configs
        if "deal_type_configs" in table_names and "contract_type_configs" not in table_names:
            conn.execute(text("ALTER TABLE deal_type_configs RENAME TO contract_type_configs"))
            conn.commit()
            logger.info("마이그레이션: deal_type_configs → contract_type_configs 테이블 리네임")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # contracts 테이블: deal_code → contract_code, deal_name → contract_name, deal_type → contract_type
        if "contracts" in table_names:
            c_cols = _table_columns(inspector, "contracts")
            if "deal_code" in c_cols and "contract_code" not in c_cols:
                conn.execute(text("ALTER TABLE contracts RENAME COLUMN deal_code TO contract_code"))
                conn.commit()
                logger.info("마이그레이션: contracts.deal_code → contract_code")
            if "deal_name" in c_cols and "contract_name" not in c_cols:
                conn.execute(text("ALTER TABLE contracts RENAME COLUMN deal_name TO contract_name"))
                conn.commit()
                logger.info("마이그레이션: contracts.deal_name → contract_name")
            if "deal_type" in c_cols and "contract_type" not in c_cols:
                conn.execute(text("ALTER TABLE contracts RENAME COLUMN deal_type TO contract_type"))
                conn.commit()
                logger.info("마이그레이션: contracts.deal_type → contract_type")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # contract_periods: deal_id → contract_id
        if "contract_periods" in table_names:
            cp_cols = _table_columns(inspector, "contract_periods")
            if "deal_id" in cp_cols and "contract_id" not in cp_cols:
                conn.execute(text("ALTER TABLE contract_periods RENAME COLUMN deal_id TO contract_id"))
                conn.commit()
                logger.info("마이그레이션: contract_periods.deal_id → contract_id")
                inspector = inspect(engine)
                table_names = _table_names(inspector)

        # contract_contacts: deal_id → contract_id, deal_period_id → contract_period_id
        if "contract_contacts" in table_names:
            cc_cols = _table_columns(inspector, "contract_contacts")
            if "deal_id" in cc_cols and "contract_id" not in cc_cols:
                conn.execute(text("ALTER TABLE contract_contacts RENAME COLUMN deal_id TO contract_id"))
                conn.commit()
                logger.info("마이그레이션: contract_contacts.deal_id → contract_id")
            if "deal_period_id" in cc_cols and "contract_period_id" not in cc_cols:
                conn.execute(text("ALTER TABLE contract_contacts RENAME COLUMN deal_period_id TO contract_period_id"))
                conn.commit()
                logger.info("마이그레이션: contract_contacts.deal_period_id → contract_period_id")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # monthly_actuals: deal_id → contract_id
        if "monthly_actuals" in table_names:
            ma_cols = _table_columns(inspector, "monthly_actuals")
            if "deal_id" in ma_cols and "contract_id" not in ma_cols:
                conn.execute(text("ALTER TABLE monthly_actuals RENAME COLUMN deal_id TO contract_id"))
                conn.commit()
                logger.info("마이그레이션: monthly_actuals.deal_id → contract_id")
                inspector = inspect(engine)
                table_names = _table_names(inspector)

        # monthly_forecasts: deal_period_id → contract_period_id
        if "monthly_forecasts" in table_names:
            mf_cols = _table_columns(inspector, "monthly_forecasts")
            if "deal_period_id" in mf_cols and "contract_period_id" not in mf_cols:
                conn.execute(text("ALTER TABLE monthly_forecasts RENAME COLUMN deal_period_id TO contract_period_id"))
                conn.commit()
                logger.info("마이그레이션: monthly_forecasts.deal_period_id → contract_period_id")
                inspector = inspect(engine)
                table_names = _table_names(inspector)

        # receipts: deal_id → contract_id
        if "receipts" in table_names:
            r_cols = _table_columns(inspector, "receipts")
            if "deal_id" in r_cols and "contract_id" not in r_cols:
                conn.execute(text("ALTER TABLE receipts RENAME COLUMN deal_id TO contract_id"))
                conn.commit()
                logger.info("마이그레이션: receipts.deal_id → contract_id")
                inspector = inspect(engine)
                table_names = _table_names(inspector)

        # receipt_matches: deal_id → contract_id (if column exists)
        if "receipt_matches" in table_names:
            rm_cols = _table_columns(inspector, "receipt_matches")
            if "deal_id" in rm_cols and "contract_id" not in rm_cols:
                conn.execute(text("ALTER TABLE receipt_matches RENAME COLUMN deal_id TO contract_id"))
                conn.commit()
                logger.info("마이그레이션: receipt_matches.deal_id → contract_id")
                inspector = inspect(engine)
                table_names = _table_names(inspector)

        # audit_logs: entity_type 'deal' → 'contract'
        if "audit_logs" in table_names:
            conn.execute(text("UPDATE audit_logs SET entity_type = 'contract' WHERE entity_type = 'deal'"))
            conn.commit()
            logger.info("마이그레이션: audit_logs.entity_type 'deal' → 'contract'")

        # ── Phase 4: monthly_actuals → transaction_lines 테이블/컬럼 리네임 ──
        # 테이블 리네임: monthly_actuals → transaction_lines
        if "monthly_actuals" in table_names and "transaction_lines" not in table_names:
            conn.execute(text("ALTER TABLE monthly_actuals RENAME TO transaction_lines"))
            conn.commit()
            logger.info("마이그레이션: monthly_actuals → transaction_lines 테이블 리네임")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # receipt_matches: actual_id → transaction_line_id
        if "receipt_matches" in table_names:
            rm_cols = _table_columns(inspector, "receipt_matches")
            if "actual_id" in rm_cols and "transaction_line_id" not in rm_cols:
                conn.execute(text("ALTER TABLE receipt_matches RENAME COLUMN actual_id TO transaction_line_id"))
                conn.commit()
                logger.info("마이그레이션: receipt_matches.actual_id → transaction_line_id")
                inspector = inspect(engine)
                table_names = _table_names(inspector)

        # ── Recovery: create_all 이후 구/신 테이블이 공존하는 경우 데이터 복사 ──
        _copy_table_rows(
            conn,
            inspector,
            old_table="deals",
            new_table="contracts",
            column_map={
                "id": "id",
                "contract_code": "deal_code",
                "contract_name": "deal_name",
                "contract_type": "deal_type",
                "end_customer_id": "end_customer_id",
                "owner_user_id": "owner_user_id",
                "status": "status",
                "notes": "notes",
                "inspection_day": "inspection_day",
                "inspection_date": "inspection_date",
                "invoice_month_offset": "invoice_month_offset",
                "invoice_day_type": "invoice_day_type",
                "invoice_day": "invoice_day",
                "invoice_holiday_adjust": "invoice_holiday_adjust",
                "created_at": "created_at",
                "updated_at": "updated_at",
            },
        )
        inspector = inspect(engine)

        _copy_table_rows(
            conn,
            inspector,
            old_table="deal_periods",
            new_table="contract_periods",
            column_map={
                "id": "id",
                "contract_id": "deal_id",
                "period_year": "period_year",
                "period_label": "period_label",
                "stage": "stage",
                "expected_revenue_total": "expected_revenue_total",
                "expected_gp_total": "expected_gp_total",
                "start_month": "start_month",
                "end_month": "end_month",
                "owner_user_id": "owner_user_id",
                "customer_id": "customer_id",
                "notes": "notes",
                "inspection_day": "inspection_day",
                "inspection_date": "inspection_date",
                "invoice_month_offset": "invoice_month_offset",
                "invoice_day_type": "invoice_day_type",
                "invoice_day": "invoice_day",
                "invoice_holiday_adjust": "invoice_holiday_adjust",
                "created_at": "created_at",
                "updated_at": "updated_at",
            },
        )
        inspector = inspect(engine)

        _copy_table_rows(
            conn,
            inspector,
            old_table="monthly_actuals",
            new_table="transaction_lines",
            column_map={
                "id": "id",
                "contract_id": "contract_id",
                "revenue_month": "revenue_month",
                "line_type": "line_type",
                "customer_id": "customer_id",
                "supply_amount": "supply_amount",
                "invoice_issue_date": "invoice_issue_date",
                "status": "status",
                "description": "description",
                "created_by": "created_by",
                "created_at": "created_at",
                "updated_at": "updated_at",
            },
            transforms={
                "line_type": "CASE WHEN line_type = 'sales' THEN 'revenue' ELSE line_type END",
            },
        )
        inspector = inspect(engine)

        _copy_table_rows(
            conn,
            inspector,
            old_table="payments",
            new_table="receipts",
            column_map={
                "id": "id",
                "contract_id": "deal_id",
                "customer_id": "customer_id",
                "receipt_date": "payment_date",
                "revenue_month": "revenue_month",
                "amount": "amount",
                "description": "description",
                "created_by": "created_by",
                "created_at": "created_at",
                "updated_at": "updated_at",
            },
        )
        inspector = inspect(engine)

        _copy_table_rows(
            conn,
            inspector,
            old_table="allocations",
            new_table="receipt_matches",
            column_map={
                "id": "id",
                "receipt_id": "payment_id",
                "transaction_line_id": "actual_id",
                "matched_amount": "allocated_amount",
                "match_type": "allocation_type",
                "created_by": "created_by",
                "created_at": "created_at",
                "updated_at": "updated_at",
            },
        )
        inspector = inspect(engine)

        _copy_table_rows(
            conn,
            inspector,
            old_table="deal_contacts",
            new_table="contract_contacts",
            column_map={
                "id": "id",
                "contract_period_id": "deal_period_id",
                "customer_id": "customer_id",
                "contact_type": "contact_type",
                "name": "name",
                "phone": "phone",
                "email": "email",
                "notes": "notes",
                "created_at": "created_at",
                "updated_at": "updated_at",
            },
        )

        # ── contract_periods: is_completed 컬럼 추가 ──
        if "contract_periods" in table_names:
            cp_cols = _table_columns(inspector, "contract_periods")
            if "is_completed" not in cp_cols:
                conn.execute(text(
                    "ALTER TABLE contract_periods ADD COLUMN is_completed BOOLEAN DEFAULT 0 NOT NULL"
                ))
                conn.commit()
                logger.info("마이그레이션: contract_periods.is_completed 컬럼 추가")

        # ── 담당자 구조 변경: 역할 분리 + 사업별 담당자 참조 방식 ──
        inspector = inspect(engine)
        table_names = _table_names(inspector)

        # 1) customer_contact_roles 테이블 생성 (create_all로 이미 생성될 수 있음)
        if "customer_contact_roles" not in table_names:
            conn.execute(text("""
                CREATE TABLE customer_contact_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_contact_id INTEGER NOT NULL REFERENCES customer_contacts(id) ON DELETE CASCADE,
                    role_type VARCHAR(20) NOT NULL,
                    is_default BOOLEAN DEFAULT 0 NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    UNIQUE(customer_contact_id, role_type)
                )
            """))
            conn.execute(text(
                "CREATE INDEX ix_customer_contact_roles_contact_id "
                "ON customer_contact_roles(customer_contact_id)"
            ))
            conn.commit()
            logger.info("마이그레이션: customer_contact_roles 테이블 생성")
            inspector = inspect(engine)
            table_names = _table_names(inspector)

        # 2) customer_contacts.contact_type → customer_contact_roles로 데이터 이전
        if "customer_contacts" in table_names and "customer_contact_roles" in table_names:
            cc_cols = _table_columns(inspector, "customer_contacts")
            if "contact_type" in cc_cols:
                role_count = int(
                    conn.execute(text("SELECT COUNT(*) FROM customer_contact_roles")).scalar() or 0
                )
                if role_count == 0:
                    conn.execute(text("""
                        INSERT INTO customer_contact_roles (customer_contact_id, role_type, is_default)
                        SELECT id, contact_type, is_default
                        FROM customer_contacts
                        WHERE contact_type IS NOT NULL
                    """))
                    conn.commit()
                    migrated = int(
                        conn.execute(text("SELECT COUNT(*) FROM customer_contact_roles")).scalar() or 0
                    )
                    if migrated > 0:
                        logger.info(
                            "마이그레이션: customer_contacts.contact_type → customer_contact_roles %s건 이전",
                            migrated,
                        )

        # 3) contract_contacts: customer_contact_id 컬럼 추가
        if "contract_contacts" in table_names:
            cc_cols = _table_columns(inspector, "contract_contacts")
            if "customer_contact_id" not in cc_cols:
                conn.execute(text(
                    "ALTER TABLE contract_contacts ADD COLUMN customer_contact_id "
                    "INTEGER REFERENCES customer_contacts(id) ON DELETE SET NULL"
                ))
                conn.commit()
                logger.info("마이그레이션: contract_contacts.customer_contact_id 컬럼 추가")
                inspector = inspect(engine)

            # 4) contract_contacts: rank 컬럼 추가
            cc_cols = _table_columns(inspector, "contract_contacts")
            if "rank" not in cc_cols:
                conn.execute(text(
                    "ALTER TABLE contract_contacts ADD COLUMN rank VARCHAR(10) DEFAULT '정' NOT NULL"
                ))
                conn.commit()
                logger.info("마이그레이션: contract_contacts.rank 컬럼 추가")
                inspector = inspect(engine)

            # 5) 기존 contract_contacts의 name/phone/email → customer_contacts 매칭
            cc_cols = _table_columns(inspector, "contract_contacts")
            if "customer_contact_id" in cc_cols and "name" in cc_cols:
                unlinked = int(conn.execute(text(
                    "SELECT COUNT(*) FROM contract_contacts "
                    "WHERE customer_contact_id IS NULL AND name IS NOT NULL AND name != ''"
                )).scalar() or 0)
                if unlinked > 0:
                    # 이름+거래처로 매칭 시도
                    conn.execute(text("""
                        UPDATE contract_contacts SET customer_contact_id = (
                            SELECT cc.id FROM customer_contacts cc
                            WHERE cc.customer_id = contract_contacts.customer_id
                            AND cc.name = contract_contacts.name
                            LIMIT 1
                        )
                        WHERE customer_contact_id IS NULL
                        AND name IS NOT NULL AND name != ''
                    """))
                    conn.commit()
                    matched = unlinked - int(conn.execute(text(
                        "SELECT COUNT(*) FROM contract_contacts "
                        "WHERE customer_contact_id IS NULL AND name IS NOT NULL AND name != ''"
                    )).scalar() or 0)
                    if matched > 0:
                        logger.info(
                            "마이그레이션: contract_contacts → customer_contacts 매칭 %s건",
                            matched,
                        )

                    # 매칭 안 된 레코드: customer_contacts에 자동 등록 후 연결
                    remaining = conn.execute(text(
                        "SELECT id, customer_id, contact_type, name, phone, email "
                        "FROM contract_contacts "
                        "WHERE customer_contact_id IS NULL AND name IS NOT NULL AND name != ''"
                    )).fetchall()
                    for row in remaining:
                        cc_id, cust_id, ctype, cname, cphone, cemail = row
                        # customer_contacts에 신규 등록
                        conn.execute(text(
                            "INSERT INTO customer_contacts (customer_id, name, phone, email, "
                            "contact_type, is_default, created_at, updated_at) "
                            "VALUES (:cust_id, :name, :phone, :email, "
                            "COALESCE(:ctype, ''), 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                        ), {"cust_id": cust_id, "name": cname, "phone": cphone, "email": cemail, "ctype": ctype})
                        new_cc_id = int(conn.execute(text("SELECT last_insert_rowid()")).scalar())
                        # customer_contact_roles에 역할 추가
                        if ctype:
                            conn.execute(text(
                                "INSERT OR IGNORE INTO customer_contact_roles "
                                "(customer_contact_id, role_type, is_default, "
                                "created_at, updated_at) "
                                "VALUES (:cc_id, :role, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                            ), {"cc_id": new_cc_id, "role": ctype})
                        # contract_contacts 연결
                        conn.execute(text(
                            "UPDATE contract_contacts SET customer_contact_id = :cc_id WHERE id = :id"
                        ), {"cc_id": new_cc_id, "id": cc_id})
                    conn.commit()
                    if remaining:
                        logger.info(
                            "마이그레이션: 매칭 안 된 contract_contacts %s건 → customer_contacts 자동 등록",
                            len(remaining),
                        )


@app.on_event("startup")
def on_startup() -> None:
    logger.info("영업관리 시스템 시작 (ENV=%s)", os.getenv("ENV", "dev"))
    # 개발 환경에서는 모델 스키마를 먼저 생성하되, 기존 데이터는 _run_migrations()가 복구한다.
    if ENV == "dev":
        Base.metadata.create_all(bind=engine)
    _run_migrations()
    # 시드 데이터 초기화
    from app.database import SessionLocal
    from app.services.contract_type_config import seed_defaults as seed_contract_types
    from app.services.term_config import seed_defaults as seed_terms
    from app.services.user import ensure_bootstrap_admin
    db = SessionLocal()
    try:
        seed_contract_types(db)
        seed_terms(db)
        admin = ensure_bootstrap_admin(
            db,
            login_id=BOOTSTRAP_ADMIN_LOGIN_ID,
            password=BOOTSTRAP_ADMIN_PASSWORD,
            name=BOOTSTRAP_ADMIN_NAME,
        )
        if admin:
            logger.info("초기 관리자 계정을 생성했습니다. login_id=%s", admin.login_id)
        elif ENV != "dev":
            logger.info("초기 관리자 bootstrap 미설정 상태로 시작했습니다.")
    finally:
        db.close()

# 미들웨어 등록 (순서 중요: Session → Auth)
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# ── 전역 예외 핸들러 ──────────────────────────────────────────
@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(_request: Request, exc: UnauthorizedError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def not_found_handler(_request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(_request: Request, exc: BusinessRuleError):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.exception_handler(DuplicateError)
async def duplicate_handler(_request: Request, exc: DuplicateError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(_request: Request, exc: PermissionDeniedError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(_request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors})


# 라우터 등록
app.include_router(auth_router)
app.include_router(dashboard.router)
app.include_router(customers.router)
app.include_router(contracts.router)
app.include_router(excel.router)
app.include_router(users.router)
app.include_router(settings.router)
app.include_router(contract_contacts.router)
app.include_router(contract_types.router)
app.include_router(term_configs.router)
app.include_router(user_preferences.router)
app.include_router(reports.router)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request):
    return templates.TemplateResponse("change_password.html", {"request": request})


@app.get("/")
def index():
    return RedirectResponse(url=DEFAULT_HOME)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/my-contracts", response_class=HTMLResponse)
def my_contracts_page(request: Request):
    return templates.TemplateResponse("my_contracts.html", {"request": request})


@app.get("/contracts", response_class=HTMLResponse)
def contracts_page(request: Request):
    return templates.TemplateResponse("contracts.html", {"request": request})


@app.get("/contracts/new/{contract_id}", response_class=HTMLResponse)
def contract_detail_new_page(request: Request, contract_id: int):
    """Period 없는 신규 Contract 상세 — contract_id 기반 진입."""
    return templates.TemplateResponse(
        "contract_detail.html", {"request": request, "contract_period_id": 0, "contract_id": contract_id}
    )


@app.get("/contracts/{contract_period_id}", response_class=HTMLResponse)
def contract_detail_page(request: Request, contract_period_id: int):
    return templates.TemplateResponse(
        "contract_detail.html", {"request": request, "contract_period_id": contract_period_id, "contract_id": 0}
    )


@app.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request):
    return templates.TemplateResponse("customers.html", {"request": request})


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})


@app.get("/system", response_class=HTMLResponse)
def system_page(request: Request):
    return templates.TemplateResponse("system.html", {"request": request})


@app.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(request: Request):
    return templates.TemplateResponse("audit_logs.html", {"request": request})
