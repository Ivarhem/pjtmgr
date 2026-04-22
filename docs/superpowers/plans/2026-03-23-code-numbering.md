# 코드 채번 체계 재설계 Implementation Plan

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** 고객코드(C000)·사업코드(C000-P000)·기간코드(C000-P000-Y26A) 계층적 코드 체계를 구현한다.

**Architecture:** `app/core/code_generator.py`에 채번 유틸리티를 집중하고, 기존 서비스의 인라인 채번 로직을 교체한다. Alembic 마이그레이션으로 기존 데이터를 새 형식으로 변환한다.

**Tech Stack:** Python 3.11, SQLAlchemy, Alembic, PostgreSQL 16, pytest

**Spec:** `docs/superpowers/specs/2026-03-23-code-numbering-design.md`

---

## File Structure

| 파일 | 역할 | 작업 |
| --- | --- | --- |
| `app/core/code_generator.py` | 채번 유틸리티 (base36 변환, next_*_code) | 신규 생성 |
| `tests/common/test_code_generator.py` | 채번 유틸리티 단위 테스트 | 신규 생성 |
| `app/modules/common/models/customer.py` | Customer 모델 | 수정: customer_code String(4) |
| `app/modules/common/models/contract.py` | Contract 모델 | 수정: contract_code String(9) |
| `app/modules/common/models/contract_period.py` | ContractPeriod 모델 | 수정: period_code 컬럼 추가 |
| `app/modules/common/schemas/contract.py` | Contract 스키마 | 수정: ContractUpdate에서 contract_code 제거 |
| `app/modules/common/schemas/contract_period.py` | ContractPeriod 스키마 | 수정: period_code 필드 추가 |
| `app/modules/common/services/customer.py` | 고객 서비스 | 수정: 채번 교체, 코드 변경 차단 |
| `app/modules/common/services/contract_service.py` | 사업/기간 서비스 | 수정: 채번 교체, period_code 생성, 응답 dict에 포함 |
| `app/modules/accounting/services/importer.py` | Excel 임포터 | 수정: contract_code 채번 교체 |
| `alembic/versions/0011_code_numbering.py` | 마이그레이션 | 신규 생성 |
| `app/static/js/infra_projects.js` | 인프라 계약단위 목록 | 수정: period_code 표시 |
| `app/static/js/infra_project_detail.js` | 인프라 계약단위 상세 | 수정: 제목에 period_code 표시 |
| `app/static/js/customers.js` | 거래처 관리 | 수정: customer_code 읽기전용 |

---

### Task 1: code_generator.py — 채번 유틸리티

**Files:**
- Create: `app/core/code_generator.py`
- Create: `tests/common/test_code_generator.py`

- [ ] **Step 1: 테스트 파일 생성 — base36 변환**

```python
# tests/common/test_code_generator.py
import pytest
from app.core.code_generator import int_to_base36, base36_to_int

class TestBase36:
    def test_zero(self):
        assert int_to_base36(0) == "000"

    def test_one(self):
        assert int_to_base36(1) == "001"

    def test_ten(self):
        assert int_to_base36(10) == "00A"

    def test_thirty_five(self):
        assert int_to_base36(35) == "00Z"

    def test_thirty_six(self):
        assert int_to_base36(36) == "010"

    def test_max(self):
        assert int_to_base36(46655) == "ZZZ"

    def test_roundtrip(self):
        for n in [0, 1, 35, 36, 100, 46655]:
            assert base36_to_int(int_to_base36(n)) == n

    def test_width_1(self):
        assert int_to_base36(0, width=1) == "0"
        assert int_to_base36(25, width=1) == "P"
```

- [ ] **Step 2: 테스트 실행 → FAIL 확인**

Run: `pytest tests/common/test_code_generator.py -v`
Expected: ImportError (모듈 없음)

- [ ] **Step 3: base36 변환 함수 구현**

```python
# app/core/code_generator.py
"""계층적 코드 채번 유틸리티.

코드 형식: C000-P000-Y26A
- 고객코드: C + base36(3) 전역 순번
- 사업코드: {고객코드}-P + base36(3) 고객 내 순번
- 기간코드: {사업코드}-Y + 연도(2) + A~Z 순번
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError

_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE36_MAP = {c: i for i, c in enumerate(_BASE36)}

RESERVED_CUSTOMER_CODE = "CXXX"


def int_to_base36(n: int, width: int = 3) -> str:
    """정수 → 고정 폭 base36 문자열. 0→'000', 35→'00Z', 36→'010'."""
    result: list[str] = []
    for _ in range(width):
        result.append(_BASE36[n % 36])
        n //= 36
    return "".join(reversed(result))


def base36_to_int(s: str) -> int:
    """base36 문자열 → 정수. '00Z'→35, '010'→36."""
    n = 0
    for c in s:
        n = n * 36 + _BASE36_MAP[c]
    return n
```

