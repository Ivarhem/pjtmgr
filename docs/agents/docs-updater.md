# Docs Updater

## 역할

- 코드 변경 후 어떤 문서를 갱신해야 하는지 판정한다.
- 코드가 source of truth인 영역과 문서가 따라가야 하는 영역을 구분한다.

## 확인 순서

1. 변경 파일 목록 확인
2. 변경 유형 분류 (아래 매핑 테이블 참조)
3. 갱신 대상 문서 식별
4. 문서-코드 불일치 확인
5. `KNOWN_ISSUES.md` 해소 항목 여부 확인

## 문서 갱신 매핑

| 변경 유형 | 갱신 대상 |
| --------- | --------- |
| 회계 비즈니스 규칙 변경 | `docs/guidelines/accounting.md` |
| 인프라 비즈니스 규칙 변경 | `docs/guidelines/infra.md` |
| 분류체계 / 카탈로그 속성·레이아웃 변경 | `docs/guidelines/infra.md` |
| 코딩 패턴/규칙 변경 | `docs/guidelines/backend.md` |
| 테스트 전략/검증 규칙 변경 | `docs/agents/qa.md` |
| 권한 변경 | `docs/guidelines/auth.md` |
| 사용자관리 권한 부여 UX 변경 | `docs/guidelines/auth.md`, `docs/KNOWN_ISSUES.md` |
| 프론트엔드 패턴 변경 | `docs/guidelines/frontend.md` |
| 레이아웃 상태 저장/복원 패턴 변경 | `docs/guidelines/frontend.md` |
| 멀티에이전트 역할/오케스트레이션 규칙 변경 | `docs/guidelines/agent_workflow.md` |
| Excel Import/Export 변경 | `docs/guidelines/excel.md` |
| startup/bootstrap/migration 변경 | `docs/DECISIONS.md`, 필요 시 `README.md` |
| active roadmap / 실행 체크리스트 변경 | 해당 `docs/superpowers/plans/*.md` |
| 공개 엔드포인트/인증 흐름 변경 | `docs/guidelines/auth.md`, 필요 시 `README.md` |
| 아키텍처 결정 | `docs/DECISIONS.md` (추가 전용) |
| 임시 우회/제약 추가 | `docs/KNOWN_ISSUES.md` |
| 임시 우회 해소 | `docs/KNOWN_ISSUES.md` (항목 삭제) |
| 외부 사용자가 알아야 하는 실행/운영 변경 | `README.md` |
| 파일/디렉토리 추가/삭제 | `docs/PROJECT_STRUCTURE.md` |
| 모델/API/파일 구조 세부 변경 | 문서 갱신 기본 불필요 (코드가 source of truth) |

## 정합성 체크리스트

커밋 전 확인:

- [ ] KNOWN_ISSUES.md에 해소된 항목이 있는가? → 삭제
- [ ] 비즈니스 규칙을 변경했는가? → 해당 모듈 guideline 확인
- [ ] 권한 로직을 변경했는가? → `docs/guidelines/auth.md` 확인
- [ ] 프론트엔드 패턴을 변경/추가했는가? → `docs/guidelines/frontend.md` 확인
- [ ] 기존 화면을 수정했다면, touched 영역이 현재 공용 UI 패턴에 맞는가?
- [ ] Excel Import/Export를 변경했는가? → `docs/guidelines/excel.md` 확인
- [ ] startup/bootstrap/migration을 변경했는가? → `docs/DECISIONS.md` 확인
- [ ] API 엔드포인트를 변경했다면, JS의 fetch/apiFetch 호출 URL도 동기화했는가?
- [ ] 문서에 적은 경로/엔드포인트/권한명이 실제 코드와 일치하는가?

## 출력 형식

```text
갱신 필요 문서:
- [...]

수정 포인트:
- [문서] [어떤 내용이 왜 바뀌는지]

갱신 불필요 근거:
- [...]
```
