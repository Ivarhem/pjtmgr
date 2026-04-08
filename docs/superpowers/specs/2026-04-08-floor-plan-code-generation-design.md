# 전산실 상면도 고도화 + 랙ID/프로젝트코드 자동생성

> 전산실 격자 기반 상면도 시각화와 위치 데이터를 활용한 코드 자동생성 시스템.

## 1. 목표

- 전산실을 `grid_cols × grid_rows` 격자로 시각화
- 격자 위에 열(RackLine) 단위로 랙 배치 라인을 정의
- 라인 내 슬롯에 랙을 드래그로 배치
- 위치 계층 데이터(센터 > 전산실 > 라인 > 랙 위치 > U)를 조합하여 랙ID/프로젝트코드를 자동생성
- 프로젝트별 생성규칙(템플릿) 커스텀 가능

## 2. 배경: 코드 생성 의도

전산실 상면도의 위치 데이터를 랙ID/프로젝트코드 자동생성에 활용한다.

**예시:** 상암센터 7층A전산실 A열 12번 랙 41U 장비

| 계층 | 값 | prefix |
|------|-----|--------|
| 센터 | 상암센터 | `S` |
| 전산실 | 7층A전산실 | `07A` |
| 라인 | A열 | `A` |
| 랙 위치 | 12번 | `12` |
| U 위치 | 41U | `41` |

- **랙ID:** `S07A-A12` — `{center.prefix}{room.prefix}-{line.prefix}{rack.position}`
- **프로젝트코드:** `S07A-A12-41` — `{rack_id}-{unit}`

## 3. 데이터 모델 변경

### 3.1 Room (변경)

```
rooms
├── ... (기존 필드)
├── grid_cols (int, default 10) ─── 격자 열 수
├── grid_rows (int, default 12) ─── 격자 행 수
├── prefix (str 20, nullable) ─── 코드 생성용 약칭 (예: "07A")
```

기존 `racks_per_row` 필드는 유지하되, 상면도 뷰에서는 `grid_cols`/`grid_rows`를 사용한다.

### 3.2 RackLine (신설)

```
rack_lines
├── id (PK)
├── room_id (FK → rooms, CASCADE)
├── line_name (str 50) ─── 표시명 (예: "A열")
├── col_index (int) ─── 격자 내 열 위치 (0-based)
├── slot_count (int) ─── 라인 내 슬롯 수 (= grid_rows 이하)
├── disabled_slots (JSON, default []) ─── 비활성 위치 배열 (예: [3, 7])
├── sort_order (int, default 0)
├── prefix (str 20, nullable) ─── 코드 생성용 약칭 (예: "A")
├── created_at, updated_at (TimestampMixin)
├── UNIQUE(room_id, col_index)
```

### 3.3 Rack (변경)

```
racks
├── ... (기존 필드)
├── rack_line_id (FK → rack_lines, SET NULL, nullable) ─── 소속 라인
├── line_position (int, nullable) ─── 라인 내 위치 (행 번호, 0-based)
```

- 생성된 랙ID는 기존 `rack_code` 필드에 저장

### 3.3.1 Asset (변경)

```
assets
├── ... (기존 필드)
├── project_code (str 100, nullable) ─── 프로젝트코드 (자동생성 또는 수동입력)
```

### 3.4 Center (변경)

```
centers
├── ... (기존 필드)
├── prefix (str 10, nullable) ─── 코드 생성용 약칭 (예: "S")
```

### 3.5 ContractPeriod (변경)

```
contract_periods
├── ... (기존 필드)
├── rack_id_template (str 200, nullable) ─── 랙ID 생성 템플릿
├── project_code_template (str 200, nullable) ─── 프로젝트코드 생성 템플릿
```

**기본 템플릿 (미설정 시 자유 텍스트 입력):**
- `rack_id_template`: `"{center.prefix}{room.prefix}-{line.prefix}{rack.position}"`
- `project_code_template`: `"{rack_id}-{unit}"`

**사용 가능한 템플릿 변수:**

| 변수 | 출처 | 설명 |
|------|------|------|
| `{center.prefix}` | Center.prefix | 센터 약칭 |
| `{room.prefix}` | Room.prefix | 전산실 약칭 |
| `{line.prefix}` | RackLine.prefix | 라인 약칭 |
| `{rack.position}` | Rack.line_position | 라인 내 위치 (1-based 표시) |
| `{rack_id}` | 생성된 랙ID | 프로젝트코드에서 랙ID 참조 |
| `{unit}` | Asset.rack_start_unit | 장비 시작 U 위치 |

## 4. API 변경

### 4.1 변경 엔드포인트

| 엔드포인트 | 변경 내용 |
|-----------|----------|
| `PATCH /api/v1/centers/{id}` | `prefix` 필드 추가 |
| `PATCH /api/v1/rooms/{id}` | `grid_cols`, `grid_rows`, `prefix` 필드 추가 |
| `PATCH /api/v1/racks/{id}` | `rack_line_id`, `line_position` 필드 추가 |