- [ ] **Step 4: 테스트 실행 → PASS 확인**

Run: `pytest tests/common/test_code_generator.py::TestBase36 -v`
Expected: 전체 PASS

- [ ] **Step 5: 테스트 추가 — next_customer_code**

```python
# tests/common/test_code_generator.py (추가)
from unittest.mock import MagicMock
from app.core.code_generator import next_customer_code, RESERVED_CUSTOMER_CODE

class TestNextCustomerCode:
    def _mock_db(self, last_code: str | None):
        """MAX(customer_code) 쿼리 결과를 모킹."""
        db = MagicMock()
        row = MagicMock()
        row.__getitem__ = lambda self, idx: last_code
        query = db.execute.return_value
        query.scalar.return_value = last_code
        return db

    def test_first_customer(self):
        db = self._mock_db(None)
        assert next_customer_code(db) == "C000"

    def test_increment(self):
        db = self._mock_db("C001")
        assert next_customer_code(db) == "C002"

    def test_skip_reserved(self):
        """CXXX(=C + base36 'XXX')에 도달하면 건너뛴다."""
        db = self._mock_db("CXXW")
        code = next_customer_code(db)
        # XXW(=44251) → XXX(=44252, reserved) → XXY(=44253)
        assert code == "CXXY"
```

- [ ] **Step 6: next_customer_code 구현**

```python
# app/core/code_generator.py (추가)
from sqlalchemy import text


def next_customer_code(db: Session) -> str:
    """전역 MAX customer_code 다음 번호. C000~CZZZ. CXXX 건너뜀."""
    row = db.execute(
        text("SELECT MAX(customer_code) FROM customers WHERE customer_code LIKE 'C%' AND customer_code != :reserved"),
        {"reserved": RESERVED_CUSTOMER_CODE},
    ).scalar()
    if row:
        n = base36_to_int(row[1:]) + 1  # 'C' prefix 제거
    else:
        n = 0
    # CXXX (base36 XXX = 44252) 건너뛰기
    reserved_n = base36_to_int("XXX")
    if n == reserved_n:
        n += 1
    return f"C{int_to_base36(n)}"
```

- [ ] **Step 7: 테스트 실행 → PASS 확인**

Run: `pytest tests/common/test_code_generator.py::TestNextCustomerCode -v`
Expected: PASS

- [ ] **Step 8: next_contract_code, next_period_code 테스트 추가**

```python
# tests/common/test_code_generator.py (추가)
from app.core.code_generator import next_contract_code, next_period_code

class TestNextContractCode:
    def _mock_db(self, last_code: str | None):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = last_code
        return db

    def test_first_contract(self):
        db = self._mock_db(None)
        assert next_contract_code(db, "C000") == "C000-P000"

    def test_increment(self):
        db = self._mock_db("C000-P002")
        assert next_contract_code(db, "C000") == "C000-P003"

    def test_null_customer(self):
        db = self._mock_db(None)
        assert next_contract_code(db, RESERVED_CUSTOMER_CODE) == "CXXX-P000"


class TestNextPeriodCode:
    def _mock_db(self, last_code: str | None):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = last_code
        return db

    def test_first_period(self):
        db = self._mock_db(None)
        assert next_period_code(db, "C000-P000", 2026) == "C000-P000-Y26A"

    def test_increment(self):
        db = self._mock_db("C000-P000-Y26A")
        assert next_period_code(db, "C000-P000", 2026) == "C000-P000-Y26B"

    def test_slot_exhausted(self):
        db = self._mock_db("C000-P000-Y26Z")
        with pytest.raises(Exception, match="최대 26개"):
            next_period_code(db, "C000-P000", 2026)
```

- [ ] **Step 9: next_contract_code, next_period_code 구현**

