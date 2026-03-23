# 코드 채번 체계 재설계

> 고객코드 · 사업코드 · 기간코드를 계층적으로 통합하는 코드 체계 설계.

---

## 1. 코드 형식

```text
C000-P000-Y26A
│     │     └── 기간코드: Y + 연도(2자리) + 순번(A~Z)
│     └──────── 사업코드: P + base36(3자리), 고객 내 순번
└────────────── 고객코드: C + base36(3자리), 전역 순번
```

### 1.1 고객코드 (Customer.customer_code)

- 형식: `C` + base36 3자리 = `C000` ~ `CZZZ`
- 범위: 전역 순번 (46,656 슬롯)
- 채번: 전역 MAX 다음 번호
- **생성 후 변경 불가** (하위 사업/기간 코드에 포함되므로)
- 기존 `C-000` → `C000` 으로 대시 제거 마이그레이션

### 1.2 사업코드 (Contract.contract_code)

- 형식: `{고객코드}-P{base36(3)}` = `C000-P000` ~ `C000-PZZZ`
- 범위: 고객당 순번 (46,656 슬롯)
- 채번: 해당 고객의 MAX `P___` 다음 번호
- 고객 미지정(end_customer_id=NULL) 사업: `CXXX-P000` (예약 고객코드 `CXXX` 사용)
- 기존 `SI-2026-0016` → 해당 고객의 순번으로 재채번

### 1.3 기간코드 (ContractPeriod.period_code) — 신규 컬럼

- 형식: `{사업코드}-Y{연도2자리}{순번}` = `C000-P000-Y26A` ~ `C000-P000-Y26Z`
- 범위: 사업·연도당 26개 (A~Z)
- 채번: 해당 사업+연도의 MAX suffix letter 다음
- `period_label` 컬럼은 유지 (표시용, `Y26` 등)
- 기존 데이터: period_label 기반으로 period_code 생성

---

## 2. DB 스키마 변경

### 2.1 Customer (변경)

- `customer_code`: `String(10)` → `String(4)` (C + 3자리)
- 마이그레이션: `C-000` → `C000` (대시 제거)
- 제약: UNIQUE, NOT NULL (기존과 동일)

### 2.2 Contract (변경)

- `contract_code`: `String(50)` → `String(9)` (C000-P000)
- 채번 로직 변경: `{type}-{year}-{id}` → `{customer_code}-P{seq}`
- 제약: UNIQUE, NOT NULL (기존과 동일)

### 2.3 ContractPeriod (컬럼 추가)

- `period_code`: `String(14)` 신규 추가 (C000-P000-Y26A)
- 제약: UNIQUE, NOT NULL
- `period_label`은 유지 (표시용)

---

## 3. 채번 로직 상세

### 3.1 공통 유틸리티 (`app/core/code_generator.py` 신규)

```python
BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def int_to_base36(n: int, width: int = 3) -> str:
    """정수 → base36 문자열 (고정 폭)."""

def base36_to_int(s: str) -> int:
    """base36 문자열 → 정수."""

def next_customer_code(db: Session) -> str:
    """전역 MAX customer_code 다음 번호. C000~CZZZ.
    CXXX는 예약 코드이므로 건너뛴다."""

def next_contract_code(db: Session, customer_code: str) -> str:
    """해당 고객의 MAX contract_code에서 P-부분 다음 번호."""

def next_period_code(db: Session, contract_code: str, period_year: int) -> str:
    """해당 사업+연도의 MAX period_code에서 suffix letter 다음.
    Z 이후 슬롯 소진 시 BusinessRuleError 발생."""
```

### 3.2 동시성 및 충돌 처리

채번은 `SELECT MAX → +1 → INSERT` 패턴이므로 TOCTOU race condition 가능.

**전략**: UNIQUE 제약 + retry

1. `next_*_code()` 로 코드 생성
2. `db.flush()` 시 UNIQUE violation 발생하면 `IntegrityError` catch
3. 최대 3회 retry (새 MAX 조회 → 재채번)
4. 3회 초과 시 `BusinessRuleError("코드 채번 충돌, 잠시 후 재시도")` 발생

base36 순번은 PostgreSQL 기본 collation에서 lexicographic 정렬이 숫자 순서와 일치한다 (0-9 < A-Z).

### 3.3 채번 순서

**고객 생성:**

1. `SELECT MAX(customer_code) FROM customers WHERE customer_code LIKE 'C%'`
2. base36 decode → +1 → encode → `C{new}`

**사업 생성:**

1. 고객의 `customer_code` 조회
2. `SELECT MAX(contract_code) FROM contracts WHERE contract_code LIKE '{customer_code}-P%'`
3. P-부분 추출 → base36 decode → +1 → `{customer_code}-P{new}`

**기간 생성:**

1. 사업의 `contract_code` 조회
2. year_suffix = `Y{period_year % 100:02d}`
3. `SELECT MAX(period_code) FROM contract_periods WHERE period_code LIKE '{contract_code}-{year_suffix}%'`
4. 마지막 letter 추출 → +1 → `{contract_code}-{year_suffix}{new_letter}`
5. 첫 기간이면 `A`

### 3.4 고객 미지정 사업 처리

`end_customer_id`가 NULL인 사업의 경우:

- 예약 고객코드 `CXXX` 사용 (DB에 실제 고객 레코드 불필요)
- `CXXX`는 `next_customer_code()`에서 항상 건너뛴다 (실제 고객에 할당 금지)
- 사업코드: `CXXX-P000`, `CXXX-P001`, ...
- 나중에 고객 지정 시 **사업코드는 변경하지 않음** (이미 발급된 코드는 불변)

### 3.5 슬롯 소진 처리

