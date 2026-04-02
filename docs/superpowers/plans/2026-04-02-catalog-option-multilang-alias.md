# 카탈로그 속성 옵션 다국어 라벨 + Alias 관리 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 속성 옵션에 영문 기본 라벨 + 한글 보조 라벨을 분리하고, 한/영 전환 UI와 인라인 alias 관리를 구현한다.

**Architecture:** DB에 `label_kr` 컬럼 추가, 기존 한글 label→label_kr 이동 + 영문 backfill. 서비스에서 label_kr 저장 시 alias 자동 동기화. 프론트엔드에서 한/영 토글, 통합 검색, 모달 내 alias 태그 관리.

**Tech Stack:** PostgreSQL (Alembic), SQLAlchemy 2.0, Pydantic, FastAPI, AG Grid, Vanilla JS

**Spec:** `docs/superpowers/specs/2026-04-02-catalog-option-multilang-alias-design.md`

---

### Task 1: 마이그레이션 — label_kr 컬럼 추가 + 데이터 backfill

**Files:**
- Create: `alembic/versions/0055_option_label_kr.py`

- [ ] **Step 1: 마이그레이션 파일 작성**

```python
# alembic/versions/0055_option_label_kr.py
# 1. label_kr VARCHAR(100) NULL 컬럼 추가
# 2. 기존 한글 label → label_kr 복사
# 3. label을 영문으로 교체 (BACKFILL_MAP 딕셔너리 사용)
# 4. label_kr auto alias 등록 (ON CONFLICT DO NOTHING)
# 5. 검증 로그
```

BACKFILL_MAP은 모든 속성(domain, imp_type, platform, deployment_model, license_model, product_family, vendor_series)의 기존 ~100개 옵션에 대해 `{(attribute_key, option_key): {"label": "영문명", "label_kr": "한글명"}}` 형태로 작성한다.

한글 label이 없는 옵션(UTM, IPS, WAF 등)은 label 유지, label_kr은 NULL.

- [ ] **Step 2: 마이그레이션 테스트 실행**

Run: `alembic upgrade head`
Expected: 컬럼 추가 + 데이터 교체 완료, 오류 없음

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/0055_option_label_kr.py
git commit -m "feat: add label_kr column to catalog_attribute_options with backfill"
```

---

### Task 2: 모델 + 스키마 변경

**Files:**
- Modify: `app/modules/infra/models/catalog_attribute_option.py`
- Modify: `app/modules/infra/schemas/catalog_attribute_option.py`

- [ ] **Step 1: 모델에 label_kr 컬럼 추가**

`app/modules/infra/models/catalog_attribute_option.py`에 추가:

```python
label_kr: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

`label` 컬럼 바로 아래에 배치.

- [ ] **Step 2: 스키마에 label_kr + label 한글 validator 추가**

`app/modules/infra/schemas/catalog_attribute_option.py` 변경:

```python
import re
from pydantic import field_validator

_HANGUL_RE = re.compile(r"[\uAC00-\uD7A3\u3130-\u318F]")

class CatalogAttributeOptionBase(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    label_kr: str | None = Field(default=None, max_length=100)
    # ... 기존 필드 유지

    @field_validator("label")
    @classmethod
    def label_must_not_contain_korean(cls, v: str) -> str:
        if _HANGUL_RE.search(v):
            raise ValueError("영문 라벨에는 한글을 포함할 수 없습니다.")
        return v
```

`CatalogAttributeOptionUpdate`에도 `label_kr: str | None = None` 추가 + 같은 validator.

`CatalogAttributeOptionRead`에 추가:

```python
label_kr: str | None = None
domain_option_label_kr: str | None = None
aliases: list[dict] = Field(default_factory=list)
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/infra/models/catalog_attribute_option.py app/modules/infra/schemas/catalog_attribute_option.py
git commit -m "feat: add label_kr field to option model and schema with Korean validator"
```

---

### Task 3: 서비스 변경 — alias 자동 동기화 + 중복 가드 확장

**Files:**
- Modify: `app/modules/infra/services/catalog_attribute_service.py`

- [ ] **Step 1: `_sync_label_kr_auto_alias` 헬퍼 함수 추가**

파일 상단 import에 `CatalogAttributeOptionAlias` 추가.
`catalog_alias_service`에서 `normalize_catalog_alias` import.