```python
# app/core/code_generator.py (추가)

def next_contract_code(db: Session, customer_code: str) -> str:
    """해당 고객의 MAX contract_code에서 P-부분 다음 번호."""
    pattern = f"{customer_code}-P%"
    row = db.execute(
        text("SELECT MAX(contract_code) FROM contracts WHERE contract_code LIKE :pattern"),
        {"pattern": pattern},
    ).scalar()
    if row:
        p_part = row.split("-P")[-1]  # "000" ~ "ZZZ"
        n = base36_to_int(p_part) + 1
    else:
        n = 0
    return f"{customer_code}-P{int_to_base36(n)}"


def next_period_code(db: Session, contract_code: str, period_year: int) -> str:
    """해당 사업+연도의 MAX period_code에서 suffix letter 다음. A~Z (26슬롯)."""
    year_suffix = f"Y{period_year % 100:02d}"
    pattern = f"{contract_code}-{year_suffix}%"
    row = db.execute(
        text("SELECT MAX(period_code) FROM contract_periods WHERE period_code LIKE :pattern"),
        {"pattern": pattern},
    ).scalar()
    if row:
        last_letter = row[-1]  # A ~ Z
        if last_letter == "Z":
            raise BusinessRuleError("해당 연도의 기간 슬롯이 모두 사용되었습니다 (최대 26개)")
        next_letter = chr(ord(last_letter) + 1)
    else:
        next_letter = "A"
    return f"{contract_code}-{year_suffix}{next_letter}"
```

- [ ] **Step 10: 전체 테스트 실행 → PASS 확인**

Run: `pytest tests/common/test_code_generator.py -v`
Expected: 전체 PASS

- [ ] **Step 11: 커밋**

```bash
git add app/core/code_generator.py tests/common/test_code_generator.py
git commit -m "feat: add hierarchical code generator (C000-P000-Y26A)"
```

---

### Task 2: 모델 · 스키마 수정

**Files:**
- Modify: `app/modules/common/models/customer.py:12` — customer_code String(4)
- Modify: `app/modules/common/models/contract.py:12` — contract_code String(9)
- Modify: `app/modules/common/models/contract_period.py` — period_code 컬럼 추가
- Modify: `app/modules/common/schemas/contract.py:20` — ContractUpdate에서 contract_code 제거
- Modify: `app/modules/common/schemas/contract_period.py:50-67` — period_code 필드 추가

- [ ] **Step 1: Customer 모델 수정**

`app/modules/common/models/customer.py:12`:
```python
# 변경 전:
customer_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
# 변경 후:
customer_code: Mapped[str] = mapped_column(String(4), unique=True, index=True)
```

- [ ] **Step 2: Contract 모델 수정**

`app/modules/common/models/contract.py:12`:
```python
# 변경 전:
contract_code: Mapped[str | None] = mapped_column(String(50), unique=True)
# 변경 후:
contract_code: Mapped[str] = mapped_column(String(9), unique=True, nullable=False)
```

- [ ] **Step 3: ContractPeriod 모델에 period_code 추가**

`app/modules/common/models/contract_period.py:15` (period_label 아래에 추가):
```python
period_code: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
```

- [ ] **Step 4: ContractUpdate 스키마에서 contract_code 제거**

`app/modules/common/schemas/contract.py:20` — `contract_code` 라인 삭제.

- [ ] **Step 5: ContractPeriod 스키마에 period_code 추가**

`app/modules/common/schemas/contract_period.py`:

ContractPeriodRead (line 50-67)에 추가:
```python
period_code: str
```

`app/modules/accounting/schemas/contract.py` ContractPeriodListRead에도 추가:
```python
period_code: str
```

- [ ] **Step 6: 커밋**

```bash
git add app/modules/common/models/ app/modules/common/schemas/ app/modules/accounting/schemas/contract.py
git commit -m "refactor: update models/schemas for hierarchical code numbering"
```

---

### Task 3: 서비스 레이어 수정

**Files:**
- Modify: `app/modules/common/services/customer.py:211-213,262-264,288-304,389-424`
- Modify: `app/modules/common/services/contract_service.py:35-36,54-72,101-118,137-155,179-211,303-355`
- Modify: `app/modules/accounting/services/importer.py:428`

- [ ] **Step 1: customer.py — 채번 로직 교체**

`app/modules/common/services/customer.py`:

기존 `_BASE36_CHARS`, `_int_to_base36`, `_base36_to_int`, `_generate_customer_code` 함수 (lines 389-424) 를 삭제하고, import로 교체:

파일 상단 import 추가:
```python
from app.core.code_generator import next_customer_code
```

