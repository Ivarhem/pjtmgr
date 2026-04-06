# 프론트엔드 작업 지침

> CSS, JavaScript, HTML 템플릿 작업 시 참조.

---

## JavaScript 명명 규칙

- **변수·함수**: `camelCase` (예: `loadData`, `gridApi`, `contractId`)
- **상수**: `UPPER_SNAKE_CASE` (예: `COL_STATE_KEY`, `CONTRACT_PERIOD_ID`)
- **AG Grid 컬럼 field**: 백엔드 응답 필드 그대로 `snake_case` 사용
- **공통 유틸 함수**: `utils.js`에 정의 (예: `fmt`, `fmtNumber`, `fmtPct`)
  - 페이지별 JS에서 재정의 금지 — `utils.js`가 `base.html`에서 전역 로드됨

## HTML / CSS 명명 규칙

- **HTML element ID**: `kebab-case` (예: `btn-save-ledger`, `grid-receipt`, `modal-add`)
- **CSS 클래스**: `kebab-case` (예: `filter-bar`, `grid-summary-bar`, `section-header`)
- **전역 CSS**: `base.css`(리셋·네비·버튼), `components.css`(재사용 컴포넌트)
- **페이지 전용 CSS**: `{page}.css` (예: `contract_detail.css`) — 해당 템플릿 `{% block styles %}`에서 로드
- `style=""` 인라인 스타일은 금지한다 (HTML 템플릿, JS 템플릿 리터럴 모두 해당). 상태 전환은 CSS 클래스(`is-hidden`, 의미 클래스 등)로 처리한다.
  - 초기 숨김: `style="display:none"` 대신 `is-hidden` 클래스 사용
  - JS 조건부 숨김: `el.style.display='none'` 대신 `el.classList.add('is-hidden')` / `classList.toggle('is-hidden', condition)` 사용
  - 테이블 열 너비: `style="width:..."` 대신 CSS 클래스 또는 `<col>` 사용
  - 공통 상태 전환은 `utils.js` helper와 `is-hidden`, `is-disabled` 같은 상태 클래스를 우선 사용
  - 예외: `position: fixed` 드롭다운의 동적 좌표 계산(`el.style.left/top/width`)은 허용

## CSS 작업 규칙

- `base.css` — 모든 페이지 공통 스타일. 수정 시 전 페이지에 영향.
- `components.css` — 여러 페이지에서 재사용되는 UI 컴포넌트(필터, 드롭다운, 그리드 등).
- `contract_detail.css` — 사업 상세 페이지 전용. 다른 페이지에 영향 없음.
- **새 페이지에 고유 스타일이 필요하면 `{page}.css`를 신규 생성**하고 해당 템플릿의 `{% block styles %}`에서 로드한다.
- 한 화면에서 버튼 크기·간격·색상 변형이 반복되면 인라인 스타일로 복제하지 말고 페이지 CSS에 유틸 클래스로 승격한다.
- AG Grid editor나 dropdown처럼 JS에서 반복 생성되는 UI도 인라인 `cssText` 대신 CSS 클래스로 스타일링한다.
- 페이지 공통 `.filter-bar label`과 컴포넌트 내부 라벨(`.chk-drop-menu label`)이 충돌하지 않도록, **컴포넌트 내부 label은 반드시 `flex-direction`을 명시**한다.
- **색상과 그림자(box-shadow)는 CSS 변수로 관리**한다. JS `cellStyle`에 하드코딩 색상 금지 → `cellClass` + CSS 클래스 사용.
  - `base.css` `:root`에 정의된 변수 사용 (예: `--danger-color`, `--cell-negative-color`, `--text-color-tertiary`)
  - 새 색상이 필요하면 `base.css`에 light/dark 모드 변수 쌍으로 추가

## UI/UX 원칙

- 언어: 한국어 전용
- 날짜 형식: `YYYY-MM-DD`
- 금액 표시: 천 단위 콤마, 원(₩) 단위
- 한 화면 안에서 신규/기존 UI가 섞일 때는 새로 건드린 영역을 현재 공용 패턴으로 정리한다. 같은 화면에 서로 다른 모달 구조, 버튼 크기, 라벨 배치, 임시 스타일이 공존한 채로 남기지 않는다.
- 사용자가 직접 조정할 수 있는 화면 상태는 기본적으로 저장/복원한다.
  - 예: 좌우 패널 너비, 트리 펼침/접힘, 마지막 선택 행, 상세 패널 열림/닫힘, 필터/탭 상태
  - 탐색형 화면(트리-목록-상세, 목록-상세, 다중 패널)은 새로고침이나 재진입 후에도 직전 작업 맥락을 최대한 복원해야 한다.
  - 저장 범위는 화면 단위로 나누고, 프로젝트/고객사처럼 컨텍스트 의존성이 있으면 key도 그 범위로 분리한다.
  - 브라우저 저장소 사용 시 key는 상수로 선언하고, 허용 범위/기본값/유효성 검사를 같이 둔다.
  - 저장 대상이 아닌 경우는 명시적 이유가 있어야 한다. 예: 보안상 민감한 임시 입력값, 서버 진실원본과 충돌하는 편집 중 draft