```python
from app.modules.infra.models.catalog_attribute_option_alias import CatalogAttributeOptionAlias
from app.modules.infra.services.catalog_alias_service import normalize_catalog_alias

def _sync_label_kr_auto_alias(db: Session, option: CatalogAttributeOption) -> None:
    """label_kr 변경 시 label_kr_auto alias를 동기화한다."""
    existing_auto = db.scalar(
        select(CatalogAttributeOptionAlias).where(
            CatalogAttributeOptionAlias.attribute_option_id == option.id,
            CatalogAttributeOptionAlias.match_type == "label_kr_auto",
        )
    )
    label_kr = (option.label_kr or "").strip()
    if not label_kr:
        if existing_auto:
            db.delete(existing_auto)
        return
    normalized = normalize_catalog_alias(label_kr)
    if existing_auto:
        existing_auto.alias_value = label_kr
        existing_auto.normalized_alias = normalized
    else:
        # ON CONFLICT 방지: 같은 normalized_alias가 수동 alias로 이미 존재하면 skip
        conflict = db.scalar(
            select(CatalogAttributeOptionAlias).where(
                CatalogAttributeOptionAlias.attribute_option_id == option.id,
                CatalogAttributeOptionAlias.normalized_alias == normalized,
            )
        )
        if conflict is None:
            db.add(CatalogAttributeOptionAlias(
                attribute_option_id=option.id,
                alias_value=label_kr,
                normalized_alias=normalized,
                match_type="label_kr_auto",
            ))
    db.flush()
```

- [ ] **Step 2: create_attribute_option, update_attribute_option에 호출 추가**

`create_attribute_option`에서 기존 `db.add(option); db.commit(); db.refresh(option)` 블록을 **교체**:

```python
    db.add(option)
    db.flush()  # id 할당 (commit 전)
    _sync_label_kr_auto_alias(db, option)
    db.commit()
    db.refresh(option)
```

`update_attribute_option`에서 기존 `for ... setattr; db.commit()` 블록을 **교체**:

```python
    for field, value in updates.items():
        setattr(option, field, value)
    _sync_label_kr_auto_alias(db, option)
    db.commit()
    db.refresh(option)
```

주의: 기존 `db.commit()` 호출이 **두 번** 나오지 않도록 기존 블록을 교체한다.

- [ ] **Step 3: `_guard_same_attribute_option_duplicate`에 label_kr 비교 추가**

기존 함수 시그니처에 `label_kr: str | None = None` 파라미터 추가.

```python
def _guard_same_attribute_option_duplicate(
    db, attribute_id, option_key, label, *, label_kr=None, exclude_option_id=None
):
    # ... 기존 로직 유지
    if label_kr:
        normalized_label_kr = label_kr.strip().casefold()
        for candidate in candidates:
            if exclude_option_id and candidate.id == exclude_option_id:
                continue
            if candidate.label_kr and StringOrEmpty(candidate.label_kr).casefold() == normalized_label_kr:
                raise DuplicateError("같은 한글 아이템명이 이미 존재합니다.")
```

`_guard_cross_attribute_option_duplicate`에도 동일하게 `label_kr` 파라미터 추가 + 비교 로직.

호출부(`create_attribute_option`, `update_attribute_option`)에서 `label_kr=payload.label_kr` 또는 `label_kr=next_label_kr` 전달.

- [ ] **Step 4: `_enrich_option_scope`에 label_kr 추가**

```python
def _enrich_option_scope(option: CatalogAttributeOption) -> None:
    domain_option = getattr(option, "domain_option", None)
    option.domain_option_key = domain_option.option_key if domain_option else None
    option.domain_option_label = domain_option.label if domain_option else None
    option.domain_option_label_kr = domain_option.label_kr if domain_option else None
```

- [ ] **Step 5: `list_attribute_options` 응답에 aliases 포함 (N+1 방지)**

`selectinload`로 aliases를 eager load하여 N+1 쿼리 방지:

```python
from sqlalchemy.orm import selectinload

def list_attribute_options(db, attribute_id, active_only=False):
    get_attribute(db, attribute_id)
    stmt = (
        select(CatalogAttributeOption)
        .where(CatalogAttributeOption.attribute_id == attribute_id)
        .options(selectinload(CatalogAttributeOption.aliases))
        .order_by(CatalogAttributeOption.sort_order.asc(), CatalogAttributeOption.id.asc())
    )
    if active_only:
        stmt = stmt.where(CatalogAttributeOption.is_active.is_(True))
    options = list(db.scalars(stmt))
    for option in options:
        _enrich_option_scope(option)
        option.aliases = [
            {"id": a.id, "alias_value": a.alias_value, "match_type": a.match_type}
            for a in (option.aliases or [])
        ]
    return options
```

`_get_option`에서도 `selectinload`를 사용하여 aliases를 eager load하고 동일 형태로 주입.

