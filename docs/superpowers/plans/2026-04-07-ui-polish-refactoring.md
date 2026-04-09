# UI 폴리싱 리팩토링 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프로젝트 목적(엑셀 대체 인벤토리 플랫폼)에 맞춰 메뉴 명칭, 페이지 타이틀, IP 유형 정합성, 컨텍스트 안내를 통일하고, 프로젝트 상세를 인라인 병합한다.

**Architecture:** 순수 프론트엔드 수정. HTML 템플릿과 JS만 변경. 백엔드 변경 없음.

**Tech Stack:** Jinja2 템플릿, Vanilla JS

---

## Task 1: 사이드바 서브설명 통일

사용자가 이해할 수 있는 언어로 서브설명을 교체한다.

**Files:**
- Modify: `app/templates/base.html:123-128, 142-147` (2개 블록 동일 수정)

- [ ] **Step 1:** 사이드바 서브설명 교체 (infra 양쪽 블록 모두)

| 메뉴 | AS-IS | TO-BE |
|------|-------|-------|
| 프로젝트 | 계약단위·단계·산출물 | 프로젝트 현황·일정·산출물 |
| 자산 | 자산 원장·역할 기준 | 장비 인벤토리·상세 관리 |
| 협력업체 | 담당자·담당 자산 | 업체 배정·담당자 연결 |

네트워크, 배치, 이력은 현행 유지.

- [ ] **Step 2:** 커밋 `refactor(ui): update sidebar sub-descriptions for clarity`

---

## Task 2: 포트맵 페이지 타이틀 통일

**Files:**
- Modify: `app/modules/infra/templates/infra_port_maps.html:2`

- [ ] **Step 1:** 타이틀 변경

```
AS-IS: {% block title %}케이블 배선도 - SI Project Inventory{% endblock %}
TO-BE: {% block title %}포트맵 - SI Project Inventory{% endblock %}
```

페이지 내부에 "케이블 배선도" 텍스트가 있으면 함께 변경 — 단, 포트맵 모달 내 "배선 등록/수정" 레이블은 유지 (실제 행위 설명이므로).

- [ ] **Step 2:** 커밋 `refactor(ui): rename portmap page title for consistency with sidebar`

---

## Task 3: IP 유형 HTML select 정합성

백엔드 스키마(service/mgmt/vip/secondary)와 HTML select option value를 일치시킨다.

**Files:**
- Modify: `app/modules/infra/templates/infra_ip_inventory.html:157-163`
- Verify: `app/modules/infra/templates/infra_assets.html:256-261` (이미 정확할 수 있음)

- [ ] **Step 1:** infra_ip_inventory.html IP 유형 select 교체

```html
AS-IS:
<option value="service">서비스</option>
<option value="management">관리</option>
<option value="backup">백업</option>
<option value="vip">VIP</option>
<option value="other">기타</option>

TO-BE:
<option value="service">서비스</option>
<option value="mgmt">관리</option>
<option value="vip">VIP</option>
<option value="secondary">보조</option>
```

- [ ] **Step 2:** infra_assets.html IP 유형 select 확인 — 이미 올바르면(service/mgmt/vip/secondary) 스킵

- [ ] **Step 3:** JS의 `IP_TYPE_LABELS` (utils.js)가 동일 값을 사용하는지 확인

- [ ] **Step 4:** 커밋 `fix(ui): align IP type select options with backend schema`

---

## Task 4: 컨텍스트 미선택 안내 통일

infra.md 원칙: "컨텍스트 미선택 상태는 단순 빈 메시지 대신 선택 CTA와 안내를 함께 제공한다."

**Files:**
- Modify: `app/modules/infra/templates/infra_ip_inventory.html`
- Modify: `app/modules/infra/templates/infra_port_maps.html`
- Modify: `app/static/js/infra_ip_inventory.js`
- Modify: `app/static/js/infra_port_maps.js`

- [ ] **Step 1:** 각 인프라 페이지의 빈 상태를 점검