Line 213 변경:
```python
# 변경 전:
obj = Customer(name=name, customer_code=_generate_customer_code(db))
# 변경 후:
obj = Customer(name=name, customer_code=next_customer_code(db))
```

Line 264 변경:
```python
# 변경 전:
obj.customer_code = _generate_customer_code(db)
# 변경 후:
obj.customer_code = next_customer_code(db)
```

- [ ] **Step 2: customer.py — 코드 변경 차단**

`update_customer()` (line 288-304)에 customer_code 변경 차단 추가. Line 292 이후:

```python
updates = data.model_dump(exclude_unset=True)
# customer_code는 변경 불가
if "customer_code" in updates:
    raise BusinessRuleError("고객코드는 변경할 수 없습니다.")
```

import 추가: `from app.core.exceptions import BusinessRuleError`

- [ ] **Step 3: contract_service.py — create_contract 채번 교체**

파일 상단 import 추가:
```python
from app.core.code_generator import next_contract_code, next_period_code, RESERVED_CUSTOMER_CODE
```

`create_contract()` (lines 205-207) 변경:

```python
# 변경 전:
cur_year = datetime.date.today().year
contract.contract_code = f"{data.contract_type}-{cur_year}-{contract.id:04d}"

# 변경 후:
if contract.end_customer_id:
    customer = db.get(Customer, contract.end_customer_id)
    cust_code = customer.customer_code if customer else RESERVED_CUSTOMER_CODE
else:
    cust_code = RESERVED_CUSTOMER_CODE
contract.contract_code = next_contract_code(db, cust_code)
```

Customer import 추가:
```python
from app.modules.common.models.customer import Customer
```

- [ ] **Step 4: contract_service.py — create_period에 period_code 생성 추가**

`create_period()` (line 340-354) 변경. period 생성 직전에:

```python
# contract_code 조회
contract_code = contract.contract_code
period_code = next_period_code(db, contract_code, data.period_year)
```

ContractPeriod 생성자에 `period_code=period_code` 추가:
```python
period = ContractPeriod(
    contract_id=contract_id,
    period_year=data.period_year,
    period_label=label,
    period_code=period_code,
    ...
)
```

- [ ] **Step 5: contract_service.py — 응답 dict에 period_code 포함**

`_period_read_dict()` (line 54-72)에 추가:
```python
"period_code": period.period_code,
```

`list_periods()` (line 101-118) 인라인 dict에 추가:
```python
"period_code": p.period_code,
```

`get_contract_periods()` (line 137-155) 인라인 dict에 추가:
```python
"period_code": p.period_code,
```

- [ ] **Step 6: importer.py — contract_code 채번 교체**

`app/modules/accounting/services/importer.py:428`:

파일 상단 import 추가:
```python
from app.core.code_generator import next_contract_code, next_period_code, RESERVED_CUSTOMER_CODE
```

Line 428 변경:
```python
# 변경 전:
contract.contract_code = f"{contract_type}-{year}-{contract.id:04d}"

# 변경 후:
cust_code = customer.customer_code if customer else RESERVED_CUSTOMER_CODE
contract.contract_code = next_contract_code(db, cust_code)
```

Period 생성 부분 (line 433 부근)에 period_code 추가:
```python
period_code = next_period_code(db, contract.contract_code, year)
```
ContractPeriod 생성자에 `period_code=period_code` 포함.

- [ ] **Step 7: 커밋**

```bash
git add app/modules/common/services/ app/modules/accounting/services/importer.py app/core/code_generator.py
git commit -m "refactor: integrate hierarchical code generator into services"
```

---

### Task 4: Alembic 마이그레이션

**Files:**
- Create: `alembic/versions/0011_code_numbering.py`

- [ ] **Step 1: 마이그레이션 파일 생성**

