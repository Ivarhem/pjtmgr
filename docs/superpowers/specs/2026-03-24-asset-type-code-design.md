# 자산유형 코드 체계 설계

> 자산유형을 DB 관리형으로 전환하고, 유형 기반 자산 코드를 자동 생성한다.

---

## 1. 목표

1. 자산유형(server, network 등)을 하드코딩에서 DB 설정 테이블로 전환
2. 시스템관리 페이지에서 관리자가 유형을 추가/수정/비활성화 가능
3. 자산 등록 시 `{고객사코드}-{유형코드}-{base36 4자리}` 형식의 코드를 자동 부여
4. 시스템관리 페이지를 공통/영업관리/프로젝트관리 탭으로 구조화

---

## 2. 데이터 모델

### 2.1 `asset_type_codes` 테이블

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| type_key | String(30) | PK | 내부 식별 키 (예: `server`) |
| code | String(3) | UNIQUE, NOT NULL | 영문 3자리 코드 (예: `SVR`) |
| label | String(50) | NOT NULL | 한글 표시명 (예: `서버`) |
| sort_order | Integer | default 0 | 정렬 순서 |
| is_active | Boolean | default true | 활성 여부 |

- **위치:** `app/modules/common/models/asset_type_code.py` (common 모듈 — infra가 참조)
- **패턴:** `ContractTypeConfig`와 동일 (timestamp 없음, code PK가 아닌 type_key PK)
- type_key를 PK로 사용하는 이유: 기존 `Asset.asset_type` 컬럼에 저장된 값(server, network 등)과 직접 매핑

### 2.2 기본 시드 데이터

| type_key | code | label | sort_order |
|----------|------|-------|------------|
| server | SVR | 서버 | 1 |
| network | NET | 네트워크 | 2 |
| security | SEC | 보안장비 | 3 |
| storage | STO | 스토리지 | 4 |
| middleware | MID | 미들웨어 | 5 |
| application | APP | 응용 | 6 |
| other | ETC | 기타 | 7 |

### 2.3 기존 Asset 모델 변경

- `Asset.asset_type`: String(50) 유지. 저장 값은 `type_key` (예: `server`). 변경 없음.
- `Asset.asset_code`: String(50) 유지. 자동 생성 값 형식만 변경.
- **자산 유형 변경 차단:** `update_asset`에서 `asset_type` 필드 변경을 거부.

---

## 3. 자산 코드 자동 생성

### 3.1 형식

```
{고객사코드}-{유형코드}-{base36 4자리}
```

- 예: `P000-SEC-0000`, `P000-NET-001A`, `P000-SVR-00Z3`
- 문자셋: `0-9A-Z` (대문자), 4자리 zero-padded
- 범위: `0000` ~ `ZZZZ` (1,679,616개 per partner+type)

### 3.2 순번 결정 로직

```python
_BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def to_base36(num: int, width: int = 4) -> str:
    """Convert integer to zero-padded uppercase base36 string."""
    if num == 0:
        return "0" * width
    result = ""
    while num:
        result = _BASE36_CHARS[num % 36] + result
        num //= 36
    return result.zfill(width)


def _generate_asset_code(db, partner_id, type_key):
    partner_code = get_partner_code(db, partner_id)  # e.g. "P000"
    type_code = get_type_code(db, type_key)           # e.g. "SEC"
    prefix = f"{partner_code}-{type_code}-"

    # DB에서 해당 prefix의 max asset_code 조회
    # NOTE: zero-padded base36 대문자의 lexicographic MAX = numeric MAX
    # (ASCII 순서 0x30-0x39, 0x41-0x5A에서 '9' < 'A' 이므로 정합)
    max_code = db.scalar(
        select(func.max(Asset.asset_code))
        .where(Asset.partner_id == partner_id)
        .where(Asset.asset_code.like(f"{prefix}%"))
    )

    if max_code:
        suffix = max_code[len(prefix):]
        next_seq = int(suffix, 36) + 1
    else:
        next_seq = 0

    return prefix + to_base36(next_seq, width=4)
```

**동시성 처리:** `asset_code` 컬럼에 UNIQUE 제약이 있으므로, 동시 등록 시 IntegrityError가 발생할 수 있다. `create_asset`에서 IntegrityError 발생 시 최대 3회 재시도(retry loop)하여 다음 순번으로 재생성한다.

