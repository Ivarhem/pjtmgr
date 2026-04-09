# 배치 페이지 재설계

> 3컬럼 테이블 → 트리 + 시각화 배치도로 전환. 랙/장비 드래그 배치 포함.

## 1. 목표

- 좌측 트리로 센터 > 층 > 전산실 > 랙 계층 탐색
- 전산실 선택 시 랙 배치도 (격자 + 드래그 순서 재배치)
- 랙 선택 시 장비 배치도 (세로 U 다이어그램 + 드래그 U 위치 변경)
- 랙 라벨링 기준(start/end) 프로젝트 설정 + 페이지 임시 전환

## 2. 레이아웃

역할 기준 보기(`infra_asset_roles.html`) 패턴 참조 — 좌측 트리 패널 + 우측 콘텐츠 패널.

### 2.1 좌측: 트리 패널

```
📍 센터A
  └ 1F
    └ 🚪 전산실A (12랙)
      └ 💽 랙-01 (42U)
      └ 💽 랙-02 (42U)
  └ 2F
    └ 🚪 전산실B (8랙)
📍 센터B
  └ 1F
    └ 🚪 전산실C
```

- 센터: API에서 로드 (`GET /api/v1/centers?partner_id=X`)
- 층: `Room.floor` 값으로 가상 그룹핑 (별도 엔티티 아님)
- 전산실: 센터 하위 (`GET /api/v1/centers/{id}/rooms`)
- 랙: 전산실 하위 (`GET /api/v1/rooms/{id}/racks`)
- floor 값이 없거나 동일한 전산실은 하나의 층 그룹으로 묶음

### 2.2 우측: 콘텐츠 패널 (선택 레벨에 따라 전환)

| 트리 선택 | 우측 표시 |
|-----------|----------|
| 센터 | 센터 기본정보 + 전산실 요약 목록 |
| 층 | 해당 층 전산실 목록 (카드) |
| 전산실 | **랙 배치도** (격자 시각화) |
| 랙 | **장비 배치도** (U 다이어그램) |

## 3. 전산실 뷰 — 랙 배치도

### 3.1 시각화

전산실 내 랙을 격자로 배열. `Room.racks_per_row`(신규 필드, 기본 6)로 한 행 당 랙 수 결정.

```
┌──────────────────────────────────────────────┐
│  전산실A  (racks_per_row: 4)                  │
│                                              │
│  [랙-01]  [랙-02]  [랙-03]  [랙-04]          │
│  12/42U   38/42U   0/42U    22/42U           │
│                                              │
│  [랙-05]  [랙-06]                             │
│  42/42U   10/42U                              │
└──────────────────────────────────────────────┘
```

- 각 랙 카드: 랙명, 사용률(사용U/전체U), 사용률 바
- 빈 랙은 회색, 높사용률은 경고색

### 3.2 드래그 재배치

- HTML5 Drag & Drop으로 랙 카드 순서 변경
- 드래그 완료 시 `Rack.sort_order` PATCH
- Rack 모델에 `sort_order`(int, default 0) 필드 추가

### 3.3 액션

- "랙 추가" 버튼 → 모달 (기존 modal-rack 재활용)
- 랙 카드 클릭 → 트리에서 해당 랙 선택 → 장비 배치도로 전환
- 랙 카드 우클릭 또는 ... 메뉴 → 수정/삭제

## 4. 랙 뷰 — 장비 배치도

### 4.1 시각화

세로 U 다이어그램. 랙의 `total_units` 기준으로 U 슬롯 표시.

```
┌─── 랙-01 (42U) ─────────────┐
│ 42 │                         │
│ 41 │                         │
│ 40 │ ┌─────────────────────┐ │
│ 39 │ │ 서버A (2U)          │ │
│ 38 │ └─────────────────────┘ │
│ 37 │                         │
│ ...│                         │
│ 22 │ ┌─────────────────────┐ │
│ 21 │ │ 스위치B (1U)        │ │
│ 20 │ └─────────────────────┘ │
│ ...│                         │
│  1 │                         │
├────┤                         │
│미배치│ 장비C, 장비D           │
└─────────────────────────────┘
```

- U 번호는 라벨 기준 설정에 따라 start(하→상) 또는 end(상→하) 표시
- 장비 블록: 자산명 + size_unit으로 높이 결정
- 빈 U: 비어 있는 슬롯으로 표시
- 미배치: `rack_start_unit`이 null인 장비는 하단 "미배치" 영역에 목록 표시
- 장비 블록 색상: 환경(prod/dev/staging) 또는 상태(active/planned)별 구분

### 4.2 드래그 배치