- 그리드는 AG Grid Community를 사용한다.
  - 행 단위 복사(Ctrl+C), 붙여넣기(Ctrl+V) 지원
  - 열 단위 선택 및 복사 지원
  - 셀 인라인 편집 허용 여부는 화면별로 명시
  - 커스텀 셀 에디터(CellEditor 클래스)는 `isPopup() { return true; }`로 설정한다. `false`이면 드롭다운/달력 등이 셀 `overflow`에 잘린다.
- 페이지 전환 없는 동적 업데이트는 HTMX를 사용한다.
- 테이블 중심 업무 화면으로 구성하며, 데이터 밀도를 우선한다.

### 화면 유형별 설계 원칙

- **사용자(영업) 화면** — 사업 중심, 입력 중심, 그리드 중심, 빠른 복사/붙여넣기 지원
- **경영진/관리자 화면** — 기간 중심, 숫자/요약 중심, 수정 기능 없음

---

## 모달 디자인 규칙

### 기본 구조

모든 모달은 HTML5 `<dialog>` + `.modal` 클래스를 사용한다.
기존 모달을 수정할 때도 예외 없이 이 구조를 기준으로 정리한다. 필드 추가만 하고 예전 레이아웃을 유지하는 식의 부분 수정은 허용하지 않는다.

```html
<dialog id="modal-xxx" class="modal modal-sm">
  <h2>제목</h2>
  <p class="modal-desc">설명문 (선택)</p>
  <div class="form-grid">
    <label>필드명 <input ...></label>
    <label class="full-width">전체폭 필드 <input ...></label>
  </div>
  <p class="modal-hint">보조 텍스트 (선택)</p>
  <div class="modal-actions">
    <button class="btn btn-secondary">취소</button>
    <button class="btn btn-primary">등록</button>
  </div>
</dialog>
```

### 사이즈 체계

| 클래스 | max-width | 용도 |
| --- | --- | --- |
| `.modal-xs` | 320px | 마이크로 다이얼로그 (인라인 업체 등록 등) |
| `.modal-sm` | 380px | 단순 폼 (1~4 필드) |
| `.modal` (기본) | 520px | 중간 폼 (5~8 필드) |
| `.modal-md` | 480px | 그룹형 폼 (fieldset 포함) |
| `.modal-lg` | 720px | 넓은 폼, 프리뷰 포함, Import 등 |
| `.modal-xl` | 960px | 월별 테이블 등 넓은 데이터 표시 |

- **일회성 커스텀 사이즈 금지** — 반드시 위 체계 사용.
- 기존 모달이 임의 폭, 임의 패딩, 인라인 margin에 의존하고 있으면 해당 모달을 수정하는 변경에서 함께 정리한다.

### 필드 그룹화

5개 이상 필드가 있는 모달은 `<fieldset class="modal-group">`으로 논리적 그룹으로 분리한다.

```html
<fieldset class="modal-group">
  <legend class="modal-group-title">그룹 제목</legend>
  <div class="form-grid">
    <label>...</label>
  </div>
</fieldset>
```

### 체크박스 인라인 배치

`.form-grid`나 `.info-edit-field` 안에서 체크박스+텍스트를 가로 배치할 때 `chk-inline` 클래스를 사용한다.

```html
<label class="chk-inline full-width">
  <input type="checkbox" id="some-flag" checked>
  체크박스 라벨 텍스트
</label>
```

- `base.css`에 정의: `flex-direction: row`, `align-items: center`, `gap: 8px`
- 체크박스 크기 15px로 고정 (`min-width: unset`으로 상위 input 스타일 오버라이드)

### Pill Tab (빠른 선택 버튼)

연도/기간 등 빠른 선택 버튼에 `pill-tab` 클래스를 사용한다. `components.css`에 정의.

```html
<div class="pill-tabs">
  <button class="pill-tab active" data-value="2026">2026년</button>
  <button class="pill-tab" data-value="2027">2027년</button>
</div>
```

- 상태: `.active` (선택됨), `.selected` (다중선택), hover 효과 포함
- 탭이 많아 overflow 시 `pill-tabs-scroll` + `pill-tab-nav`(◀▶) 사용
- 대시보드 연도 선택, 사업상세 Period 탭에서 공통 사용

### 텍스트 클래스

