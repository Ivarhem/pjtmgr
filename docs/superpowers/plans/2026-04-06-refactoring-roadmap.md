# 리팩토링 실행 로드맵

> 2026-04-06 기준 코드/문서/UI-UX 점검 결과를 바탕으로, 기능 추가보다 구조 안정화와 회귀 안전성 확보를 우선하는 실행 계획.
> 멀티에이전트로 진행할 때는 벤더 전용 sub-skill 이름 대신 `docs/guidelines/agent_workflow.md`와 필요한 `docs/agents/*.md`를 기준으로 역할을 나눈다.

## 이 문서의 역할

- 이 문서는 리팩토링 전용 **active roadmap**이다.
- 개별 증상 리스트를 그대로 따라가기보다, 서로 연결된 구조 문제를 트랙 단위로 묶어 실행 순서를 고정한다.
- 인프라 메뉴/UI 개편의 상세안은 `docs/superpowers/plans/2026-04-06-infra-navigation-ux-review.md`를 참조한다.

## 리팩토링 목표

1. 보안과 데이터 정합성을 먼저 안정화한다.
2. 모듈 경계 위반과 트랜잭션 경계를 정리한다.
3. 인프라모듈의 탐색 구조와 화면 컨텍스트를 제품 목적에 맞게 재배치한다.
4. 카탈로그/인프라 핵심 서비스에 회귀 안전망을 추가한다.
5. 문서와 결정 기록을 현재 코드와 다시 맞춘다.

## 기본 원칙

- 새 기능 추가보다 기존 계약 안정화를 우선한다.
- 리팩토링은 작은 PR/커밋 단위로 나눈다.
- 공용 유틸/공용 패턴을 먼저 만들고, 화면별 중복 제거는 그 다음에 진행한다.
- README보다 `CLAUDE.md`, `docs/guidelines/*.md`, active roadmap이 내부 실행 기준이다.
- UI polish보다 메뉴 구조, 컨텍스트 전달, 회귀 안전성 확보를 먼저 본다.

## Track 1. 보안 / 공통 프론트엔드 기반 정리

### 목적

- XSS 가능성을 줄이고, 화면 렌더링 패턴을 공용 기준으로 통일한다.

### 작업 범위

- `innerHTML` 기반 렌더링 전수 점검
  - 1차 대상: `infra_asset_roles.js`, `infra_assets.js`, `utils.js`
- `escapeHtml()` 중복 제거
  - 공용 DOM/escape 유틸로 통합
- 사용자 입력/서버 응답 렌더링 규칙 정리
  - 기본은 `textContent`, `createElement`
  - 제한적으로만 escape 후 HTML 허용
- `window.confirm()` 대체 공용 confirm dialog 도입
- `.hidden`, 직접 표시/숨김 토글을 `is-hidden`/공용 헬퍼로 통일

### 완료 기준

- 인프라 핵심 화면에서 raw 사용자값이 `innerHTML`로 삽입되지 않는다.
- 숨김/표시/확인 패턴이 공용 규칙으로 정리된다.
- 보안 수정이 공통 유틸에 모여 후속 화면에도 재사용 가능하다.

## Track 2. 모듈 경계 / 데이터 구조 정리

### 목적

- `core <- common <- {accounting, infra}` 규칙을 다시 강제한다.

### 작업 범위

- `common -> accounting` 직접 import 제거
  - common 서비스의 회계 집계 책임을 accounting 확장 서비스로 이동
- `ContractPeriod`의 infra 전용 FK 재설계
  - common 모델에서 infra 상세 테이블 의존 제거
  - 필요 시 infra 확장 설정 테이블로 분리
- bulk 작업의 트랜잭션 경계 재정리
  - 행 단위 commit 제거
  - batch 단위 rollback 가능 구조로 변경
- 마이그레이션 위생 정리
  - `assert` 제거
  - 누락 인덱스 추가
  - revision 네이밍 규칙 정상화

### 완료 기준

- 모듈 경계 위반 import가 제거된다.
- common 모델이 infra 테이블 세부사항을 직접 참조하지 않는다.
- 대량 작업이 부분 성공 상태를 덜 남긴다.

## Track 3. 인프라 IA / UI-UX 재구성

### 목적

- 인프라 사용자의 실제 시작점을 메뉴 구조와 화면 헤더에 반영한다.

### 작업 범위

- 메뉴 IA 재편
  - `프로젝트 / 자산 / 네트워크 / 배치 / 업체 / 이력`
  - 공통 관리 메뉴는 별도 관리 구역으로 분리
