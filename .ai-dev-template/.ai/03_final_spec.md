# 03. Final Spec — 최종 명세 확정

## 목표

사용자의 질문 답변을 반영하여 최종 프로젝트 명세를 확정한다.
이 문서가 이후 모든 설계·구현의 기준이 된다.

## 입력

- `docs/SPEC.md` 초안 (01단계 산출물)
- 사용자의 질문 답변 (02단계)

## 출력 — `docs/SPEC.md` 최종본 + `docs/PROJECT_CONTEXT.md` + `docs/DECISIONS.md` 초기화

### SPEC.md 최종본

01단계 구조에 다음을 추가/수정한다.

1. 질문 답변이 반영된 Scope 확정
2. 확정된 Domain Model
3. 구체화된 Functional Requirements
4. **Acceptance Criteria** — Must 범위 기능별 완료 조건과 사용자 관점의 검증 기준
5. **Contracts & Invariants** — 상태 전이, 중복 금지, canonical format, 원자성/롤백, 권한 경계 등 구현 전 합의해야 할 불변 조건
6. **Implementation Plan** — 작은 단계로 나눈 구현 순서

### PROJECT_CONTEXT.md 생성

프로젝트의 핵심 맥락을 요약한다. AI가 매번 맥락을 복구할 필요 없도록 한다.

```markdown
# Project Context

## 목적
[한두 문장으로 프로젝트 존재 이유]

## 사용자
[사용자 유형과 규모]

## 핵심 문제
[이 프로젝트가 해결하는 문제들]

## 핵심 데이터
[주요 엔티티 나열]

## 핵심 원칙
[설계 및 운영의 기본 원칙]

## MVP 범위
[첫 번째 릴리스에 포함되는 것]

## 향후 기능
[이후 추가 예정인 것]
```

### DECISIONS.md 초기화

질문 답변 과정에서 내린 설계 결정을 기록한다.

```markdown
# Architecture Decisions

## [결정 제목]

### 이유
[왜 이렇게 결정했는가]

### 영향
[이 결정이 코드/설계에 미치는 영향]
```

## 주의사항

- 구현 계획은 각 단계가 독립적으로 동작·검증 가능해야 한다
- 단계 간 의존성이 있으면 명시한다
- Acceptance Criteria는 "구현했다"가 아니라 "어떻게 완료를 판정할지"를 기준으로 적는다
- Contracts & Invariants에는 이후 구현/리뷰에서 깨지면 안 되는 규칙만 넣고, 단순 희망사항은 넣지 않는다
- PROJECT_CONTEXT는 간결하게 유지한다 (1페이지 이내)
- DECISIONS는 "왜"에 집중한다 ("무엇"은 SPEC에 있다)