| 클래스 | 용도 | 위치 |
| --- | --- | --- |
| `.modal-desc` | 모달 상단 설명문 | `<h2>` 아래 |
| `.modal-hint` | 필드 하단 보조 텍스트 | `.form-grid` 아래 |

- ~~`.import-guide`~~, ~~`.inline-help-text`~~, ~~`.form-hint`~~ 사용 금지 → 위 클래스로 통일.
- Import 모달 내 각 단계별 가이드는 `.import-guide` 유지 (import-section 전용).

### 버튼 규칙

| 모달 유형 | Primary 버튼 라벨 |
| --- | --- |
| 새 엔티티 생성 | **등록** |
| 기존 데이터 수정 | **저장** |
| 설정/일괄 적용 | **적용** |
| Import | **가져오기** 또는 섹션별 **Import** |
| 닫기 전용 | **닫기** (Secondary) |

- 버튼 순서: `[취소(Secondary)] [확인(Primary)]` — 항상 오른쪽 정렬(`modal-actions`).
- 전체폭 필드: `class="full-width"` 사용 (`style="grid-column: 1 / -1"` 인라인 금지).
- 모달 내부 보조 액션(예: 카탈로그 열기, 인라인 추가, 검색 보조 버튼)도 `modal-actions` 또는 별도 공용 액션 클래스에 맞춘다. 인라인 `margin-top`, 임시 flex 스타일을 추가하지 않는다.

### 버튼 사이즈 클래스

| 클래스 | 크기 | 용도 |
| --- | --- | --- |
| `.btn` (기본) | 14px, 9px 18px | 모달 액션, 페이지 헤더 |
| `.btn-sm` | 12px, 4px 10px | 섹션 헤더, 패널 내부 |
| `.btn-xs` | 12px, 4px 10px | Import 섹션 내 템플릿 다운로드 등 |
| `.btn-compact` | 12px, 4px 10px | 그리드 상단 액션 바 |

- 버튼 사이즈는 `components.css`에 정의. 페이지별 CSS에 중복 정의 금지.

---

## 모듈별 프론트엔드 네이밍 규칙

## 기존 화면 수정 시 일관성 규칙

- 기존 화면을 수정할 때는 그 변경 범위 안의 모달, 패널, 액션바, 동적 드롭다운, 인라인 편집 UI를 현재 공용 패턴에 맞춘다.
- 기존 화면을 수정할 때는 touched 영역의 상태 저장/복원도 함께 본다. 이미 사용자가 조정 가능한 패널/트리/상세 구조가 있다면, 새 UI만 저장되고 기존 UI는 저장되지 않는 식의 불균형 상태로 남기지 않는다.
- 새 기능을 추가하면서 touched 영역에 남아 있는 인라인 `style=""`, JS `style.*`, JS `cssText`를 그대로 두지 않는다. 단, 드롭다운/팝오버의 동적 좌표 계산처럼 문서상 허용된 예외는 제외한다.
- 공용 컴포넌트로 표현 가능한 구조를 페이지별 ad-hoc 마크업/스타일로 다시 만들지 않는다. 먼저 `components.css`, `base.css`, 기존 페이지 CSS를 확인하고, 반복되면 공용 클래스로 승격한다.
- 특히 모달 작업에서는 다음 항목을 같이 본다: 사이즈 클래스, `.form-grid`, `.modal-desc`, `.modal-hint`, `.modal-actions`, `.full-width`, 버튼 순서, 필드 그룹화.
- 리뷰 기준은 “기능이 동작하는가”만이 아니라 “같은 화면 안에서 스타일 언어가 하나로 읽히는가”이다.

### 템플릿

- 공통 템플릿 (`app/templates/`): `base.html`, `login.html` 등 — 접두사 없음
- 모듈별 템플릿 (`app/modules/{module}/templates/`): 모듈명 접두사 사용
  - 회계: `acct_contracts.html`, `acct_dashboard.html`
  - 인프라: `infra_assets.html`, `infra_projects.html`
- Jinja2 `ChoiceLoader`로 공통 -> 활성 모듈 순서로 경로 추가

### JavaScript

- 공통 JS (`app/static/js/`): `utils.js` — 접두사 없음
- 모듈별 JS: 모듈 접두사 사용
  - 회계: `acct_contract_detail.js`, `acct_dashboard.js`
  - 인프라: `infra_assets.js`, `infra_projects.js`
- 기존 회계모듈 JS (접두사 없는 `contract_detail.js` 등)는 레거시로 유지할 수 있다.
- 단, **새 JS 파일을 만들거나 기존 파일을 분리/이동할 때는 반드시 접두사 규칙을 적용한다.**
- 단순 버그 수정이나 소규모 기능 추가만으로 레거시 파일명을 즉시 rename할 필요는 없다. rename은 별도 정리 작업으로 수행한다.