- [ ] **Step 6: Commit**

```bash
git add app/modules/infra/services/catalog_attribute_service.py
git commit -m "feat: auto-sync label_kr alias, extend duplicate guards and enrichment"
```

---

### Task 4: 프론트엔드 — 한/영 토글 + 투영 함수

**Files:**
- Modify: `app/static/js/infra_product_catalog.js`
- Modify: `app/templates/product_catalog.html`

- [ ] **Step 1: JS 상수 + 헬퍼 추가**

`infra_product_catalog.js` 상단 상수 영역에:

```javascript
const CATALOG_LABEL_LANG_KEY = "catalog_label_lang";

function getCatalogLabelLang() {
  const lang = localStorage.getItem(CATALOG_LABEL_LANG_KEY);
  return lang === "en" ? "en" : "ko";
}

function setCatalogLabelLang(lang) {
  localStorage.setItem(CATALOG_LABEL_LANG_KEY, lang === "en" ? "en" : "ko");
}

function getCatalogOptionDisplayLabel(option) {
  if (!option) return "";
  const lang = getCatalogLabelLang();
  if (lang === "ko") return option.label_kr || option.label || option.option_key;
  return option.label || option.option_key;
}
```

- [ ] **Step 2: toolbar에 한/영 토글 버튼 추가**

`product_catalog.html`의 catalog-toolbar 안에 열 설정 버튼 앞에:

```html
<button type="button" class="btn btn-compact" id="btn-catalog-lang-toggle">한</button>
```

- [ ] **Step 3: 토글 이벤트 연결**

`infra_product_catalog.js`의 초기화 영역에:

```javascript
document.getElementById("btn-catalog-lang-toggle")?.addEventListener("click", async () => {
  const current = getCatalogLabelLang();
  const next = current === "ko" ? "en" : "ko";
  setCatalogLabelLang(next);
  document.getElementById("btn-catalog-lang-toggle").textContent = next === "ko" ? "한" : "EN";
  applyCatalogClassificationAliases();
  // 그리드 row data도 재투영하여 표시 언어 반영
  const projected = await projectCatalogRowsForCurrentLayout(_catalogRows || []);
  if (catalogGridApi) catalogGridApi.setGridOption("rowData", projected);
  await rebuildCatalogClassificationTree(_catalogRows || []);
});
```

초기 로드 시 버튼 텍스트도 동기화.

- [ ] **Step 4: `projectCatalogRowForCurrentLayout` 수정 — lang 기반 라벨 선택**

기존 레벨 투영 + attr 투영에서 `getCatalogLabelLang()` 참조:

```javascript
// 옵션맵 구성 시 label_kr도 포함
// optionMap: Map<optionKey, {label, label_kr}>
// 투영 시:
const lang = getCatalogLabelLang();
const displayLabel = lang === "ko"
  ? (optionData.label_kr || optionData.label || optionKey)
  : (optionData.label || optionKey);
```

`buildCatalogAttributeOptionMaps` 반환 형식을 `Map<key, {label, label_kr}>` 형태로 확장.

- [ ] **Step 5: 트리 노드 라벨도 lang 기반 전환**

`rebuildCatalogClassificationTree`에서 노드 생성 시:

```javascript
const lang = getCatalogLabelLang();
const optionLabel = lang === "ko"
  ? (option?.label_kr || option?.label || optionKey)
  : (option?.label || optionKey);
```

- [ ] **Step 6: Commit**

```bash
git add app/static/js/infra_product_catalog.js app/templates/product_catalog.html
git commit -m "feat: add ko/en label toggle for catalog classification"
```

---

### Task 5: 프론트엔드 — 통합 검색

**Files:**
- Modify: `app/static/js/infra_product_catalog.js`

- [ ] **Step 1: 옵션 캐시에 label_kr, aliases 포함**

`loadCatalogAttributeOptions` 응답에 이미 `label_kr`, `aliases`가 포함된다 (Task 3에서 서비스 수정). 캐시에 그대로 저장되므로 추가 코드 변경 불필요. 확인만 한다.

- [ ] **Step 2: 트리 필터에 통합 검색 적용**

트리 검색/필터 로직에서 노드 매칭 기준 확장:

```javascript
function matchesCatalogOptionSearch(option, searchTerm) {
  const term = searchTerm.toLowerCase();
  if ((option.option_key || "").toLowerCase().includes(term)) return true;
  if ((option.label || "").toLowerCase().includes(term)) return true;
  if ((option.label_kr || "").toLowerCase().includes(term)) return true;
  if ((option.aliases || []).some((a) => (a.alias_value || "").toLowerCase().includes(term))) return true;
  return false;
}
```

