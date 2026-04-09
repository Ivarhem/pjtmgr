# 자산 등록 모달 카탈로그 선택 ModalCombobox 전환

> 멀티에이전트로 진행할 때는 `docs/guidelines/agent_workflow.md`와 필요한 `docs/agents/*.md`를 기준으로 역할을 나눈다. 이 문서의 체크박스는 작업 추적용이다.

**Goal:** 자산 등록 모달의 커스텀 카탈로그 검색 위젯을 `ModalCombobox` 패턴으로 교체하여 제조사/제품군 combobox와 UI/코드 일관성을 확보한다.

**Architecture:** 기존 `infra_product_catalog.js`의 `ModalCombobox` 클래스에 `maxDisplay` 옵션(표시 제한)을 추가한다. 자산 등록 모달의 HTML을 `modal-combobox` 구조로 교체하고, JS에서 커스텀 검색 로직(~100줄)을 제거 후 ModalCombobox 인스턴스로 대체한다. 모달 열기 시 전체 카탈로그 목록을 API로 1회 로드하여 로컬 필터링한다.

**Tech Stack:** JavaScript (vanilla), HTML, CSS

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `app/static/js/infra_product_catalog.js:1106-1135` | `ModalCombobox._render()`에 `maxDisplay` 제한 추가 |
| Modify | `app/modules/infra/templates/infra_assets.html:96-103` | HTML 구조를 `modal-combobox` 클래스로 교체 |
| Modify | `app/static/js/infra_assets.js` | 커스텀 검색 로직 제거, ModalCombobox 인스턴스 사용 |
| Modify | `app/static/css/infra_common.css:1487-1527` | 사용하지 않는 `.catalog-search-wrap`, `.catalog-dropdown-*` CSS 정리 |

---

### Task 1: ModalCombobox에 maxDisplay 옵션 추가

**Files:**
- Modify: `app/static/js/infra_product_catalog.js:1060-1135`

- [ ] **Step 1: constructor에 maxDisplay 옵션 추가**

`app/static/js/infra_product_catalog.js`의 `ModalCombobox` constructor를 수정한다:

```javascript
constructor({ inputId, hiddenId, dropdownId, onSelect, maxDisplay = 0 }) {
  this.input = document.getElementById(inputId);
  this.hidden = document.getElementById(hiddenId);
  this.dropdown = document.getElementById(dropdownId);
  this.onSelect = onSelect || (() => {});
  this.maxDisplay = maxDisplay;   // 0 = 제한 없음
  this.items = [];
  this._focusIdx = -1;
  this._bound = false;
}
```

- [ ] **Step 2: _render()에 표시 제한 로직 추가**

`_render()` 메서드에서 `maxDisplay > 0`일 때 아이템을 잘라내고, 잘렸으면 안내 메시지를 표시한다:

```javascript
_render(items) {
  this.dropdown.textContent = "";
  this._focusIdx = -1;
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "modal-combobox-empty";
    empty.textContent = "검색 결과 없음";
    this.dropdown.appendChild(empty);
    setElementHidden(this.dropdown, false);
    return;
  }
  const totalCount = items.length;
  const display = this.maxDisplay > 0 ? items.slice(0, this.maxDisplay) : items;
  display.forEach((item, idx) => {
    const div = document.createElement("div");
    div.className = "modal-combobox-option";
    div.dataset.value = item.value;
    div.dataset.idx = idx;
    div.textContent = item.label;
    if (item.hint) {
      const span = document.createElement("span");
      span.className = "combobox-hint";
      span.textContent = item.hint;
      div.appendChild(span);
    }
    div.addEventListener("mousedown", (e) => {
      e.preventDefault();
      this._select(item);
    });
    this.dropdown.appendChild(div);
  });
  if (this.maxDisplay > 0 && totalCount > this.maxDisplay) {
    const more = document.createElement("div");
    more.className = "modal-combobox-empty";
    more.textContent = `외 ${totalCount - this.maxDisplay}건 — 검색어를 더 입력하세요`;
    this.dropdown.appendChild(more);
  }
  setElementHidden(this.dropdown, false);
}
```

- [ ] **Step 3: 브라우저에서 기존 제조사/제품군 combobox가 정상 동작하는지 확인**

