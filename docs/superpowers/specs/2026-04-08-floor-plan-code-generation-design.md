# 전산실 상면도 고도화 + 시스템ID/프로젝트코드 자동생성

> 전산실 격자 기반 상면도 시각화와, 위치 계층 데이터를 활용한 이원 코드 체계(시스템ID + 프로젝트코드).

## 1. 목표

- 전산실을 `grid_cols × grid_rows` 격자로 시각화
- 격자 위에 열(RackLine) 단위로 랙 배치 라인을 정의
- 라인 내 슬롯에 랙을 드래그로 배치
- **시스템 ID**: 위치 계층의 `_code` 필드를 자동 조합한 안정적 참조키
- **프로젝트 코드**: `prefix` 필드 + 템플릿 기반의 가변 운영 코드

## 2. 이원 코드 체계

### 2.1 개념

자산(Asset) 모델의 기존 패턴을 센터/전산실/랙에도 동일하게 적용한다.

| 구분 | 시스템 ID (`system_id`) | 프로젝트 코드 (`project_code`) |
|------|------------------------|-------------------------------|
| 목적 | 시스템 내부 안정 참조키 | 프로젝트별 운영 식별자 |
| 출처 | `_code` 필드 계층 조합 | `prefix` 필드 + 템플릿 |
| 생성 | 엔티티 생성 시 자동 | 템플릿 설정 시 자동, 아니면 수동 |
| 변경 | 부모 코드 변경 시 하위 전체 갱신 | 템플릿/prefix 변경 시 일괄 재생성 |
| 안정성 | 높음 (참조키 역할) | 가변 (운영 환경에 맞춰 변경 가능) |

### 2.2 예시

```
         고객사 | 센터 | 전산실 | 랙
시스템ID: P000 - C01  - R01   - A12       ← _code 필드 조합 (자동, 안정)
프로젝트코드:     S07A - A12  - 41        ← prefix + 템플릿 (가변, 커스텀)
```

| 계층 | _code (시스템ID 세그먼트) | prefix (프로젝트코드 세그먼트) |
|------|--------------------------|-------------------------------|
| 고객사 (Partner) | `P000` | — |
| 센터 | `C01` | `S` |
| 전산실 | `R01` | `07A` |
| 라인 | — | `A` |
| 랙 위치 | — | (line_position: `12`) |
| U 위치 | — | (rack_start_unit: `41`) |

- **센터 system_id:** `P000-C01`
- **전산실 system_id:** `P000-C01-R01`
- **랙 system_id:** `P000-C01-R01-A12`
- **랙 프로젝트코드:** `S07A-A12` (템플릿: `{center.prefix}{room.prefix}-{line.prefix}{rack.position}`)
- **자산 프로젝트코드:** `S07A-A12-41` (템플릿: `{rack.project_code}-{unit}`)

### 2.3 자산 모델과의 대응

| 자산 (기존) | 센터/전산실/랙 (신규) |
|------------|---------------------|
| `asset_code` (시스템 식별) | `system_id` (계층 조합) |
| `project_asset_number` (프로젝트 코드) | `project_code` (템플릿 기반) |

## 3. 데이터 모델 변경

### 3.1 Center (변경)

```
centers
├── ... (기존 필드: center_code, center_name 등)
├── system_id (str 100, unique, nullable) ─── 자동생성 (예: "P000-C01")
├── prefix (str 10, nullable) ─── 프로젝트코드용 약칭 (예: "S")
├── project_code (str 100, nullable) ─── 프로젝트코드 (가변)
```

- `system_id` = `{partner_code}-{center_code}` 형태로 자동 생성
- 기존 `center_code`는 로컬 식별자로 유지

### 3.2 Room (변경)

```
rooms
├── ... (기존 필드: room_code, room_name 등)
├── system_id (str 100, unique, nullable) ─── 자동생성 (예: "P000-C01-R01")
├── prefix (str 20, nullable) ─── 프로젝트코드용 약칭 (예: "07A")
├── project_code (str 100, nullable) ─── 프로젝트코드 (가변)
├── grid_cols (int, default 10) ─── 격자 열 수
├── grid_rows (int, default 12) ─── 격자 행 수
```

기존 `racks_per_row` 필드는 유지하되, 상면도 뷰에서는 `grid_cols`/`grid_rows`를 사용한다.

### 3.3 RackLine (신설)

```
rack_lines
├── id (PK)
├── room_id (FK → rooms, CASCADE)
├── line_name (str 50) ─── 표시명 (예: "A열")
├── col_index (int) ─── 격자 내 열 위치 (0-based)
├── slot_count (int) ─── 라인 내 슬롯 수 (= grid_rows 이하)
├── disabled_slots (JSON, default []) ─── 비활성 위치 배열 (예: [3, 7])
├── sort_order (int, default 0)
├── prefix (str 20, nullable) ─── 프로젝트코드용 약칭 (예: "A")
├── created_at, updated_at (TimestampMixin)
├── UNIQUE(room_id, col_index)
```

### 3.4 Rack (변경)

