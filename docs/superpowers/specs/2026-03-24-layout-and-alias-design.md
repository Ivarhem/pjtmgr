# 전산실 배치도 + Alias 관리 설계

> 작성일: 2026-03-24
> 상태: 승인됨
> 브랜치: feat/unified-business-model

---

## 1. 개요

인프라모듈에 두 가지 기능을 추가한다.

1. **전산실 배치도** — 센터/전산실/랙의 공간 구조를 정의하고, 자산을 랙에 매핑하여 시각화
2. **Alias 관리** — 자산의 다양한 호칭(고객명, 팀명, 레거시명 등)을 관리하고 검색에 활용

## 2. 설계 원칙

- **기존 패턴 준수**: Period 계층 구조(FK 체인 + bridge 테이블) 패턴을 동일하게 적용
- **원장 분리**: 배치도는 Asset 원장의 시각화 레이어. Asset이 진실의 원천, 배치도는 공간 기준 뷰
- **기존 필드 유지**: Asset의 `center`, `rack_no`, `rack_unit` 문자열 필드는 그대로 유지. Excel Import 영향 없음
- **일관된 시각 언어**: 프로젝트 전체에 "원장 연결 = 정상색, 미연결 = 회색" 패턴 적용
- **그리드 기반 편집**: CAD/자유도형 금지. 셀 단위 조작만 허용

## 3. 전산실 배치도

### 3.1 메뉴 구조

- 사이드바 독립 메뉴: **전산실 배치도**
- 하위 화면 (탭):
  - 센터 관리
  - 전산실 관리
  - 배치도 편집
  - 자산 매핑 현황

### 3.2 데이터 모델

계층 구조: `Center → Room → RoomZone / RackPosition → AssetRackMapping → Asset`

#### Center (센터)

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | Integer | PK | |
| partner_id | Integer | FK(partners.id), NOT NULL, INDEX | 고객사 스코프 |
| center_code | String(50) | NOT NULL | 센터 코드 |
| center_name | String(200) | NOT NULL | 센터명 |
| address | String(500) | nullable | 주소 |
| note | Text | nullable | 비고 |
| created_at, updated_at | | TimestampMixin | |

- UniqueConstraint: (partner_id, center_code) — 고객사 내 센터 코드 유일
- FK partner_id: ondelete 미지정 (Partner 삭제 시 FK 제약으로 차단 — 의도적. 센터가 있는 고객사는 삭제 불가)

#### Room (전산실)

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | Integer | PK | |
| center_id | Integer | FK(centers.id, ondelete=CASCADE), NOT NULL, INDEX | |
| room_code | String(50) | NOT NULL | 전산실 코드 |
| room_name | String(200) | NOT NULL | 전산실명 |
| grid_rows | Integer | NOT NULL | 그리드 행 수 |
| grid_cols | Integer | NOT NULL | 그리드 열 수 |
| note | Text | nullable | 비고 |
| created_at, updated_at | | TimestampMixin | |

- UniqueConstraint: (center_id, room_code)
- CheckConstraint: grid_rows >= 1, grid_cols >= 1

#### RoomZone (전산실 영역/경계)

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | Integer | PK | |
| room_id | Integer | FK(rooms.id, ondelete=CASCADE), NOT NULL, INDEX | |
| zone_name | String(100) | NOT NULL | 영역명 |
| start_row | Integer | NOT NULL | 시작 행 |
| start_col | Integer | NOT NULL | 시작 열 |
| end_row | Integer | NOT NULL | 끝 행 |
| end_col | Integer | NOT NULL | 끝 열 |
| note | Text | nullable | 비고 |
| created_at, updated_at | | TimestampMixin | |

- UniqueConstraint: (room_id, zone_name)
- Zone 영역 겹침: 서비스 레이어에서 검증 (DB 제약 아님). 겹치는 zone 생성 시 에러 반환.

#### RackPosition (랙 위치)

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | Integer | PK | |
| room_id | Integer | FK(rooms.id, ondelete=CASCADE), NOT NULL, INDEX | |
| row_no | Integer | NOT NULL | 그리드 행 위치 |
| col_no | Integer | NOT NULL | 그리드 열 위치 |
| rack_code | String(50) | NOT NULL | 랙 코드 |
| rack_name | String(200) | nullable | 랙명 |
| ru_size | Integer | NOT NULL | RU 크기 |
| face_direction | String(10) | NOT NULL | 방향 — FaceDirection Enum (UP/DOWN/LEFT/RIGHT) |
| note | Text | nullable | 비고 |
| created_at, updated_at | | TimestampMixin | |

- UniqueConstraint: (room_id, row_no, col_no) — 셀 1개에 랙 1개
- UniqueConstraint: (room_id, rack_code) — 전산실 내 랙 코드 유일

#### AssetRackMapping (자산-랙 매핑, bridge 테이블)

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | Integer | PK | |
| asset_id | Integer | FK(assets.id, ondelete=CASCADE), NOT NULL, INDEX | |
| rack_position_id | Integer | FK(rack_positions.id, ondelete=CASCADE), NOT NULL, INDEX | |
| ru_start | Integer | nullable | RU 시작 위치 |
| ru_end | Integer | nullable | RU 끝 위치 |
| note | Text | nullable | 비고 |
| created_at, updated_at | | TimestampMixin | |

- UniqueConstraint: (asset_id) — 자산 1개는 랙 1곳에만 매핑 (의도적 제약: 블레이드/HA 등 다중 위치는 향후 확장 시 해제 가능)
- RU 충돌(동일 랙 내 ru_start~ru_end 겹침): 서비스 레이어에서 검증 (ru_start/ru_end nullable이므로 DB 제약 부적합). 충돌 시 경고 반환, 저장은 허용 (시각화에서 빨간색 표시).