제품 카탈로그 페이지에서 제조사 combobox, 제품군 combobox가 기존과 동일하게 작동하는지 확인한다. `maxDisplay` 기본값이 0이므로 기존 동작에 영향이 없어야 한다.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/infra_product_catalog.js
git commit -m "feat: add maxDisplay option to ModalCombobox for large item sets"
```

---

### Task 2: 자산 등록 모달 HTML 구조 교체

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html:96-103`

- [ ] **Step 1: catalog-search-wrap을 modal-combobox 구조로 교체**

`infra_assets.html`에서 기존 카탈로그 검색 영역:

```html
<label class="full-width">
  카탈로그 제품 <span class="text-danger">*</span>
  <div class="catalog-search-wrap">
    <input type="text" id="catalog-search" placeholder="제조사 또는 모델명 검색" autocomplete="off">
    <input type="hidden" id="catalog-id">
    <div id="catalog-dropdown" class="catalog-dropdown hidden"></div>
  </div>
</label>
```

다음으로 교체:

```html
<label class="full-width">
  카탈로그 제품 <span class="text-danger">*</span>
  <div class="modal-combobox">
    <input type="text" id="catalog-search" placeholder="제조사 또는 모델명 검색" autocomplete="off">
    <input type="hidden" id="catalog-id">
    <div id="catalog-dropdown" class="modal-combobox-dropdown hidden"></div>
  </div>
</label>
```

변경 사항: `catalog-search-wrap` → `modal-combobox`, `catalog-dropdown` → `modal-combobox-dropdown` 클래스 추가. 요소 ID는 그대로 유지한다 (JS에서 ID로 참조하는 곳이 많으므로).

- [ ] **Step 2: Commit**

```bash
git add app/modules/infra/templates/infra_assets.html
git commit -m "refactor: switch catalog search HTML to modal-combobox structure"
```

---

### Task 3: JS — ModalCombobox 인스턴스로 전환

**Files:**
- Modify: `app/static/js/infra_assets.js`

이 태스크가 핵심이다. 커스텀 카탈로그 검색 로직을 제거하고 ModalCombobox 인스턴스로 교체한다.

- [ ] **Step 1: 카탈로그 목록 로드 함수와 combobox 인스턴스 추가**

`infra_assets.js`에서 `_catalogSearchTimer` 선언(line 2059) 바로 위, `/* ── Modal (간소화 등록) ── */` 아래에 다음을 추가한다:

```javascript
let _catalogCombobox = null;
let _catalogItemsCache = [];

function getCatalogCombobox() {
  if (!_catalogCombobox) {
    _catalogCombobox = new ModalCombobox({
      inputId: "catalog-search",
      hiddenId: "catalog-id",
      dropdownId: "catalog-dropdown",
      maxDisplay: 50,
      onSelect: (item) => {
        const full = _catalogItemsCache.find((p) => String(p.id) === String(item.value));
        if (full) selectCatalogItem(full);
      },
    });
    _catalogCombobox.bind();
  }
  return _catalogCombobox;
}

async function loadCatalogListForModal(productType = "") {
  try {
    let url = "/api/v1/product-catalog";
    if (productType) url += "?product_type=" + encodeURIComponent(productType);
    const items = await apiFetch(url);
    _catalogItemsCache = items;
    const combo = getCatalogCombobox();
    combo.setItems(
      items
        .filter((item) => buildCatalogClassificationPath(item) && buildCatalogClassificationPath(item) !== "분류 미지정")
        .map((item) => {
          const kindLabel = CATALOG_KIND_LABELS[item.product_type] || item.product_type || "";
          const vendorModel = ((item.vendor || "") + " " + (item.name || "")).trim();
          return {
            value: String(item.id),
            label: `[${kindLabel}] ${vendorModel}`,
            hint: buildCatalogClassificationPath(item),
            aliases: [item.vendor || "", item.name || ""],
          };
        })
    );
  } catch (e) {
    showToast("카탈로그 목록을 불러올 수 없습니다: " + e.message, "error");
  }
}
```

- [ ] **Step 2: `_catalogSearchTimer` 변수 선언 삭제**

`let _catalogSearchTimer = null;` (line 2059)를 삭제한다.

