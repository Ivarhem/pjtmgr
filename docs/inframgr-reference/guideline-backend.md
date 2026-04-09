# 백엔드 작업 지침

> Python/FastAPI/SQLAlchemy 백엔드 작업 시 참조.

---

## 파일 / 모듈 명명 규칙

| 레이어 | 패턴 | 예시 |
| ------ | ---- | --- |
| 모델/스키마/서비스 | 단수 snake_case | `project.py`, `asset.py`, `policy_assignment.py` |
| 서비스 내부 헬퍼 | `_` 접두사 + snake_case | `_policy_helpers.py` |
| 라우터 | 복수 snake_case | `projects.py`, `assets.py`, `port_maps.py` |

## Python 규칙

- 모델 클래스: `PascalCase` 단수
- 테이블명: 복수 snake_case
- 스키마 클래스: `{Model}{Operation}` (`Create`, `Update`, `Read`)
- 서비스 함수(CRUD): `create_*`, `list_*`, `get_*`, `update_*`, `delete_*`
- `get_all`, `add`, `set` 사용 금지
- 비-CRUD 서비스 함수는 `동사_목적어` 형태 사용
- private 함수는 `_` 접두사 사용
- SQLAlchemy Boolean 필터는 `.is_(True)`, `.is_(False)` 사용

## API 라우트 규칙

- `prefix="/api/v1/{리소스}"` 사용
- 여러 리소스를 하나의 라우터에서 처리할 때만 `prefix="/api/v1"` 사용
- 리소스 URL은 복수 kebab-case 사용
- 중첩 리소스는 `/{부모}/{id}/{자식}` 패턴 사용
- CRUD는 GET/POST/PATCH/DELETE를 사용하고 PUT은 사용하지 않는다
- 비-CRUD 동작은 `POST /{리소스}/{id}/{동작}` 패턴을 사용한다

## 도메인 용어 통일

| 개념 | 표준 용어 (DB/API) | 비고 |
| ---- | ----------------- | ---- |
| 프로젝트 | `project` | `contract`, `job` 사용 금지 |
| 프로젝트 단계 | `project_phase` | `stage`는 enum 값으로만 사용 |
| 산출물 | `deliverable` | |
| 자산 | `asset` | 중심 엔티티 |
| 자산 IP | `asset_ip` | `ip_inventory`는 UI 명칭으로 사용 가능 |
| 포트맵 | `port_map` | |
| 정책 정의 | `policy_definition` | |
| 정책 적용 | `policy_assignment` | |
| 업체 | `partner` | `customer`, `vendor`는 partner_type 값으로 표현 |
| 담당자 | `contact` | |
