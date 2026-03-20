# Known Issues

> 인지된 문제와 임시 제약을 기록한다.
> 수정 완료 시 해당 항목을 제거한다.

---

## 모듈화 마이그레이션 — 코드 구조 완료, 런타임 E2E 검증 미완

- 코드 구조 마이그레이션 완료: `app/core/`, `app/modules/{common,accounting,infra}/` 구조로 전환됨
- 인프라모듈 전체 구현 완료 (프로젝트/자산/IP/포트맵/정책/대시보드/Import/Export/Pin/업체연결/감사로그)
- 런타임 통합 테스트 (실제 서버 기동, 브라우저 E2E) 미수행 — 마이그레이션 예외 조항(CLAUDE.md §8)은 런타임 검증 완료 시 삭제 예정
- Standalone 배포용 데이터 Export/Import CLI 미구현 (`app/cli/export_standalone.py`, `app/cli/import_standalone.py` placeholder만 존재)

## 동시 편집

- 같은 사업을 두 사용자가 동시 편집하면 마지막 저장이 이전 저장을 덮어씀
- Optimistic Locking 미구현 (향후 version 컬럼 기반 충돌 방지 예정)

## Excel Import

- 대량 데이터(1000행 이상) Import 시 성능 미검증

## 감사 로그

- 인프라모듈: `audit.log()` 연동 완료 (프로젝트/자산/IP대역/포트맵/정책 CRUD)
- 인프라모듈: 변경이력 탭에서 AG Grid 조회 가능 (`/api/v1/infra-dashboard/audit-log`)
- 회계모듈: `audit.log()` 호출 미연동 — CRUD 동작에 감사 기록이 남지 않음
- `/audit-logs` 공통 화면은 placeholder — 목록/필터 UI 미구현

## 권한

- admin/user 2단계만 구현 (RBAC 전환 예정 — 마이그레이션 단계 5)

## 발행일 휴일 조정

- 공휴일 달력 미적용 (`invoice_holiday_adjust` 필드만 존재)