- [ ] **Step 3: `_catalogSearchResults` 변수 선언 삭제**

`let _catalogSearchResults = [];` (line 408)를 삭제한다. 이 변수는 `_catalogItemsCache`로 대체된다.

- [ ] **Step 4: `renderCatalogDropdown()` 함수 삭제**

lines 2259-2291 전체를 삭제한다:

```javascript
function renderCatalogDropdown(items) {
  // ... 전체 삭제
}
```

- [ ] **Step 5: `onCatalogSearchInput()` 함수 삭제**

lines 2294-2309 전체를 삭제한다:

```javascript
async function onCatalogSearchInput() {
  // ... 전체 삭제
}
```

- [ ] **Step 6: 바깥 클릭 핸들러 삭제**

lines 2632-2637의 `document.addEventListener("click", ...)` 카탈로그 드롭다운 닫기 핸들러를 삭제한다:

```javascript
document.addEventListener("click", (e) => {
  const wrap = document.querySelector(".catalog-search-wrap");
  if (wrap && !wrap.contains(e.target)) {
    document.getElementById("catalog-dropdown").classList.add("hidden");
  }
});
```

ModalCombobox가 자체적으로 외부 클릭 시 닫기를 처리한다.

- [ ] **Step 7: catalog-search 이벤트 리스너 교체**

파일 하단의 이벤트 리스너 등록 부분(lines 3009-3019)에서:

```javascript
// 삭제:
document.getElementById("catalog-search").addEventListener("input", onCatalogSearchInput);
document.getElementById("catalog-search").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    if (_catalogSearchResults.length === 1) {
      selectCatalogItem(_catalogSearchResults[0]);
    }
  } else if (e.key === "Escape") {
    document.getElementById("catalog-dropdown").classList.add("hidden");
  }
});
```

ModalCombobox가 input, keydown, 외부 클릭을 모두 처리하므로 이 리스너들은 불필요하다.

- [ ] **Step 8: 상위분류 change 이벤트 수정**

lines 3020-3023의 상위분류 change 핸들러:

```javascript
// 기존:
document.getElementById("catalog-kind-filter-modal").addEventListener("change", () => {
  clearSelectedCatalog({ keepSearch: true });
  onCatalogSearchInput();
});
```

다음으로 교체:

```javascript
document.getElementById("catalog-kind-filter-modal").addEventListener("change", () => {
  clearSelectedCatalog({ keepSearch: true });
  const kind = document.getElementById("catalog-kind-filter-modal").value;
  loadCatalogListForModal(kind);
});
```

- [ ] **Step 9: `clearSelectedCatalog()` 수정**

기존 `clearSelectedCatalog()` (lines 2119-2132)에서 `_catalogSearchResults = [];`를 제거하고, combobox reset을 추가한다:

```javascript
function clearSelectedCatalog({ keepSearch = false } = {}) {
  const combo = getCatalogCombobox();
  if (keepSearch) {
    combo.hidden.value = "";
  } else {
    combo.reset();
  }
  const summary = document.getElementById("catalog-summary");
  summary.classList.add("hidden");
  summary.textContent = "";
  summary.classList.remove("placeholder-style");
  document.getElementById("btn-clear-catalog").classList.add("hidden");
  updateAssetNameHint("카탈로그를 선택하면 자산명이 자동 제안됩니다.");
  updateAssetHostnameHint("호스트명은 자산명 기준으로 자동 제안됩니다.");
  updateAssetRoleSuggestionHint("역할명 추천은 자산명 기준으로 참고용 제안만 제공합니다. 자동 선택되지 않습니다.");
  updateAssetSaveState();
}
```

- [ ] **Step 10: `openCreateModal()` 수정**

`openCreateModal()` (lines 2188-2242)에서 기존 드롭다운 초기화 코드를 combobox 초기화 + 목록 로드로 교체한다. 변경되는 부분만:

```javascript
// 기존의 이 줄들:
clearSelectedCatalog();
document.getElementById("catalog-kind-filter-modal").value = "hardware";
document.getElementById("catalog-dropdown").classList.add("hidden");
document.getElementById("inline-catalog-form").classList.add("hidden");

// 다음으로 교체:
clearSelectedCatalog();
document.getElementById("catalog-kind-filter-modal").value = "hardware";
document.getElementById("inline-catalog-form").classList.add("hidden");
```