현재 확인된 빈 상태 안내:
- 자산: ✅ "자산을 선택하면 오른쪽에서 상세 정보를 확인할 수 있습니다."
- 배치: ✅ "고객사를 선택하면 센터를 불러옵니다."
- 협력업체: ✅ "고객사를 선택하세요."

확인 필요:
- IP 인벤토리: 고객사 미선택 시 서브넷 목록이 비어만 있는지, 안내가 있는지
- 포트맵: 고객사 미선택 시 그리드가 비어만 있는지

- [ ] **Step 2:** IP 인벤토리 빈 상태 안내 추가

고객사 미선택 시 서브넷 목록 영역에:
```html
<div class="ctx-empty-guide">
  <p>고객사를 먼저 선택하세요.</p>
  <p class="text-secondary">상단 고객사 셀렉터에서 고객사를 선택하면 IP 대역과 할당 현황을 확인할 수 있습니다.</p>
</div>
```

JS에서 `getCtxPartnerId()`가 없을 때 이 안내를 표시.

- [ ] **Step 3:** 포트맵 빈 상태 안내 추가

동일 패턴으로 고객사 미선택 안내.

- [ ] **Step 4:** 커밋 `feat(ui): add context empty state guides to network pages`

---

## Task 5: 프로젝트 상세 인라인 병합

프로젝트 상세 페이지(`/projects/{id}`)를 제거하고, 프로젝트 목록 페이지(`/periods`) 내에서 선택 시 상세(기본정보 + 단계 + 산출물)를 인라인 표시한다.

> 메모리 참고: `project_menu_restructure.md` — 미완료 항목 5~7

**Files:**
- Modify: `app/modules/infra/templates/infra_projects.html`
- Modify: `app/static/js/infra_projects.js`
- Modify: `app/modules/infra/routers/pages.py` (리다이렉트)
- Remove or deprecate: `app/modules/infra/templates/infra_project_detail.html`
- Remove or deprecate: `app/static/js/infra_project_detail.js`

- [ ] **Step 1:** 현재 `infra_projects.js`와 `infra_project_detail.js` 구조 파악

`infra_project_detail.js`에서 단계(PeriodPhase)와 산출물(Deliverable) 관리 UI를 가져온다.

- [ ] **Step 2:** `infra_projects.html`에 상세 영역 추가

프로젝트 목록 아래 또는 우측에 상세 패널 추가. 자산 페이지의 좌우 분할(목록+상세) 패턴 참고.

프로젝트 선택 시 표시:
- 기본정보 카드 (기간코드, 고객사, 진행단계, 시작/종료일, 설명)
- 단계 목록 (PeriodPhase CRUD)
- 산출물 목록 (Deliverable CRUD)

- [ ] **Step 3:** `infra_project_detail.js`의 단계/산출물 관련 코드를 `infra_projects.js`에 병합

모달 HTML도 `infra_projects.html`에 포함.

- [ ] **Step 4:** `/projects/{id}` 라우트를 `/periods`로 리다이렉트 변경

```python
# pages.py
@router.get("/projects/{project_id}")
async def project_detail_redirect(project_id: int):
    return RedirectResponse(url="/periods", status_code=302)
```

- [ ] **Step 5:** 기존 `infra_project_detail.html`, `infra_project_detail.js` 정리

코드가 `infra_projects.*`에 병합 완료되면 삭제.

- [ ] **Step 6:** 수동 검증 — 프로젝트 선택 시 상세 인라인 표시, 단계/산출물 CRUD 동작

- [ ] **Step 7:** 커밋 `feat(ui): merge project detail into projects list page (inline panel)`

---

## Task 6: 문서 갱신

**Files:**
- Modify: `docs/KNOWN_ISSUES.md` (프로젝트 상세 병합 완료 시 관련 항목 정리)
- Modify: `docs/PROJECT_STRUCTURE.md` (파일 삭제/이동 반영)

- [ ] **Step 1:** KNOWN_ISSUES 확인 및 정리
- [ ] **Step 2:** PROJECT_STRUCTURE 갱신
- [ ] **Step 3:** 메모리 `project_menu_restructure.md` 업데이트
- [ ] **Step 4:** 커밋 `docs: update docs after UI polish refactoring`