```python
# alembic/versions/0011_code_numbering.py
"""Hierarchical code numbering: C000-P000-Y26A.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-23

NON-REVERSIBLE: 기존 코드 형식이 파괴됨. 실행 전 DB 백업 권장.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def _int_to_base36(n: int, width: int = 3) -> str:
    result = []
    for _ in range(width):
        result.append(_BASE36[n % 36])
        n //= 36
    return "".join(reversed(result))


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step 1: customer_code 변환 (C-000 → C000) ──
    conn.execute(text(
        "UPDATE customers SET customer_code = REPLACE(customer_code, 'C-', 'C') "
        "WHERE customer_code LIKE 'C-%'"
    ))

    # ── Step 2: contract_code 재채번 ──
    # 고객별로 사업을 id 순 정렬, {customer_code}-P{seq} 형식으로 재채번
    contracts = conn.execute(text(
        "SELECT c.id, c.end_customer_id, "
        "  COALESCE(cu.customer_code, 'CXXX') AS cust_code "
        "FROM contracts c "
        "LEFT JOIN customers cu ON cu.id = c.end_customer_id "
        "ORDER BY COALESCE(cu.customer_code, 'CXXX'), c.id"
    )).fetchall()

    cust_seq: dict[str, int] = {}  # customer_code → next seq
    for row in contracts:
        cust_code = row[2]
        seq = cust_seq.get(cust_code, 0)
        new_code = f"{cust_code}-P{_int_to_base36(seq)}"
        conn.execute(text(
            "UPDATE contracts SET contract_code = :code WHERE id = :id"
        ), {"code": new_code, "id": row[0]})
        cust_seq[cust_code] = seq + 1

    # ── Step 3: period_code 컬럼 추가 및 채번 ──
    op.add_column("contract_periods", sa.Column("period_code", sa.String(14), nullable=True))

    periods = conn.execute(text(
        "SELECT cp.id, cp.period_year, c.contract_code "
        "FROM contract_periods cp "
        "JOIN contracts c ON c.id = cp.contract_id "
        "ORDER BY c.contract_code, cp.period_year, cp.id"
    )).fetchall()

    contract_year_seq: dict[str, int] = {}  # "{contract_code}-Y{yy}" → next letter index
    for row in periods:
        period_id, period_year, contract_code = row[0], row[1], row[2]
        year_suffix = f"Y{period_year % 100:02d}"
        key = f"{contract_code}-{year_suffix}"
        letter_idx = contract_year_seq.get(key, 0)
        letter = chr(ord("A") + letter_idx)
        period_code = f"{key}{letter}"
        conn.execute(text(
            "UPDATE contract_periods SET period_code = :code WHERE id = :id"
        ), {"code": period_code, "id": period_id})
        contract_year_seq[key] = letter_idx + 1

    # NOT NULL + UNIQUE
    op.alter_column("contract_periods", "period_code", nullable=False)
    op.create_index("ix_contract_periods_period_code", "contract_periods", ["period_code"], unique=True)

    # ── Step 4: 컬럼 크기 조정 (안전 검증) ──
    overflow = conn.execute(text(
        "SELECT COUNT(*) FROM customers WHERE LENGTH(customer_code) > 4"
    )).scalar()
    assert overflow == 0, f"customer_code 길이 초과 행 {overflow}건 — 마이그레이션 중단"

    overflow = conn.execute(text(
        "SELECT COUNT(*) FROM contracts WHERE LENGTH(contract_code) > 9"
    )).scalar()
    assert overflow == 0, f"contract_code 길이 초과 행 {overflow}건 — 마이그레이션 중단"

    op.alter_column("customers", "customer_code",
                     type_=sa.String(4), existing_type=sa.String(10))
    op.alter_column("contracts", "contract_code",
                     type_=sa.String(9), existing_type=sa.String(50), nullable=False)


def downgrade() -> None:
    raise NotImplementedError("비가역 마이그레이션 — downgrade 불가")
```

- [ ] **Step 2: Docker 앱 재시작하여 마이그레이션 실행 확인**

```bash
docker compose restart app
docker compose logs app --tail 30
```

Expected: `alembic upgrade head` 성공, 0011 적용

- [ ] **Step 3: DB에서 코드 형식 확인**

```bash
docker compose exec db psql -U pjtmgr -d pjtmgr -c \
  "SELECT customer_code FROM customers LIMIT 5;"
docker compose exec db psql -U pjtmgr -d pjtmgr -c \
  "SELECT contract_code FROM contracts LIMIT 5;"
docker compose exec db psql -U pjtmgr -d pjtmgr -c \
  "SELECT period_code, period_label FROM contract_periods LIMIT 5;"
```

Expected: `C000`, `C000-P000`, `C000-P000-Y26A` 형식

- [ ] **Step 4: 커밋**

```bash
git add alembic/versions/0011_code_numbering.py
git commit -m "feat(migration): 0011 hierarchical code numbering (C000-P000-Y26A)"
```

---

### Task 5: 프론트엔드 수정