```
racks
├── ... (기존 필드: rack_code, rack_name 등)
├── system_id (str 100, unique, nullable) ─── 자동생성 (예: "P000-C01-R01-A12")
├── project_code (str 100, nullable) ─── 프로젝트코드 (가변)
├── rack_line_id (FK → rack_lines, SET NULL, nullable) ─── 소속 라인
├── line_position (int, nullable) ─── 라인 내 위치 (행 번호, 0-based)
```

- 기존 `rack_code`는 로컬 식별자로 유지

### 3.5 Asset (변경)

```
assets
├── ... (기존 필드)
├── project_code (str 100, nullable) ─── 프로젝트코드 (가변)
```

- 기존 `asset_code`가 시스템 ID 역할을 이미 수행
- `project_asset_number`는 기존 필드로 유지, `project_code`는 상면도 기반 자동생성용

### 3.6 ContractPeriod (변경)

```
contract_periods
├── ... (기존 필드)
├── rack_project_code_template (str 200, nullable) ─── 랙 프로젝트코드 템플릿
├── asset_project_code_template (str 200, nullable) ─── 자산 프로젝트코드 템플릿
```

**사용 가능한 템플릿 변수:**

| 변수 | 출처 | 설명 |
|------|------|------|
| `{center.prefix}` | Center.prefix | 센터 약칭 |
| `{room.prefix}` | Room.prefix | 전산실 약칭 |
| `{line.prefix}` | RackLine.prefix | 라인 약칭 |
| `{rack.position}` | Rack.line_position | 라인 내 위치 (1-based 표시) |
| `{rack.project_code}` | Rack.project_code | 랙 프로젝트코드 (자산 템플릿에서 참조) |
| `{unit}` | Asset.rack_start_unit | 장비 시작 U 위치 |

**기본 템플릿 예시 (미설정 시 자유 텍스트 입력):**
- 랙: `{center.prefix}{room.prefix}-{line.prefix}{rack.position}`
- 자산: `{rack.project_code}-{unit}`

## 4. 시스템 ID 자동생성 로직

### 4.1 생성 규칙

시스템 ID는 부모의 `_code` 필드를 `-`로 연결하여 자동 생성한다.

| 엔티티 | system_id 구성 | 예시 |
|--------|---------------|------|
| Center | `{partner.partner_code}-{center_code}` | `P000-C01` |
| Room | `{center.system_id}-{room_code}` | `P000-C01-R01` |
| Rack | `{room.system_id}-{rack_code}` | `P000-C01-R01-A12` |

### 4.2 생성 시점

- 엔티티 **생성** 시 자동 계산하여 저장
- 부모 또는 자신의 `_code` **변경** 시 자신 + 하위 엔티티의 system_id를 재귀적으로 갱신
- 갱신은 서비스 레이어에서 처리 (cascade update)

### 4.3 제약

- `system_id`는 전체 테이블에서 unique
- 사용자가 직접 수정할 수 없음 (읽기 전용, `_code` 변경을 통해서만 간접 변경)

## 5. 프로젝트 코드 자동생성 로직

### 5.1 자동완성 (배치 시)

- 랙을 라인 슬롯에 배치할 때 `rack_project_code_template`이 설정되어 있으면:
  1. 관련 엔티티의 prefix 값 수집
  2. 템플릿에 변수 치환하여 코드 생성
  3. 생성된 코드를 `project_code` 필드에 자동 입력 (사용자 수정 가능)
- prefix가 비어있는 엔티티가 있으면 해당 변수는 빈 문자열로 치환 + 경고 표시

### 5.2 일괄생성 (템플릿 변경 시)

1. 프로젝트 설정에서 템플릿 수정
2. "코드 재생성" 버튼 클릭
3. 미리보기 API 호출 → 변경 전/후 목록 표시 (변경될 항목, 스킵될 항목, 사유)
4. 사용자 확인 후 일괄 적용 API 호출

### 5.3 템플릿 파싱

- `{variable}` 패턴을 정규식으로 추출
- 지원 변수 외의 변수가 있으면 에러
- 리터럴 문자(구분자 등)는 그대로 유지

## 6. API 변경

### 6.1 변경 엔드포인트

| 엔드포인트 | 변경 내용 |
|-----------|----------|
| `PATCH /api/v1/centers/{id}` | `prefix`, `project_code` 필드 추가. `center_code` 변경 시 system_id 재계산 |
| `PATCH /api/v1/rooms/{id}` | `grid_cols`, `grid_rows`, `prefix`, `project_code` 추가. `room_code` 변경 시 system_id 재계산 |
| `PATCH /api/v1/racks/{id}` | `rack_line_id`, `line_position`, `project_code` 추가. `rack_code` 변경 시 system_id 재계산 |

### 6.2 신규 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/v1/rooms/{id}/rack-lines` | 전산실의 라인 목록 (소속 랙 포함) |
| `POST /api/v1/rooms/{id}/rack-lines` | 라인 생성 |
| `PATCH /api/v1/rack-lines/{id}` | 라인 수정 (disabled_slots, prefix 등) |
| `DELETE /api/v1/rack-lines/{id}` | 라인 삭제 (소속 랙의 rack_line_id → null) |
| `POST /api/v1/contract-periods/{id}/generate-codes` | 템플릿 기반 프로젝트코드 일괄생성 |
| `GET /api/v1/contract-periods/{id}/preview-codes` | 일괄생성 전 미리보기 |

