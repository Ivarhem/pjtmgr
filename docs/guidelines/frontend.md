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
- 그리드는 AG Grid Community를 사용한다.
  - 행 단위 복사(Ctrl+C), 붙여넣기(Ctrl+V) 지원
  - 열 단위 선택 및 복사 지원
  - 셀 인라인 편집 허용 여부는 화면별로 명시
- 페이지 전환 없는 동적 업데이트는 HTMX를 사용한다.
- 테이블 중심 업무 화면으로 구성하며, 데이터 밀도를 우선한다.

### 화면 유형별 설계 원칙

- **사용자(영업) 화면** — 사업 중심, 입력 중심, 그리드 중심, 빠른 복사/붙여넣기 지원
- **경영진/관리자 화면** — 기간 중심, 숫자/요약 중심, 수정 기능 없음

---

## 모달 디자인 규칙

### 기본 구조

모든 모달은 HTML5 `<dialog>` + `.modal` 클래스를 사용한다.

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
| `.modal-xs` | 320px | 마이크로 다이얼로그 (인라인 거래처 등록 등) |
| `.modal-sm` | 380px | 단순 폼 (1~4 필드) |
| `.modal` (기본) | 520px | 중간 폼 (5~8 필드) |
| `.modal-md` | 480px | 그룹형 폼 (fieldset 포함) |
| `.modal-lg` | 720px | 넓은 폼, 프리뷰 포함, Import 등 |
| `.modal-xl` | 960px | 월별 테이블 등 넓은 데이터 표시 |

- **일회성 커스텀 사이즈 금지** — 반드시 위 체계 사용.

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

### 버튼 사이즈 클래스

| 클래스 | 크기 | 용도 |
| --- | --- | --- |
| `.btn` (기본) | 14px, 9px 18px | 모달 액션, 페이지 헤더 |
| `.btn-sm` | 12px, 4px 10px | 섹션 헤더, 패널 내부 |
| `.btn-xs` | 12px, 4px 10px | Import 섹션 내 템플릿 다운로드 등 |
| `.btn-compact` | 12px, 4px 10px | 그리드 상단 액션 바 |

- 버튼 사이즈는 `components.css`에 정의. 페이지별 CSS에 중복 정의 금지.