- 접근 불가 페이지 정리
  - `/inventory/assets`, `/infra-import`, `/infra-dashboard`는
    - 메뉴에 올릴지
    - 기존 화면과 통합할지
    - 제거/리다이렉트할지
    중 하나로 결정
- 본문 컨텍스트 노출 강화
  - `/contacts`, `/assets`, `/periods` 우선
- 용어 정리
  - `업체` vs `거래처`
  - `프로젝트 / 기간 / 사업`
- 인프라 화면의 작업 밀도 재정렬
  - 현재 컨텍스트
  - 핵심 액션
  - 필터
  - 결과 그리드

### 상세 참조

- `docs/superpowers/plans/2026-04-06-infra-navigation-ux-review.md`

### 완료 기준

- 핵심 인프라 작업 화면에 전역 메뉴에서 직접 진입할 수 있다.
- 본문 상단에서 현재 고객사/프로젝트/범위를 즉시 파악할 수 있다.
- 메뉴 명칭과 정보 위계 충돌이 줄어든다.

## Track 4. 테스트 보강

### 목적

- 리팩토링 이후 회귀를 자동으로 잡을 수 있게 한다.

### 작업 범위

- 카탈로그 핵심 서비스 테스트 추가
  - `product_catalog_service`
  - `product_catalog_importer`
  - `catalog_attribute_service`
  - `catalog_similarity_service`
  - `catalog_merge_service`
- 테스트 층 분리
  - 서비스 단위 테스트
  - DB 통합 테스트
  - importer 회귀 테스트
- 인프라 핵심 브라우저 체크리스트 정리
  - 자산
  - 역할 기준
  - IP 인벤토리
  - 포트맵
  - 업체 연결

### 완료 기준

- 카탈로그/인프라 핵심 경로 변경 시 자동 회귀 확인이 가능하다.
- 리팩토링으로 깨질 가능성이 높은 경로가 테스트로 묶인다.

## Track 5. 문서 / 결정 기록 정리

### 목적

- 리팩토링 결과가 문서 기준과 다시 일치하도록 만든다.

### 작업 범위

- `docs/guidelines/frontend.md`
  - 실제 메뉴명, 숨김 규칙, dialog 패턴 반영
- `docs/guidelines/infra.md`
  - 인프라 탐색 구조, 컨텍스트 노출 원칙 반영
- `docs/guidelines/auth.md`
  - 시스템 역할 표 최신화
- `docs/DECISIONS.md`
  - 분류체계 / 카탈로그 속성 모델 / 모듈 경계 관련 결정 기록
- `docs/PROJECT_STRUCTURE.md`
  - 파일/플랜/마이그레이션 추적 최신화

### 완료 기준

- 코드와 문서가 같은 방향을 가리킨다.
- 이후 동일한 구조 부채가 문서 누락 때문에 반복되지 않는다.

## 실행 순서

### Phase 1. 보안 / 공용 UI 기반

- XSS 가능 코드 제거
- escape/confirm/visibility 공용화

### Phase 2. 모듈 경계 / 트랜잭션

- common/accounting 경계 분리
- common/infra 데이터 결합 해소
- bulk 트랜잭션 정리

### Phase 3. 인프라 IA / UX

- 메뉴 구조 재편
- 접근 불가 페이지 처리
- 본문 컨텍스트 카드 추가
- 협력업체 화면은 우선 "담당 자산 -> 자산 상세 점프"만 구현
- 업체 기준 자산 자동 필터링/제품군 그룹핑은 후속 UX 개선 항목으로 분리

### Phase 4. 테스트

- 카탈로그/인프라 서비스 회귀 추가
- 핵심 브라우저 체크리스트 정리

### Phase 5. 문서 / 결정 기록

- 가이드와 구조 문서 동기화
- 리팩토링 결정 기록 남기기

## 권장 분할 단위

### PR 1

- XSS / 공용 escape / confirm / visibility 정리

### PR 2

- 모듈 경계 위반 해소
- common/infra 결합 해소
- 트랜잭션 경계 정리

### PR 3

- 인프라 메뉴 / 진입점 / 컨텍스트 UX 개편

### PR 4

- 카탈로그 서비스 테스트팩

### PR 5

- 문서 / 결정 / 구조 동기화

## 세션 시작 체크리스트

1. 이 문서와 `2026-03-24-infra-module-roadmap.md` 중 현재 작업이 어느 트랙에 속하는지 먼저 확인
2. UI 작업이면 `2026-04-06-infra-navigation-ux-review.md`를 같이 확인
3. touched 범위가 문서 갱신 매핑에 걸리면 `CLAUDE.md` 표에 따라 동시 갱신
4. 리팩토링 중 새 기능 요구가 나오면 같은 PR에 섞지 않고 별도 backlog로 분리