- 미배치 장비 → 빈 U 슬롯으로 드래그 → `rack_start_unit`/`rack_end_unit` 자동 계산 후 PATCH
- 배치된 장비 → 다른 빈 U로 드래그 → 위치 변경
- 배치된 장비 → 미배치 영역으로 드래그 → U 위치 해제 (null)
- 충돌 검사: 놓으려는 위치에 `size_unit` 만큼의 연속 빈 U가 있는지 확인
- 드래그 중 놓을 수 없는 위치는 시각적으로 표시 (빨간 테두리 등)

### 4.3 액션

- 장비 블록 클릭 → 자산 상세로 이동 (또는 미니 팝오버)
- "장비 배치" 버튼 → 현재 고객사 자산 중 이 랙에 배치되지 않은 장비 목록에서 선택

## 5. 데이터 모델 변경

### 5.1 Room (변경)

```
rooms
├── ... (기존 필드)
├── racks_per_row (int, default 6) ─── 전산실 뷰 격자 열 수
```

### 5.2 Rack (변경)

```
racks
├── ... (기존 필드)
├── sort_order (int, default 0) ─── 전산실 내 배치 순서
```

### 5.3 Asset (변경)

```
assets
├── ... (기존 필드)
├── rack_start_unit (int, nullable) ─── 랙 내 시작 U 위치
├── rack_end_unit (int, nullable) ─── 랙 내 끝 U 위치
```

기존 `rack_unit`(텍스트) 필드는 하위호환으로 유지하되, 신규 입력은 정수 필드를 사용한다. 마이그레이션 시 파싱 가능한 기존 값은 자동 변환.

### 5.4 ContractPeriod (변경)

```
contract_periods
├── ... (기존 필드)
├── rack_label_base (str 10, default "start") ─── "start" 또는 "end"
```

## 6. API 변경

### 6.1 신규/변경 엔드포인트

| 엔드포인트 | 변경 |
|-----------|------|
| `PATCH /api/v1/racks/{id}` | `sort_order` 필드 추가 |
| `PATCH /api/v1/assets/{id}` | `rack_start_unit`, `rack_end_unit` 필드 추가 |
| `GET /api/v1/racks/{id}/assets` | **신규** — 해당 랙의 장비 목록 (rack_id 기준 필터) |
| `PATCH /api/v1/racks/{id}/reorder` | **신규** — 벌크 sort_order 업데이트 `[{id, sort_order}, ...]` |
| `PATCH /api/v1/contract-periods/{id}` | `rack_label_base` 필드 추가 |

### 6.2 GET /api/v1/racks/{id}/assets 응답

```json
[
  {
    "id": 1,
    "asset_name": "서버A",
    "hostname": "srv01",
    "rack_start_unit": 38,
    "rack_end_unit": 40,
    "size_unit": 2,
    "status": "active",
    "environment": "prod"
  }
]
```

## 7. 프론트엔드 구조

### 7.1 파일

- `infra_physical_layout.html` — 전면 재작성 (트리 + 콘텐츠 패널)
- `infra_physical_layout.js` — 전면 재작성 (트리 빌드, 뷰 전환, 드래그 로직)
- `infra_common.css` — 랙 카드, U 다이어그램, 드래그 스타일 추가

### 7.2 드래그 구현

**랙 드래그 (전산실 뷰):**
- `draggable="true"` on 랙 카드
- `dragstart`: 드래그 중인 랙 ID 저장
- `dragover`: 놓을 위치 하이라이트
- `drop`: 순서 재계산 → `PATCH /api/v1/racks/{id}/reorder`

**장비 드래그 (랙 뷰):**
- `draggable="true"` on 장비 블록 + 미배치 아이템
- `dragover` on U 슬롯: `size_unit` 만큼 연속 빈 U가 있는지 검사, 가능하면 초록 하이라이트
- `drop` on U 슬롯: `rack_start_unit = 해당 U`, `rack_end_unit = 해당 U + size_unit - 1` → PATCH
- `drop` on 미배치 영역: `rack_start_unit = null`, `rack_end_unit = null` → PATCH

### 7.3 라벨 기준 토글

- 페이지 상단에 "U 라벨 기준" 토글: `▽ start(하→상)` / `△ end(상→하)`
- 기본값: 프로젝트의 `rack_label_base` 설정
- 토글 변경 시 다이어그램 U 번호만 재렌더 (데이터 변경 없음)
- 토글 값은 페이지 내 임시 상태, 프로젝트 설정은 별도 저장

## 8. 스코프 외

- 전력/네트워크 케이블 시각화
- 발열/전력 용량 관리
- 전산실 평면도 (실제 도면 기반)
- 랙 전면/후면 구분