### 6.3 GET /api/v1/rooms/{id}/rack-lines 응답

```json
[
  {
    "id": 1,
    "line_name": "A열",
    "col_index": 0,
    "slot_count": 12,
    "disabled_slots": [3, 7],
    "prefix": "A",
    "sort_order": 0,
    "racks": [
      {
        "id": 10,
        "rack_code": "A12",
        "system_id": "P000-C01-R01-A12",
        "project_code": "S07A-A12",
        "line_position": 11,
        "total_units": 42,
        "used_units": 28
      }
    ]
  }
]
```

### 6.4 GET /api/v1/contract-periods/{id}/preview-codes 응답

```json
{
  "target": "rack",
  "template": "{center.prefix}{room.prefix}-{line.prefix}{rack.position}",
  "changes": [
    {
      "id": 10,
      "system_id": "P000-C01-R01-A12",
      "current_project_code": null,
      "generated_project_code": "S07A-A12",
      "missing_fields": []
    },
    {
      "id": 15,
      "system_id": "P000-C01-R01-B03",
      "current_project_code": "OLD-CODE",
      "generated_project_code": null,
      "missing_fields": ["center.prefix"]
    }
  ],
  "summary": {
    "total": 24,
    "will_update": 20,
    "skipped": 4
  }
}
```

## 7. 상면도 UI

### 7.1 격자 렌더링

- 전산실 선택 시 `grid_cols × grid_rows` 격자 렌더링
- 각 셀은 기본적으로 바닥색 (빈 공간)
- 라인이 정의된 열은 배경색으로 구분
- 라인 내 비활성 슬롯(`disabled_slots`)은 바닥색과 동일하게 처리 → 시각적으로 통로/빈 공간처럼 보임
- 격자 상단에 열 헤더, 좌측에 행 번호

### 7.2 라인 편집

1. 빈 열 클릭 → 라인 생성 모달 (이름, prefix 입력)
2. 라인 생성 시 해당 열 전체가 활성 슬롯으로 초기화
3. 라인 내 개별 슬롯 클릭 → 활성/비활성 토글
4. 라인 헤더 클릭 → 라인 수정/삭제 옵션

### 7.3 랙 배치

1. 미배치 랙 목록이 격자 하단에 표시
2. 미배치 랙을 라인의 활성 슬롯으로 드래그 → `rack_line_id`, `line_position` 저장
3. 배치된 랙을 다른 활성 슬롯으로 드래그 → 위치 변경
4. 배치된 랙을 미배치 영역으로 드래그 → 배치 해제
5. 배치 시 프로젝트코드 템플릿이 설정되어 있으면 자동생성하여 셀에 표시

### 7.4 코드 표시

- 격자 셀에 배치된 랙: `system_id` 또는 `project_code` 표시 (토글 가능)
- 랙 상세에서 system_id(읽기 전용)와 project_code(편집 가능) 모두 표시

### 7.5 기존 뷰와의 관계

- 기존 전산실 뷰(랙 카드 격자, `racks_per_row` 기반)는 상면도 뷰로 대체
- 기존 랙 뷰(U 다이어그램)는 그대로 유지 — 격자에서 랙 클릭 시 진입
- 트리 구조 동일 유지 (센터 > 층 > 전산실 > 랙)

## 8. 유효성 검사

- 같은 라인 내 동일 `line_position`에 랙 중복 배치 불가
- `disabled_slots`에 포함된 위치에 랙 배치 불가
- `line_position`은 0 이상 `slot_count - 1` 이하
- 격자 크기(`grid_cols`) 축소 시 범위 밖에 기존 라인이 있으면 경고 후 사용자 확인
- 프로젝트코드 일괄생성 시 prefix가 비어있는 엔티티가 있으면 해당 항목 스킵 + 경고 목록 표시
- RackLine 삭제 시 소속 랙의 `rack_line_id`는 null로 설정 (랙 자체는 유지)
- `system_id`는 unique 제약 — `_code` 변경 시 충돌 검사

## 9. 마이그레이션

단일 Alembic migration으로 처리:
- Center: `system_id`, `prefix`, `project_code` 추가
- Room: `system_id`, `prefix`, `project_code`, `grid_cols`, `grid_rows` 추가
- Rack: `system_id`, `project_code`, `rack_line_id`, `line_position` 추가
- Asset: `project_code` 추가
- ContractPeriod: `rack_project_code_template`, `asset_project_code_template` 추가
- `rack_lines` 테이블 생성
- 마이그레이션 시 기존 데이터의 system_id를 부모 코드 조합으로 일괄 생성

## 10. 스코프 외

- 전력/네트워크 케이블 시각화
- 발열/전력 용량 관리
- 전산실 실제 도면(CAD) 기반 배치
- 랙 전면/후면 구분
- 코드 생성 이력/감사 로그