**헬퍼 위치:** `to_base36` 함수는 `asset_service.py` 내부에 배치한다.

### 3.3 규칙

- **자동 전용:** 사용자가 코드를 직접 입력할 수 없음. 등록 모달에 코드 입력 필드 없음.
- **유형 변경 차단:** 자산 수정 시 `asset_type` 변경 불가. 코드 불변성 보장.
- **유형 삭제 차단:** 해당 유형의 자산이 1건이라도 있으면 삭제 불가 (is_active=false만 허용).
- **유형 검증:** `create_asset` 시 `payload.asset_type`이 `asset_type_codes`에 존재하는 활성 type_key인지 검증. 없으면 400 에러.

### 3.4 기존 자산 코드 마이그레이션

- Alembic migration에서 **모든 자산**의 `asset_code`를 새 형식으로 재생성 (기존 구형 코드 `P000-A001`도 교체)
- 기존 `asset_type` 값 → `asset_type_codes.type_key` 매핑으로 유형 코드 결정
- `asset_type` 값이 시드에 없는 경우 (예: importer의 `"etc"` fallback): migration에서 `"other"`로 매핑
- 순서: `Asset.id` ASC (등록 순), 유형별 순번은 0000부터 시작

---

## 4. API

### 4.1 자산유형 코드 API

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| GET | `/api/v1/asset-type-codes` | 로그인 | 목록 (active_only 파라미터) |
| POST | `/api/v1/asset-type-codes` | 관리자 | 유형 추가 |
| PATCH | `/api/v1/asset-type-codes/{type_key}` | 관리자 | 유형 수정 (code 변경 불가) |
| DELETE | `/api/v1/asset-type-codes/{type_key}` | 관리자 | 유형 삭제 (자산 있으면 차단) |

### 4.2 스키마

```python
class AssetTypeCodeRead(BaseModel):
    type_key: str
    code: str
    label: str
    sort_order: int
    is_active: bool

class AssetTypeCodeCreate(BaseModel):
    type_key: str = Field(pattern=r'^[a-z][a-z0-9_]{0,29}$')  # 영문 소문자 시작, 소문자+숫자+언더스코어, 1~30자
    code: str = Field(pattern=r'^[A-Z]{3}$')                    # 영문 대문자 정확히 3자리
    label: str = Field(min_length=1, max_length=50)
    sort_order: int = 0

class AssetTypeCodeUpdate(BaseModel):
    label: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    # code, type_key 변경 불가
```

### 4.3 기존 Asset API 변경

- `POST /api/v1/assets`: `asset_code` 자동 생성. payload에서 제거.
- `PATCH /api/v1/assets/{id}`: `asset_type` 변경 시 400 에러 반환.
- `GET /api/v1/assets`: 응답에 `asset_code` 포함 (기존과 동일).

---

## 5. 시스템관리 페이지 탭 구조

### 5.1 탭 구성

```
[공통] [영업관리] [프로젝트관리]
```

| 탭 | 표시 조건 | 내용 |
|----|----------|------|
| 공통 | 항상 | 기본 설정, 용어 관리 |
| 영업관리 | `accounting` in ENABLED_MODULES | 사업유형 관리 |
| 프로젝트관리 | `infra` in ENABLED_MODULES | 자산유형 관리 |

### 5.2 탭 구현

- `system.html`에서 Jinja2 `enabled_modules` 변수로 탭 표시/숨김
- 탭 전환은 기존 `infra_common.css`의 `.tab-nav` + `.tab-btn` 패턴 재사용
- URL hash로 탭 상태 유지 (`/system#infra`)

### 5.3 자산유형 관리 UI (프로젝트관리 탭 내부)

- 테이블: type_key, 코드, 표시명, 정렬순서, 활성, 액션(수정)
- 추가 모달: type_key 입력, 코드(영문3자리) 입력, 표시명, 정렬순서
- 수정 모달: 표시명, 정렬순서, 활성 여부만 편집 가능 (type_key, code는 읽기 전용)
- 삭제: 자산 존재 시 차단 메시지, 없으면 확인 후 삭제

---

## 6. 프론트엔드 변경

### 6.1 utils.js 추가

