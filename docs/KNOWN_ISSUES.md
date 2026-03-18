# Known Issues

> 인지된 문제와 임시 제약을 기록한다.
> 수정 완료 시 해당 항목을 제거한다.

---

## 모듈화 마이그레이션 진행 중

- 문서(CLAUDE.md, README.md, docs/)가 목표 구조를 선행 반영하고 있으나 코드는 아직 구 구조(`app/models/`, `app/schemas/` 등)에 있음
- 마이그레이션 계획: `docs/superpowers/plans/2026-03-18-modular-migration-plan.md` 참조
- 코드-문서 경로 불일치는 마이그레이션 완료 시 해소 예정

## 동시 편집

- 같은 사업을 두 사용자가 동시 편집하면 마지막 저장이 이전 저장을 덮어씀
- Optimistic Locking 미구현 (향후 version 컬럼 기반 충돌 방지 예정)

## Excel Import

- 대량 데이터(1000행 이상) Import 시 성능 미검증

## 감사 로그

- 모델과 유틸 준비 완료
- 서비스 레이어에서 `audit.log()` 호출 미연동 — CRUD 동작에 감사 기록이 남지 않음
- 감사 로그 조회 API 엔드포인트(`/api/v1/audit-logs`) 미구현
- `/audit-logs` 화면은 placeholder — 목록/필터 UI 미구현

## 권한

- admin/user 2단계만 구현 (RBAC 전환 예정 — 마이그레이션 단계 5)

## 발행일 휴일 조정

- 공휴일 달력 미적용 (`invoice_holiday_adjust` 필드만 존재)