### CSS

- 공통 CSS (`app/static/css/`): `base.css`, `components.css` — 접두사 없음
- 모듈별 CSS: 모듈 접두사 사용
  - 회계: `acct_contract_detail.css`, `acct_dashboard.css`
  - 인프라: `infra_assets.css`, `infra_projects.css`
- 기존 회계모듈 CSS (접두사 없는 `contract_detail.css` 등)는 레거시로 유지할 수 있다.
- 단, **새 CSS 파일을 만들거나 기존 파일을 분리/이동할 때는 반드시 접두사 규칙을 적용한다.**
- 단순 스타일 수정만으로 레거시 파일명을 즉시 rename할 필요는 없다. rename은 별도 정리 작업으로 수행한다.

### 동적 네비게이션

- `base.html`에서 `enabled_modules` Jinja2 global 변수를 사용하여 네비게이션 동적 렌더링
- accounting 활성 시: 내 사업, 사업 관리, 대시보드, 보고서
- infra 활성 시: 프로젝트, 자산, 업체, 이력
- 공통 메뉴 (항상, 구분선 아래): 거래처 관리, 카탈로그, 로그

### ag-Grid 상호작용 표준

모든 ag-Grid는 `buildStandardGridBehavior()` 헬퍼(utils.js)를 사용하여 일관된 클릭 동작을 적용한다.

| 그리드 유형 | type 값 | 싱글클릭 | 더블클릭 |
|------------|---------|----------|----------|
| 마스터-디테일 | `detail-panel` | 상세 패널 열기 | 편집 (인라인 또는 모달) |
| 네비게이션 | `navigate` | 행 하이라이트 | 상세 페이지 이동 |
| 인라인 편집 | `inline-edit` | 행 선택 | 셀 인라인 편집 |
| 모달 편집 | `modal-edit` | 행 선택 | 편집 모달 열기 |
| 읽기 전용 | `readonly` | 행 선택 | 없음 |

- `singleClickEdit: true`는 사용하지 않는다. 모든 인라인 편집은 더블클릭으로 시작.
- 새 그리드를 추가할 때 반드시 `buildStandardGridBehavior()`를 사용한다.
- `onRowClicked`, `onRowDoubleClicked`를 직접 설정하지 않고 헬퍼를 통해 설정한다.
- "테이블 편집" 같은 모드 토글 버튼은 만들지 않는다 — editable 컬럼은 항상 더블클릭으로 편집 가능.

### 하이브리드 인라인 편집

그리드 셀 편집과 모달 편집을 병행한다. 기준:

- **인라인 (더블클릭):** 텍스트 1줄, 드롭다운, 날짜, 숫자 등 단순 필드
- **모달 (버튼 또는 액션):** textarea, 참조 검색, 다중 필드 동시 입력, 신규 생성

인라인 편집 구현 패턴:

1. columnDefs에 `editable: true` + 필요 시 `cellEditor: "agSelectCellEditor"`
2. `buildStandardGridBehavior()`에 `onCellValueChanged` 핸들러 전달
3. 핸들러에서 `PATCH /api/v1/{resource}/{id}` 호출, 실패 시 `oldValue` 복원 + `refreshCells`
4. `singleClickEdit: true`는 사용 금지 — 더블클릭 편집만 허용

### 커스텀 셀 에디터 (ag-Grid v32)

`getValue()`가 객체를 반환하는 커스텀 에디터 작성 시 필수 규칙:

- **`cellDataType: false` 필수** — ag-Grid v32는 셀 데이터 타입을 자동 추론한다. 커스텀 에디터가 객체를 반환하면 "Data type does not match" 경고와 함께 값이 무시된다.
- **`valueGetter`와 커스텀 에디터를 함께 쓰지 않는다** — `valueGetter`가 있으면 ag-Grid가 편집 완료 시 `getValue()` 대신 `valueGetter` 반환값을 `newValue`로 사용한다. 표시 변환은 `valueFormatter`로 처리한다.
- **`refreshCells` 재진입 방지** — `onCellValueChanged` 핸들러에서 `refreshCells({ force: true })`를 호출하면 셀 값이 재평가되면서 핸들러가 다시 트리거될 수 있다. `_cellChangeInProgress` 같은 재진입 가드를 사용한다.

커스텀 에디터 컬럼 정의 예시:

```javascript
{
  field: "some_id",
  headerName: "표시명",
  cellEditor: CustomCellEditor,
  cellDataType: false,                    // 필수: 타입 자동 추론 비활성화
  valueFormatter: (p) => getLabel(p.value), // valueGetter 대신 사용
  editable: () => isGridFieldEditable("some_id"),
}
```

기존 커스텀 에디터: `CatalogCellEditor` (모델명), `RoleCellEditor` (현재 역할)