**Files:**
- Modify: `app/static/js/infra_projects.js:21,24-28,130`
- Modify: `app/static/js/infra_project_detail.js:68,74`
- Modify: `app/static/js/customers.js:19`
- Modify: `app/static/js/contract_detail.js` (project-contract-links 정리)

- [ ] **Step 1: infra_projects.js — period_code 표시**

Line 21: 사업코드 컬럼을 period_code로 변경:
```javascript
// 변경 전:
{ field: "contract_code", headerName: "사업코드", width: 150, sort: "asc" }
// 변경 후:
{ field: "period_code", headerName: "기간코드", width: 160, sort: "asc" }
```

Lines 24-28: 사업명 valueGetter에서 period_code 사용:
```javascript
// 변경 전:
d.contract_name + ' (' + d.period_label + ')'
// 변경 후:
d.contract_name + ' (' + d.period_code + ')'
```

Line 130: setCtxProject 호출에서 period_code 사용:
```javascript
// 변경 전:
window.setCtxProject(d.id, d.contract_code, d.contract_name + ' (' + d.period_label + ')')
// 변경 후:
window.setCtxProject(d.id, d.period_code, d.contract_name + ' (' + d.period_code + ')')
```

- [ ] **Step 2: infra_project_detail.js — 제목에 period_code 표시**

Line 68:
```javascript
// 변경 전:
document.getElementById("project-title").textContent = p.contract_name + ' (' + p.period_label + ')'
// 변경 후:
document.getElementById("project-title").textContent = p.contract_name + ' (' + p.period_code + ')'
```

Line 74:
```javascript
// 변경 전:
["사업코드", p.contract_code]
// 변경 후:
["기간코드", p.period_code]
```

- [ ] **Step 3: customers.js — 고객코드 읽기전용 확인**

Line 19: 기존 그리드 컬럼에 `editable: false` 명시 (이미 편집 불가일 수 있으나 확인):
```javascript
{ field: 'customer_code', headerName: '코드', width: 80, sort: 'asc', editable: false }
```

- [ ] **Step 4: contract_detail.js — 삭제된 project-contract-links 참조 정리**

Lines 3239-3329: `loadLinkedProjects()`, `unlinkProject()`, `linkProjectPrompt()` 함수 3개 삭제.
Line 95: `loadLinkedProjects()` 호출 삭제.

`app/templates/contract_detail.html:164-175`: 연결된 프로젝트 섹션 HTML 삭제.

- [ ] **Step 5: 커밋**

```bash
git add app/static/js/ app/templates/contract_detail.html
git commit -m "ui: update code display format and remove obsolete project-contract-links"
```

---

### Task 6: 서버 기동 검증 및 최종 정리

- [ ] **Step 1: Docker 재시작**

```bash
docker compose restart app
docker compose logs app --tail 50
```

Expected: 에러 없음, health check 통과

- [ ] **Step 2: 주요 API 엔드포인트 확인**

```bash
# 고객 목록 — customer_code 형식 확인
curl -s http://localhost:9000/api/v1/customers | python -m json.tool | head -20

# 사업 상세 — contract_code 형식 확인
curl -s http://localhost:9000/api/v1/contracts | python -m json.tool | head -20

# 기간 목록 — period_code 포함 확인
curl -s http://localhost:9000/api/v1/contract-periods | python -m json.tool | head -20
```

- [ ] **Step 3: 브라우저 수동 검증**

확인 항목:
1. 거래처 목록 (`/customers`) — `C000` 형식 표시
2. 영업 원장 (`/contracts`) — `C000-P000` 형식 표시
3. 인프라 계약단위 목록 (`/infra/periods`) — `C000-P000-Y26A` 형식 표시
4. 인프라 계약단위 상세 — 제목 `프로젝트명(C000-P000-Y26A)` 형태
5. 사업 상세 (`/contracts/{id}`) — 연결된 프로젝트 섹션 없음 (제거됨)
6. 콘솔에 404/500 에러 없음

- [ ] **Step 4: 문서 갱신**

`docs/DECISIONS.md`에 코드 채번 체계 결정 추가:
```markdown
### 코드 채번 체계 (2026-03-23)
계층적 코드: C000(고객)-P000(사업)-Y26A(기간). base36 순번, UNIQUE 제약 + 3회 retry.
고객코드 생성 후 불변. CXXX는 고객 미지정 사업 예약 코드.
```

- [ ] **Step 5: 최종 커밋**

```bash
git add docs/
git commit -m "docs: add code numbering decision record"
```
