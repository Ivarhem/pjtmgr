# 프로젝트 개발 지침

> 사업 관리 통합 플랫폼 (공통 + 회계 + 인프라 모듈).
> 이 파일은 **라우터**다 — 핵심 규칙과 "어디를 읽어야 하는지"만 정의한다.

---

## 절대 규칙

- **코드 일관성 > 기능 추가 속도.** 동일 문제 해결 시 기존 패턴을 우선 사용.
- **모듈 간 import:** `core ← common ← {accounting, infra}`. accounting ↔ infra 절대 금지.
- **서비스 레이어에 비즈니스 로직 집중.** 라우터는 얇게 유지.
- **API prefix:** `/api/v1/`
- **타입 힌트:** 모든 함수에 명시.
- **테스트 실행 필수:** 테스트를 실행하고 **출력 결과를 그대로 첨부**한다. 실행하지 않았으면 사유를 명시한다. "통과했다"는 서술만으로는 완료로 인정하지 않는다.

---

## 역할 라우팅

작업 내용에 따라 해당 문서를 **반드시 읽고** 따른다.

| 상황 | 읽을 문서 |
|---|---|
| 백엔드 (Python/FastAPI/SQLAlchemy) | `docs/guidelines/backend.md` |
| 프론트엔드 (JS/CSS/HTML) | `docs/guidelines/frontend.md` |
| 인증/권한/보안 | `docs/guidelines/auth.md` |
| 회계모듈 | `docs/guidelines/accounting.md` |
| 인프라모듈 | `docs/guidelines/infra.md` |
| Excel Import/Export | `docs/guidelines/excel.md` |
| 검증/테스트 | `docs/agents/qa.md` |
| 문서 갱신 판단 | `docs/agents/docs-updater.md` |
| 멀티에이전트 구성 | `docs/guidelines/agent_workflow.md` |

---

## 완료 조건

코드 변경이 "완료"되려면:

1. 코드 변경 완료
2. 테스트 실행 + **실행 출력 첨부** (미실행 시 사유 명시)
3. `docs/agents/docs-updater.md`의 문서 갱신 매핑에 따라 필수 문서 갱신
4. 해결된 `docs/KNOWN_ISSUES.md` 항목 삭제
5. 문서에 적은 경로/엔드포인트/권한이 코드와 일치

---

## 문서 계층

- 코드가 source of truth: 엔트리포인트, API 엔드포인트, 데이터 모델
- `docs/guidelines/*.md`: 작업별 상세 규칙
- `docs/agents/*.md`: 역할 카드와 handoff 규칙
- `docs/DECISIONS.md`: 아키텍처 결정 기록 (추가 전용)
- `docs/KNOWN_ISSUES.md`: 미해소 제약/우회
- `docs/PROJECT_CONTEXT.md`: 도메인 배경
- `docs/PROJECT_STRUCTURE.md`: 파일 구조
- `docs/superpowers/plans/*.md`: active roadmap (선언 시 source of truth)

---

## 마이그레이션 기간 예외

런타임 E2E 통합 테스트 미수행 상태. 검증 완료 후 이 섹션을 삭제한다.

- 마이그레이션 계획에 따른 의도적 코드-문서 불일치는 되돌리지 않는다.
- 미구현/부분구현 코드를 근거로 지침을 수정하지 않는다. 지침 간 모순은 보고하고 사용자 확인을 요청한다.
