# Known Issues

> 파일럿 테스트 피드백 및 인지된 문제를 기록한다.
> 수정 완료 시 해당 항목을 제거한다.

---

## 동시 편집

- 같은 사업을 두 사용자가 동시 편집하면 마지막 저장이 이전 저장을 덮어씀
- Optimistic Locking 미구현 (향후 version 컬럼 기반 충돌 방지 예정)

## Excel Import

- 대량 데이터(1000행 이상) Import 시 성능 미검증

## 감사 로그

- 테이블/유틸(`app/services/audit.py`) 준비 완료, 서비스 연동 미완료
- `/audit-logs` 화면은 placeholder이며 실제 로그 목록/API 미구현

## 권한

- admin/user 2단계만 구현 (manager/viewer 미구현)

## 발행일 휴일 조정

- 공휴일 달력 미적용 (`invoice_holiday_adjust` 필드만 존재)

## DB

- SQLite 단일 파일 — 동시 쓰기 제한