### 3.3 그리드 방식

방식 B 채택: Room의 grid_rows/grid_cols로 프론트가 빈 그리드를 생성. DB에는 의미 있는 셀(RoomZone, RackPosition)만 저장.

### 3.4 매핑 상태 시각화

| 상태 | 조건 | 표시 |
|---|---|---|
| mapped | AssetRackMapping 존재 | 기본색 |
| unmapped_asset | Asset에 center/rack_no 텍스트 있으나 매핑 없음 | 회색 텍스트 |
| empty_rack | RackPosition 있으나 매핑된 Asset 없음 | 연한색 |
| conflict | 동일 RU 범위에 Asset 중복 | 빨간색 |

### 3.5 자동 매핑 로직

- 1순위: Asset.center + Asset.rack_no와 Center.center_code + RackPosition.rack_code **완전일치**
- 2순위: Asset.rack_no와 RackPosition.rack_code 일치 (center 미기재 시)
- 유사 매칭(fuzzy) 없음

### 3.6 화면 구조

- **상단**: 센터 선택 → 전산실 선택 → 편집/조회 모드 전환
- **좌측 패널**: 센터/전산실 정보, 랙 목록, 미매핑 자산 목록
- **중앙**: 그리드 캔버스 (셀 드래그로 zone 지정, 셀 클릭으로 랙 등록)
- **우측 패널/모달**: 선택 셀 정보, 랙 상세, 매핑된 Asset 목록

### 3.7 구현 순서

1. 센터/전산실 CRUD (공간 입력)
2. 전산실 경계(zone) 편집
3. 랙 위치 등록
4. 자산 매핑 + 시각화

## 4. Alias 관리

### 4.1 메뉴 구조

- 자산 상세 내 섹션 (AssetContact, AssetSoftware와 동일 패턴)
- 별도 사이드바 메뉴 없음

### 4.2 데이터 모델

#### AssetAlias (자산 별칭)

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | Integer | PK | |
| asset_id | Integer | FK(assets.id, ondelete=CASCADE), NOT NULL, INDEX | |
| alias_name | String(255) | NOT NULL, UNIQUE | 별칭 (전체 자산 범위에서 유일) |
| alias_type | String(30) | NOT NULL | AliasType Enum (INTERNAL/CUSTOMER/VENDOR/TEAM/LEGACY/ETC) |
| source_partner_id | Integer | FK(partners.id, ondelete=SET NULL), nullable, INDEX | 출처 업체 (원장 연결) |
| source_text | String(200) | nullable | 출처 텍스트 (원장에 없는 경우) |
| note | Text | nullable | 비고 |
| is_primary | Boolean | NOT NULL, default=False | 대표 alias 여부 |
| created_at, updated_at | | TimestampMixin | |

- alias_name UNIQUE: 중복 alias 불허. 동일 이름이 다른 자산에 붙을 수 없음.

### 4.3 source 연결 시각화

| 상태 | 조건 | 표시 |
|---|---|---|
| 원장 연결 | source_partner_id 있음 | 정상색, 업체명 클릭 가능 |
| 미연결 | source_text만 있음 | 회색 텍스트 |

### 4.4 검색 통합

자산 검색 시 다음 필드 모두 검색 대상:
- asset_name
- asset_code
- alias_name (AssetAlias JOIN)

### 4.5 향후 확장

Alias 구조는 Asset 외에 Partner, Room, Rack 등에도 동일 패턴으로 확장 가능. 현재는 Asset만 구현.

## 5. API 구조

기존 패턴(Create/Update/Read 스키마, 얇은 라우터 + 서비스 레이어) 준수.

### 배치도 API

| 엔드포인트 | 설명 |
|---|---|
| `/api/v1/centers` | Center CRUD |
| `/api/v1/centers/{id}/rooms` | Room CRUD (센터 하위) |
| `/api/v1/rooms/{id}/zones` | RoomZone CRUD (전산실 하위) |
| `/api/v1/rooms/{id}/racks` | RackPosition CRUD (전산실 하위) |
| `/api/v1/rack-positions/{id}/mappings` | AssetRackMapping CRUD (랙 하위) |
| `/api/v1/rooms/{id}/layout` | 전산실 전체 레이아웃 조회 (zone + rack + mapping 한 번에) |
| `/api/v1/rooms/{id}/auto-map` | 자동 매핑 실행 |

### Alias API

| 엔드포인트 | 설명 |
|---|---|
| `/api/v1/assets/{id}/aliases` | AssetAlias CRUD (자산 하위) |

## 6. 파일 구조

```
app/modules/infra/
├── models/
│   ├── center.py
│   ├── room.py
│   ├── room_zone.py
│   ├── rack_position.py
│   ├── asset_rack_mapping.py
│   └── asset_alias.py
├── schemas/
│   ├── center.py
│   ├── room.py
│   ├── room_zone.py
│   ├── rack_position.py
│   ├── asset_rack_mapping.py
│   └── asset_alias.py
├── services/
│   ├── center_service.py
│   ├── room_service.py
│   ├── layout_service.py       # zone + rack + mapping + 자동매핑
│   └── asset_alias_service.py
├── routers/
│   ├── centers.py
│   ├── rooms.py
│   ├── room_zones.py
│   ├── rack_positions.py
│   ├── asset_rack_mappings.py
│   └── asset_aliases.py
└── templates/
    └── infra_layout.html        # 배치도 메인 (탭: 센터/전산실/배치도편집/매핑현황)
```

## 7. Migration

Alembic migration 1건으로 6개 테이블(centers, rooms, room_zones, rack_positions, asset_rack_mappings, asset_aliases) 일괄 생성.