그리고 `modal.showModal()` 직전에 목록 로드를 추가한다:

```javascript
await loadCatalogListForModal("hardware");
modal.showModal();
```

기존의 `document.getElementById("catalog-dropdown").classList.add("hidden");`은 `clearSelectedCatalog()`에서 `combo.reset()`이 처리하므로 불필요하다.

- [ ] **Step 11: `refreshAssetClassificationSelect()` 수정**

`_catalogSearchResults` 참조를 `_catalogItemsCache`로 교체한다:

```javascript
async function refreshAssetClassificationSelect(selectedId = null) {
  const currentCatalogId = Number(document.getElementById("catalog-id").value || 0);
  if (!currentCatalogId || !_catalogItemsCache?.length) {
    return;
  }
  const item = _catalogItemsCache.find((entry) => Number(entry.id) === currentCatalogId);
  updateAssetClassificationPreview(buildCatalogClassificationPath(item));
}
```

- [ ] **Step 12: `openInlineCatalogForm()` 수정**

line 2642의 드롭다운 닫기를 combobox 방식으로 교체:

```javascript
async function openInlineCatalogForm() {
  getCatalogCombobox()._close();
  const form = document.getElementById("inline-catalog-form");
  // ... 나머지 그대로
```

- [ ] **Step 13: Commit**

```bash
git add app/static/js/infra_assets.js
git commit -m "refactor: replace custom catalog search with ModalCombobox in asset modal"
```

---

### Task 4: CSS 정리

**Files:**
- Modify: `app/static/css/infra_common.css:1487-1527`

- [ ] **Step 1: 사용하지 않는 catalog-search-wrap / catalog-dropdown CSS 확인**

`catalog-search-wrap`과 `catalog-dropdown-*` 클래스가 다른 곳에서도 사용되는지 확인한다. 상세 패널 편집 모드(line 1797)에서 `catalog-search-wrap`을 동적 생성하고, CatalogCellEditor(line 179)에서 `ag-cell-catalog-dropdown`을 사용한다. 따라서:

- `.catalog-search-wrap` — 상세 패널에서 사용 중 → **유지**
- `.catalog-dropdown`, `.catalog-dropdown-item`, `.catalog-dropdown-add` — 상세 패널 드롭다운(line 1814, 1832, 1838, 1848)에서 사용 중 → **유지**
- `.catalog-dropdown.hidden` — 상세 패널에서 사용 → **유지**

결론: 상세 패널이 아직 같은 CSS를 사용하므로 이번에 CSS는 삭제하지 않는다. 상세 패널도 추후 ModalCombobox로 전환할 때 정리한다.

- [ ] **Step 2: Commit (skip)**

CSS 변경이 없으므로 커밋 불필요. 이 태스크는 확인만으로 완료.

---

### Task 5: 수동 검증

- [ ] **Step 1: 자산 등록 모달 검증**

브라우저에서 다음을 확인한다:
1. "자산 등록" 클릭 → 모달 열림
2. 카탈로그 검색 input에 텍스트 입력 → 드롭다운에 필터된 아이템 표시 (최대 50건 + "외 N건" 안내)
3. 키보드 탐색 (↑/↓/Enter/Escape) 정상 동작
4. 아이템 선택 → catalog-summary 표시, 자산명 자동 제안, 분류경로 미리보기
5. "선택 해제" 버튼 → combobox 초기화
6. 상위분류 변경 → 목록 재로드, 필터 결과 변경
7. "새 제품 등록" 인라인 폼 열기/취소/등록 정상 동작
8. 분류 미설정 제품은 드롭다운에 표시되지 않음

- [ ] **Step 2: 기존 기능 회귀 확인**

1. 제품 카탈로그 페이지 → 제조사 combobox, 제품군 combobox 정상 동작
2. 자산 그리드 → CatalogCellEditor 정상 동작 (이번 변경 스코프 밖이지만 회귀 확인)
3. 자산 상세 패널 → 카탈로그 검색 위젯 정상 동작

- [ ] **Step 3: Final commit (if any fix needed)**