```javascript
let _assetTypeCodesCache = null;

async function loadAssetTypeCodes() {
    if (!_assetTypeCodesCache) {
        _assetTypeCodesCache = await apiFetch('/api/v1/asset-type-codes');
    }
    return _assetTypeCodesCache;
}

// system.js에서 자산유형 CRUD 성공 후 반드시 호출
function invalidateAssetTypeCodesCache() {
    _assetTypeCodesCache = null;
}

async function populateAssetTypeSelect(selectId, includeAll = false) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const types = await loadAssetTypeCodes();
    sel.textContent = '';
    if (includeAll) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = '전체';
        sel.appendChild(opt);
    }
    types.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.type_key;
        opt.textContent = t.label;
        sel.appendChild(opt);
    });
}

function getAssetTypeLabel(typeKey) {
    if (!_assetTypeCodesCache) return typeKey;
    const found = _assetTypeCodesCache.find(t => t.type_key === typeKey);
    return found ? found.label : typeKey;
}
```

### 6.2 infra_assets.js 변경

- `ASSET_TYPE_MAP` 상수 제거
- AG Grid `valueFormatter`에서 `getAssetTypeLabel()` 사용
- `initGrid()` 전에 `await loadAssetTypeCodes()` 호출
- 등록 모달의 유형 `<select>`: `populateAssetTypeSelect('asset-type')` 로 동적 생성
- 필터 드롭다운: `populateAssetTypeSelect('filter-type', true)` 로 동적 생성

### 6.3 infra_assets.html 변경

- 등록 모달의 유형 `<select>`: 하드코딩 option 제거, 빈 `<select>` 유지
- 필터바의 유형 `<select>`: 하드코딩 option 제거, 빈 `<select>` 유지
- 수정 모달에서 유형 필드를 읽기 전용으로 변경 (disabled 또는 텍스트 표시)

### 6.4 system.html / system.js 변경

- 탭 네비게이션 HTML 추가
- 기존 섹션을 탭 컨텐츠 div로 래핑
- 프로젝트관리 탭에 자산유형 테이블 + 추가/수정 모달 추가
- `loadAssetTypeTable()`, `submitAssetType()` 등 CRUD 함수 추가

### 6.5 기타 infra JS 파일

- `infra_inventory_assets.js`: 유형 필터 드롭다운 동적 로드
- `infra_port_maps.js`: 직접적 유형 참조 없으면 변경 불필요
- Excel Import: `infra_importer.py`의 `_derive_asset_type()` → 유효 type_key 검증 추가

---

## 7. 파일 목록

### 신규 생성

| 파일 | 설명 |
|------|------|
| `app/modules/common/models/asset_type_code.py` | AssetTypeCode 모델 |
| `app/modules/common/schemas/asset_type_code.py` | Create/Update/Read 스키마 |
| `app/modules/common/services/asset_type_code.py` | CRUD + seed + validation |
| `app/modules/common/routers/asset_type_codes.py` | API 라우터 |
| `alembic/versions/xxxx_add_asset_type_codes.py` | Migration |

### 수정

| 파일 | 변경 내용 |
|------|----------|
| `app/modules/common/models/__init__.py` | AssetTypeCode import 추가 |
| `app/modules/common/routers/__init__.py` | 라우터 등록 |
| `app/modules/infra/services/asset_service.py` | 코드 자동 생성 로직 변경, 유형 변경 차단 |
| `app/static/js/utils.js` | loadAssetTypeCodes, populateAssetTypeSelect 추가 |
| `app/static/js/infra_assets.js` | 하드코딩 제거, 동적 로드 |
| `app/modules/infra/templates/infra_assets.html` | select 옵션 동적화, 수정 시 유형 읽기 전용 |
| `app/templates/system.html` | 탭 구조 + 자산유형 섹션 추가 |
| `app/static/js/system.js` | 탭 전환 + 자산유형 CRUD 함수 |
| `app/modules/infra/services/infra_importer.py` | 유효 type_key 검증 |

---

## 8. 범위 외 (이 스펙에 포함하지 않음)

- 자산유형별 아이콘/색상 커스터마이즈
- 유형 코드(3자리) 변경 기능 (코드 불변)
- 자산 코드 수동 입력 허용
- 자산 유형 변경 허용