- 기간코드 A~Z 26개 소진 시: `BusinessRuleError("해당 연도의 기간 슬롯이 모두 사용되었습니다 (최대 26개)")` 발생
- 고객코드/사업코드 base36 소진 (46,656개)은 실질적으로 발생 불가하므로 별도 처리 불필요

---

## 4. 마이그레이션 계획 (Alembic)

단일 마이그레이션 `0010_code_numbering.py`.
PostgreSQL에서 단일 트랜잭션으로 실행되므로 부분 실패 시 전체 롤백된다.
**비가역 마이그레이션** — 기존 코드 형식이 파괴되므로 downgrade 불가. 마이그레이션 전 DB 백업 권장.

### Step 1: customer_code 변환

```sql
UPDATE customers SET customer_code = REPLACE(customer_code, 'C-', 'C')
WHERE customer_code LIKE 'C-%';
```

### Step 2: contract_code 재채번

- 고객별로 사업을 `id` 순 정렬
- 각 사업에 `{customer_code}-P{seq}` 형식으로 재채번
- 고객 미지정 사업: `CXXX-P{seq}`

### Step 3: period_code 컬럼 추가 및 채번

- `ALTER TABLE contract_periods ADD COLUMN period_code VARCHAR(14)`
- 사업별로 기간을 `period_year, id` 순 정렬
- 각 기간에 `{contract_code}-Y{year}{letter}` 형식으로 채번
- `ALTER TABLE contract_periods ALTER COLUMN period_code SET NOT NULL`
- `CREATE UNIQUE INDEX`

### Step 4: 컬럼 크기 조정 (안전 검증 후)

- 변환 후 데이터 길이 검증: `SELECT ... WHERE LENGTH(customer_code) > 4` 등 → 0건 확인
- `customers.customer_code`: VARCHAR(10) → VARCHAR(4)
- `contracts.contract_code`: VARCHAR(50) → VARCHAR(9)

---

## 5. 서비스 레이어 변경

### 5.1 customer_service.py

- `_generate_customer_code()` → `code_generator.next_customer_code()` 호출로 교체
- 고객코드 수정 API에서 **customer_code 변경 차단** 로직 추가

### 5.2 contract_service.py

- `create_contract()`: 채번 로직을 `code_generator.next_contract_code(db, customer_code)` 로 교체
- `end_customer_id` 필수가 아닌 경우 `CXXX` prefix 사용
- `update_contract()`: `end_customer_id` 변경 시 contract_code는 변경하지 않음
- `ContractUpdate` 스키마에서 `contract_code` 필드 제거 (불변 보장)

### 5.3 contract_service.py (period)

- `create_period()`: `code_generator.next_period_code()` 호출하여 `period_code` 자동 생성
- `_period_read_dict()`: 응답에 `period_code` 필드 추가
- `list_periods()`, `get_contract_periods()`: 인라인 dict에도 `period_code` 포함

### 5.4 ContractPeriodRead 스키마

- `period_code: str` 필드 추가

### 5.5 accounting importer

- `app/modules/accounting/services/importer.py`의 contract_code 생성 로직도 `code_generator.next_contract_code()` 로 교체

---

## 6. 프론트엔드 변경

### 6.1 인프라 프로젝트 상세

- 제목 표기: `프로젝트명(C000-P000-Y26A)` 형태
- period_code를 API 응답에서 수신하여 표시

### 6.2 영업 원장

- contract_code 표시 형식이 바뀜 (`SI-2026-0016` → `C000-P000`)
- 기존 정렬/필터 로직은 문자열 비교이므로 변경 불필요

### 6.3 거래처 관리

- customer_code 표시 형식 변경 (`C-000` → `C000`)
- 고객코드 수정 비활성화 (읽기 전용)

---

## 7. 영향 범위

| 파일                                                | 변경 내용                             |
| --------------------------------------------------- | ------------------------------------- |
| `app/core/code_generator.py`                        | 신규 — 채번 유틸리티                  |
| `app/modules/common/models/customer.py`             | customer_code 길이 조정               |
| `app/modules/common/models/contract.py`             | contract_code 길이 조정               |
| `app/modules/common/models/contract_period.py`      | period_code 컬럼 추가                 |
| `app/modules/common/schemas/contract.py`            | ContractUpdate에서 contract_code 제거 |
| `app/modules/common/schemas/contract_period.py`     | period_code 필드 추가                 |
| `app/modules/common/services/customer.py`           | 채번 로직 교체, 코드 변경 차단        |
| `app/modules/common/services/contract_service.py`   | 채번 로직 교체, period_code 생성      |
| `app/modules/accounting/services/importer.py`       | contract_code 채번 로직 교체          |
| `alembic/versions/0010_code_numbering.py`           | 마이그레이션                          |
| `app/static/js/contract_detail.js`                  | 코드 표시 형식 변경                   |
| `app/static/js/infra_project_detail.js`             | period_code 표시 추가                 |
| `app/static/js/infra_projects.js`                   | period_code 표시                      |
| `app/static/js/customers.js`                        | customer_code 읽기 전용               |

---

## 8. 제약 및 결정 사항

1. **고객코드 불변**: 생성 후 변경 불가. 하위 코드에 포함되므로.
2. **사업코드 불변**: 고객 변경 시에도 기존 사업코드 유지.
3. **기간코드 불변**: 연도 변경 시에도 기존 기간코드 유지.
4. **고객 미지정 사업**: `CXXX` 예약 prefix 사용.
5. **base36 순번**: 0~9, A~Z 사용. 대소문자 구분 없음 (항상 대문자).
6. **동시성**: UNIQUE 제약 + 최대 3회 retry. IntegrityError 시 자동 재채번.