### 4.2 신규 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/v1/rooms/{id}/rack-lines` | 전산실의 라인 목록 (소속 랙 포함) |
| `POST /api/v1/rooms/{id}/rack-lines` | 라인 생성 |
| `PATCH /api/v1/rack-lines/{id}` | 라인 수정 (disabled_slots, prefix 등) |
| `DELETE /api/v1/rack-lines/{id}` | 라인 삭제 (소속 랙의 rack_line_id → null) |
| `POST /api/v1/contract-periods/{id}/generate-codes` | 템플릿 기반 코드 일괄생성 |
| `GET /api/v1/contract-periods/{id}/preview-codes` | 일괄생성 전 미리보기 |

### 4.3 GET /api/v1/rooms/{id}/rack-lines 응답

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
        "rack_code": "A-01",
        "rack_name": "랙-01",
        "line_position": 0,
        "total_units": 42,
        "used_units": 28
      }
    ]
  }
]
```

### 4.4 GET /api/v1/contract-periods/{id}/preview-codes 응답

```json
{
  "template": "{center.prefix}{room.prefix}-{line.prefix}{rack.position}",
  "changes": [
    {
      "rack_id": 10,
      "rack_code": "A-01",
      "current_value": null,
      "generated_value": "S07A-A01",
      "missing_fields": []
    },
    {
      "rack_id": 15,
      "rack_code": "B-03",
      "current_value": "OLD-CODE",
      "generated_value": null,
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

## 5. 상면도 UI

### 5.1 격자 렌더링

- 전산실 선택 시 `grid_cols × grid_rows` 격자 렌더링
- 각 셀은 기본적으로 바닥색 (빈 공간)
- 라인이 정의된 열은 배경색으로 구분
- 라인 내 비활성 슬롯(`disabled_slots`)은 바닥색과 동일하게 처리 → 시각적으로 통로/빈 공간처럼 보임
- 격자 상단에 열 헤더 (A, B, C, ...), 좌측에 행 번호 (1, 2, 3, ...)

### 5.2 라인 편집

1. 빈 열 클릭 → 라인 생성 모달 (이름, prefix 입력)
2. 라인 생성 시 해당 열 전체가 활성 슬롯으로 초기화
3. 라인 내 개별 슬롯 클릭 → 활성/비활성 토글
4. 라인 헤더 클릭 → 라인 수정/삭제 옵션

### 5.3 랙 배치

1. 미배치 랙 목록이 격자 하단에 표시
2. 미배치 랙을 라인의 활성 슬롯으로 드래그 → `rack_line_id`, `line_position` 저장
3. 배치된 랙을 다른 활성 슬롯으로 드래그 → 위치 변경
4. 배치된 랙을 미배치 영역으로 드래그 → 배치 해제
5. 배치 시 코드 템플릿이 설정되어 있으면 랙ID 자동생성하여 셀에 표시

### 5.4 기존 뷰와의 관계

- 기존 전산실 뷰(랙 카드 격자, `racks_per_row` 기반)는 상면도 뷰로 대체
- 기존 랙 뷰(U 다이어그램)는 그대로 유지 — 격자에서 랙 클릭 시 진입
- 트리 구조 동일 유지 (센터 > 층 > 전산실 > 랙)

## 6. 코드 자동생성 로직

### 6.1 자동완성 (배치 시)

- 랙을 라인 슬롯에 배치할 때 `rack_id_template`이 설정되어 있으면:
  1. 관련 엔티티의 prefix 값 수집
  2. 템플릿에 변수 치환하여 코드 생성
  3. 생성된 코드를 해당 필드에 자동 입력 (사용자 수정 가능)
- prefix가 비어있는 엔티티가 있으면 해당 변수는 빈 문자열로 치환 + 경고 표시

### 6.2 일괄생성 (템플릿 변경 시)

1. 프로젝트 설정에서 템플릿 수정
2. "코드 재생성" 버튼 클릭
3. 미리보기 API 호출 → 변경 전/후 목록 표시 (변경될 항목, 스킵될 항목, 사유)
4. 사용자 확인 후 일괄 적용 API 호출

### 6.3 템플릿 파싱

- `{variable}` 패턴을 정규식으로 추출
- 지원 변수 외의 변수가 있으면 에러
- 리터럴 문자(구분자 등)는 그대로 유지

## 7. 유효성 검사

- 같은 라인 내 동일 `line_position`에 랙 중복 배치 불가
- `disabled_slots`에 포함된 위치에 랙 배치 불가
- `line_position`은 0 이상 `slot_count - 1` 이하
- 격자 크기(`grid_cols`) 축소 시 범위 밖에 기존 라인이 있으면 경고 후 사용자 확인
- 코드 일괄생성 시 prefix가 비어있는 엔티티가 있으면 해당 항목 스킵 + 경고 목록 표시
- RackLine 삭제 시 소속 랙의 `rack_line_id`는 null로 설정 (랙 자체는 유지)

## 8. 마이그레이션

단일 Alembic migration으로 처리:
- Room: `grid_cols`, `grid_rows`, `prefix` 추가
- Center: `prefix` 추가
- ContractPeriod: `rack_id_template`, `project_code_template` 추가
- `rack_lines` 테이블 생성
- Rack: `rack_line_id`, `line_position` 추가
- Asset: `project_code` 추가

## 9. 스코프 외

- 전력/네트워크 케이블 시각화
- 발열/전력 용량 관리
- 전산실 실제 도면(CAD) 기반 배치
- 랙 전면/후면 구분
- 코드 생성 이력/감사 로그
