# AI Dev Template

AI 보조 개발을 위한 범용 프로젝트 템플릿.

---

## 구조

```text
.ai-dev-template/

.ai/                              ← 워크플로우 프롬프트 (번호순 실행)
  01_spec_draft.md                   명세 초안 작성
  02_critical_questions.md           설계 결정 질문 추출
  03_final_spec.md                   최종 명세 확정 + PROJECT_CONTEXT, DECISIONS 생성
  04_architecture.md                 아키텍처 설계
  05_project_rules.md                프로젝트 전용 개발 지침 생성
  06_review.md                       프로젝트 점검
  07_guideline_update.md             지침 개선

.ai_rules/                        ← 범용 규칙 (모든 프로젝트에 적용)
  AI_DEV_GLOBAL_RULES.md             과설계 방지, 구조 안정성, 코드-문서 동기화
  AI_ARCHITECTURE_GUARD.md           책임 분리, 순환 의존 금지, 단일 책임
  AI_EXTENSIBILITY_BALANCE.md        확장성 균형, 추상화 기준, 변경 전 체크리스트

docs/                             ← 프로젝트 문서 (워크플로우 산출물)
  PROJECT_CONTEXT.md                 프로젝트 핵심 맥락 요약
  SPEC.md                           기능 명세
  ARCHITECTURE.md                   아키텍처 설계
  DECISIONS.md                      설계 결정 기록
  TODO.md                           작업 목록
  KNOWN_ISSUES.md                   알려진 문제
```

---

## 워크플로우

### 설계 단계 (01 → 05)

```text
01 Spec Draft ──→ 02 Critical Questions ──→ 03 Final Spec
                                                  │
                                                  ├─→ docs/SPEC.md
                                                  ├─→ docs/PROJECT_CONTEXT.md
                                                  └─→ docs/DECISIONS.md
                                                  │
                                            04 Architecture
                                                  │
                                                  └─→ docs/ARCHITECTURE.md
                                                  │
                                            05 Project Rules
                                                  │
                                                  └─→ 프로젝트 전용 개발 지침
                                                       (.ai_rules/ 범용 규칙을 상속+구체화)
```

### 구현 단계

코드 작성은 05단계 이후 시작한다.

### 피드백 루프 (06 ↔ 07)

```text
06 Review ──→ 07 Guideline Update ──→ 지침 개선
     ↑                                      │
     └──────────────────────────────────────┘
```

구현 중 또는 마일스톤 완료 시 반복 실행한다.

---

## 규칙 체계

```text
.ai_rules/ (범용)          ← 프로젝트 무관, 항상 유효
       │
       │  상속 + 구체화
       ↓
프로젝트 전용 지침          ← 도메인 용어, 명명 규칙, 코드 패턴 등
(05단계에서 생성)              프로젝트 맥락에 맞춘 구체적 적용 방법
```

- 범용 규칙과 전용 지침이 충돌하면 범용 규칙이 우선한다
- 전용 지침은 범용 규칙을 **대체**하지 않고 **구체화**한다

---

## 사용법

1. 이 템플릿을 프로젝트에 복사한다
2. `.ai/01_spec_draft.md`부터 순서대로 실행한다
3. 각 단계의 산출물은 `docs/`에 저장된다
4. `05_project_rules.md`로 프로젝트 전용 지침을 생성한다
5. 구현 후 `06_review.md` → `07_guideline_update.md`로 지침을 개선한다