기존 트리 필터/그리드 필터에서 이 함수를 사용하도록 교체.

- [ ] **Step 3: Commit**

```bash
git add app/static/js/infra_product_catalog.js
git commit -m "feat: unified search across option_key, label, label_kr, aliases"
```

---

### Task 6: 프론트엔드 — 아이템 모달 변경 (label_kr + alias 태그)

**Files:**
- Modify: `app/templates/product_catalog.html`
- Modify: `app/static/js/infra_product_catalog.js`
- Modify: `app/static/css/infra_common.css`

- [ ] **Step 1: 모달 HTML 수정 — label_kr 필드 + alias 태그 영역**

`product_catalog.html`의 `modal-catalog-classification-node` 수정:

```html
<dialog id="modal-catalog-classification-node" class="modal modal-lg">
  <h2 id="modal-catalog-classification-node-title">속성값 등록</h2>
  <form class="form-grid-single">
    <input type="hidden" id="catalog-classification-node-id">
    <fieldset class="modal-group">
      <legend class="modal-group-title">속성값 정보</legend>
      <div class="form-grid">
        <label>대상 속성 <input type="text" id="catalog-classification-node-parent" readonly></label>
        <label>속성값 키 <input type="text" id="catalog-classification-node-code" required></label>
        <label>영문명 <input type="text" id="catalog-classification-node-name" required></label>
        <label>한글명 <input type="text" id="catalog-classification-node-name-kr"></label>
        <label class="hidden" id="catalog-classification-node-domain-wrap">도메인
          <select id="catalog-classification-node-domain">
            <option value="">도메인 선택</option>
          </select>
        </label>
        <label>정렬순서 <input type="number" id="catalog-classification-node-sort-order" value="100"></label>
        <label>상태
          <select id="catalog-classification-node-active">
            <option value="true">활성</option>
            <option value="false">비활성</option>
          </select>
        </label>
      </div>
    </fieldset>
    <fieldset class="modal-group" id="catalog-node-alias-section">
      <legend class="modal-group-title">별칭</legend>
      <div class="catalog-alias-tags" id="catalog-node-alias-tags"></div>
      <p class="modal-hint">※ 한글명은 자동 등록됩니다</p>
    </fieldset>
    <fieldset class="modal-group">
      <legend class="modal-group-title">설명</legend>
      <div class="form-grid">
        <label class="full-width"><textarea id="catalog-classification-node-note" rows="3"></textarea></label>
      </div>
    </fieldset>
  </form>
  <div class="modal-actions">
    <button type="button" id="btn-catalog-classification-node-cancel" class="btn btn-secondary">취소</button>
    <button type="button" id="btn-catalog-classification-node-submit" class="btn btn-primary">저장</button>
  </div>
</dialog>
```

- [ ] **Step 2: CSS — alias 태그 스타일**

`app/static/css/infra_common.css`에 추가:

```css
.catalog-alias-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 32px;
}
.catalog-alias-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 13px;
  background: var(--secondary-color);
  color: var(--text-color);
  border: 1px solid var(--border-color);
}
.catalog-alias-tag.is-auto {
  background: var(--info-bg, #e8f4fd);
  border-color: var(--info-border, #b3d9f2);
}
.catalog-alias-tag-remove {
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  opacity: 0.6;
  border: none;
  background: none;
  padding: 0 2px;
  color: inherit;
}
.catalog-alias-tag-remove:hover { opacity: 1; }
.catalog-alias-tag-remove:disabled { opacity: 0.3; cursor: default; }
.catalog-alias-add-input {
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 13px;
  width: 120px;
  background: var(--bg-primary);
  color: var(--text-color);
}
```

- [ ] **Step 3: JS — 모달 open/save 수정 + alias 태그 관리**

`openCatalogClassificationNodeModal`에 label_kr 필드 세팅 추가:

```javascript
document.getElementById("catalog-classification-node-name-kr").value = option?.label_kr || "";
// alias 태그 렌더
renderCatalogNodeAliasTags(option?.id || null, option?.aliases || []);
// 편집 모드일 때만 alias 섹션 표시
document.getElementById("catalog-node-alias-section").classList.toggle("is-hidden", !option?.id);
```

`saveCatalogClassificationNode`에 label_kr payload 추가:

```javascript
payload.label_kr = document.getElementById("catalog-classification-node-name-kr").value.trim() || null;
```

프론트엔드 중복 검사에 label_kr 포함:

```javascript
const sameLabel = String(item.label || "").trim().toLocaleLowerCase("ko-KR") === payload.label.toLocaleLowerCase("ko-KR");
const sameLabelKr = payload.label_kr && String(item.label_kr || "").trim().toLocaleLowerCase("ko-KR") === payload.label_kr.toLocaleLowerCase("ko-KR");
return sameKey || sameLabel || sameLabelKr;
```

Alias 태그 렌더/추가/삭제 함수:

```javascript
function renderCatalogNodeAliasTags(optionId, aliases) {
  const container = document.getElementById("catalog-node-alias-tags");
  container.replaceChildren();
  (aliases || []).forEach((alias) => {
    const tag = document.createElement("span");
    tag.className = "catalog-alias-tag" + (alias.match_type === "label_kr_auto" ? " is-auto" : "");
    tag.textContent = alias.alias_value;
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "catalog-alias-tag-remove";
    removeBtn.textContent = "×";
    removeBtn.disabled = alias.match_type === "label_kr_auto";
    if (alias.match_type !== "label_kr_auto") {
      removeBtn.addEventListener("click", () => deleteCatalogNodeAlias(alias.id, optionId));
    }
    tag.appendChild(removeBtn);
    container.appendChild(tag);
  });
  // + 추가 버튼
  if (optionId) {
    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "btn btn-compact";
    addBtn.textContent = "+ 추가";
    addBtn.addEventListener("click", () => showCatalogNodeAliasInput(optionId));
    container.appendChild(addBtn);
  }
}

function showCatalogNodeAliasInput(optionId) {
  const container = document.getElementById("catalog-node-alias-tags");
  if (container.querySelector(".catalog-alias-add-input")) return;
  const input = document.createElement("input");
  input.type = "text";
  input.className = "catalog-alias-add-input";
  input.placeholder = "별칭 입력";
  // + 추가 버튼 앞에 삽입
  const addBtn = container.querySelector(".btn");
  container.insertBefore(input, addBtn);
  input.focus();
  input.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const value = input.value.trim();
      if (value) await addCatalogNodeAlias(optionId, value);
      input.remove();
    } else if (e.key === "Escape") {
      input.remove();
    }
  });
  input.addEventListener("blur", () => input.remove());
}

async function addCatalogNodeAlias(optionId, aliasValue) {
  const attributeKey = document.getElementById("catalog-classification-node-parent").dataset.attributeKey;
  await apiFetch("/api/v1/catalog-integrity/attribute-aliases", {
    method: "POST",
    body: { attribute_key: attributeKey, option_id: optionId, alias_value: aliasValue },
  });
  invalidateCatalogAttributeOptionCache(attributeKey);
  const options = await loadCatalogAttributeOptions(attributeKey, false);
  const option = options.find((item) => item.id === optionId);
  renderCatalogNodeAliasTags(optionId, option?.aliases || []);
}

async function deleteCatalogNodeAlias(aliasId, optionId) {
  await apiFetch(`/api/v1/catalog-integrity/attribute-aliases/${aliasId}`, { method: "DELETE" });
  const attributeKey = document.getElementById("catalog-classification-node-parent").dataset.attributeKey;
  invalidateCatalogAttributeOptionCache(attributeKey);
  const options = await loadCatalogAttributeOptions(attributeKey, false);
  const option = options.find((item) => item.id === optionId);
  renderCatalogNodeAliasTags(optionId, option?.aliases || []);
}
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/product_catalog.html app/static/js/infra_product_catalog.js app/static/css/infra_common.css
git commit -m "feat: add label_kr field and inline alias tags to option modal"
```

---

### Task 7: 문서 갱신

**Files:**
- Modify: `docs/guidelines/infra.md`
- Modify: `docs/PROJECT_STRUCTURE.md`

- [ ] **Step 1: infra.md 상태값/코드값 규칙에 label_kr 규칙 추가**

```markdown
- `CatalogAttributeOption.label`: 영문 기본 라벨. 한글(완성형·자모) 포함 불가.
- `CatalogAttributeOption.label_kr`: 한글 보조 라벨. 저장 시 `label_kr_auto` alias 자동 동기화.
```

- [ ] **Step 2: PROJECT_STRUCTURE.md 마이그레이션 목록에 0054, 0055 추가**

0054는 이미 이번 세션에서 생성되었으나 PROJECT_STRUCTURE.md에 미반영.

- [ ] **Step 3: Commit**

```bash
git add docs/guidelines/infra.md docs/PROJECT_STRUCTURE.md
git commit -m "docs: update infra guidelines and project structure for label_kr"
```
