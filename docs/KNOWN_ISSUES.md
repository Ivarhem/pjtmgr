# Known Issues

> 인지된 문제와 임시 제약을 기록한다.
> 수정 완료 시 해당 항목을 제거한다.

---


## 운영 배포/검증 안전망

- 운영 compose는 `app`, `worker`, `catalog-research-service`, `db` 역할을 기준으로 유지한다.
- 배포 전 `docker compose -f docker-compose.prod.yml config --quiet`로 환경변수/문법을 확인한다.
- 배포 후 앱 컨테이너 안에서 `python /app/scripts/smoke_check.py`를 실행해 app import, Alembic head/current, health endpoint를 확인한다.
- 프론트엔드 성능/정적 리소스 변경 후 `scripts/check_frontend_assets.py`와 브라우저 console/network/grid 렌더링 확인을 함께 수행한다.
- `pjtmgr` 기준 health endpoint는 `http://127.0.0.1:9000/api/v1/health`이다. 포트 8000은 다른 앱일 수 있으므로 검증에 사용하지 않는다.
- Minified vendor 파일은 line 단위 삭제/수정하지 않는다. 특히 single-line minified JS는 sourcemap 줄 제거로 전체 파일이 삭제될 수 있다.

## 모듈화 마이그레이션 — 코드 구조 완료, 런타임 E2E 검증 미완

- 코드 구조 마이그레이션 완료: `app/core/`, `app/modules/{common,accounting,infra}/` 구조로 전환됨
- 인프라모듈은 골격과 일부 핵심 화면이 동작하지만, 전체 구현은 아직 진행 중
- 최신 인프라 진행 상태는 `docs/superpowers/plans/2026-03-24-infra-module-roadmap.md` 기준
- 업체 중심 구조 전환 완료 (Migration 0005): Asset/IpSubnet/PortMap/PolicyAssignment → partner_id FK, topbar 2단 셀렉터
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

- RBAC 기본 구현 완료 (Role 모델 + permissions JSONB + 기본 역할 4종 + require_module_access)
- 풀 RBAC 확장(resource x action 조합)은 향후 구현 예정 (permissions.resources 플레이스홀더 존재)
- 사용자관리 1차 UI는 체크박스 권한 조합을 내부적으로 커스텀 Role로 매핑하는 방식이다.
  - 현재는 사용자 화면에서 빠른 권한 부여가 목적이며, 역할 자체를 직접 편집/비교/정리하는 전용 역할 관리 화면은 아직 없다.

## 참여업체-자산 연결 (TODO)

- 현재 참여업체(`/contacts`) 페이지는 프로젝트-업체 연결(PeriodPartner)과 담당자 매핑만 지원
- "이 업체가 어떤 자산을 담당하는지" 직접 연결 기능 미구현
- 설계 방향: `PeriodPartnerAsset(period_partner_id, asset_id, role)` 테이블 신설하여 업체-자산 명시적 연결
- 별도 스펙 작성 후 구현 예정

## 정책 기능 (TODO)

- 정책 정의/적용 UI를 메뉴에서 제거함 (DB 테이블, 모델, API 라우터는 유지)
- 향후 재설계 후 구현 예정 — 현재 PolicyDefinition/PolicyAssignment 모델과 API는 동작하지만 UI 접근 경로 없음

## 발행일 휴일 조정

- 공휴일 달력 미적용 (`invoice_holiday_adjust` 필드만 존재)
