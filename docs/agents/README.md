# Agents Index

`docs/agents/`는 저장소 기준 멀티에이전트 역할 카드를 모아두는 디렉터리다.
공통 원칙과 병렬화 규칙은 `docs/guidelines/agent_workflow.md`를 먼저 읽고, 역할별 입력/출력 형식만 여기서 확인한다.

## 언제 어떤 카드를 쓰는가

- `planner.md`
  - 요청을 작업 단위로 나누고, 직접 처리와 위임 범위를 먼저 정해야 할 때
- `impact-analyzer.md`
  - 프론트엔드 전역 상태, 공용 컴포넌트, 모듈 경계, import 규칙처럼 숨은 영향이 있을 때
- `implementer.md`
  - write set이 명확하고 실제 코드나 문서를 수정할 때
- `reviewer.md`
  - 회귀 위험, 규약 위반, 누락 테스트를 코드 리뷰 관점으로 볼 때
- `tester.md`
  - 실제로 실행한 검증과 미실행 범위를 독립적으로 남길 때
- `docs-updater.md`
  - `CLAUDE.md` 문서 갱신 매핑에 따라 어떤 문서를 바꿔야 하는지 판정할 때

## 자주 쓰는 조합

- 작은 수정
  - 코디네이터 단독 또는 `implementer`만 사용
- 3파일 이상 프론트엔드 수정
  - `planner` → `impact-analyzer` → `implementer` + `reviewer`/`tester`
- 코드 수정 후 문서 정합성 점검
  - `implementer` + `docs-updater`
- 구조 변경 또는 회귀 위험 높은 작업
  - `planner` → `impact-analyzer` → `implementer` → `reviewer` + `tester`

## 생략해도 되는 경우

- `impact-analyzer`
  - 수정 범위가 작고 영향 파일이 명확할 때
- `reviewer`
  - 1~2파일, 단순 기계적 수정, 회귀 위험이 낮을 때
- `tester`
  - 실행 가능한 검증이 전혀 없을 때는 생략할 수 있지만, 미실행 사유는 남긴다

## 주의사항

- 이 디렉터리의 카드는 도구 문법이 아니라 운영 규약이다.
- 로컬 `.claude/`, `.cursor/` 설정은 개인 보조 수단일 뿐, 저장소 기준 규칙을 대체하지 않는다.
- 공통 규칙은 역할 카드에 복제하지 말고 `agent_workflow.md`를 기준으로 유지한다.
