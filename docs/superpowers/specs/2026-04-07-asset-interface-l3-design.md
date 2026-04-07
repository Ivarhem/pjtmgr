# Asset Interface L3 모델링 설계

> 자산 인터페이스 인스턴스 테이블 신설 및 AssetIP·PortMap 연동 전환

## 1. 목표

SSOT 관리 시스템의 핵심 연결고리로서, 자산별 인터페이스 인스턴스를 관리하고
IP 할당과 포트맵을 인터페이스 기반으로 전환한다.

### 달성 기준

- 자산별 물리/논리 인터페이스를 인스턴스 단위로 관리
- IP는 인터페이스에 할당 (자산 직접 할당 제거)
- PortMap은 인터페이스 FK로 연결 (텍스트 중복 필드 제거)
- 카탈로그 스펙에서 인터페이스 자동 생성
- IP 인벤토리 ↔ 인터페이스 ↔ 포트맵이 동일 데이터의 다른 뷰로 기능

## 2. 설계 결정 사항

| 결정 사항 | 결론 | 근거 |
|-----------|------|------|
| 모델링 수준 | L3 (풀 모델링) | 최종적으로 필요한 방향 |
| 1차 UI 범위 | physical, lag, virtual | D~G(vlan, subinterface, loopback, tunnel)는 모델 수용, UI 후순위 |
| VM ↔ 호스트 | AssetRelation(HOSTS)으로 처리 | 인터페이스 간 연결 불필요, VM은 IP 관리 목적 |
| 네이밍 | 자유 입력 + if_type enum | 벤더별 네이밍 룰 파싱은 후순위 |
| LAG 멤버십 | 단일 자산 내 parent-child | MC-LAG은 양쪽 장비 각각 LAG + PortMap으로 표현 |
| IP 할당 주체 | AssetInterface | asset_id 직접 연결 제거 |
| PortMap 전환 | 인터페이스 FK 기반, 텍스트 필드 제거 | 24개 필드 → 2개 FK |
| 외부 장비 | 자산으로 등록 + description 명시 | PortMap FK nullable 불필요 |
| 데이터 마이그레이션 | 불필요 | 제로베이스 |

## 3. 데이터 모델

### 3.1 AssetInterface (신설)

```
asset_interfaces
├── id (PK)
├── asset_id (FK → assets, CASCADE, indexed)
├── parent_id (FK → asset_interfaces, SET NULL) ─── 본딩/LAG 시 논리IF
├── hw_interface_id (FK → hardware_interfaces, SET NULL) ─── 카탈로그 스펙 원본
│
├── name (str 100) ─── "ge-0/0/1", "bond0", "ens192"
├── if_type (str 30) ─── physical, lag, vlan, subinterface, loopback, tunnel, virtual
├── slot (str 30, nullable) ─── 모듈 슬롯: "Slot1", "LC2"
├── slot_position (int, nullable) ─── 슬롯 내 포트 순서
│
├── speed (str 20, nullable) ─── "1G", "10G", "25G"
├── media_type (str 30, nullable) ─── "copper", "sfp", "sfp+", "qsfp28"
├── mac_address (str 17, nullable) ─── "AA:BB:CC:DD:EE:FF"
│
├── admin_status (str 20, default "up") ─── "up", "down"
├── oper_status (str 20, nullable) ─── "up", "down", "not_present"
├── description (text, nullable)
│
├── sort_order (int, default 0) ─── UI 정렬
├── created_at, updated_at (TimestampMixin)
│
├── UNIQUE(asset_id, name)
└── CHECK(parent_id != id)
```

**parent_id 규칙:**
- 물리IF가 LAG에 속하면 parent_id = 해당 LAG 인터페이스의 id
- 1단계 깊이만 허용 (물리 → 논리)
- LAG의 parent_id는 항상 NULL

**if_type enum 값:**
- `physical` — 고정/모듈 물리 포트
- `lag` — 본딩/LAG/Port-Channel
- `vlan` — VLAN 인터페이스 (UI 후순위)
- `subinterface` — 서브인터페이스 (UI 후순위)
- `loopback` — 루프백 (UI 후순위)
- `tunnel` — 터널 (UI 후순위)
- `virtual` — VM vNIC

### 3.2 AssetIP (변경)

```
asset_ips
├── id (PK)
├── interface_id (FK → asset_interfaces, CASCADE, indexed) ─── ★ 변경
├── ip_subnet_id (FK → ip_subnets, SET NULL, indexed)
│
├── ip_address (str 64, indexed)
├── ip_type (str 30) ─── "service", "mgmt", "vip", "secondary"
├── is_primary (bool, default false)
│
├── hostname (str 255, nullable)
├── service_name (str 200, nullable)
├── zone (str 100, nullable)
├── vlan_id (str 30, nullable)
│
├── note (text, nullable)
├── created_at, updated_at
│
└── UNIQUE(interface_id, ip_address)
```

**제거 필드:**
- `asset_id` → `interface.asset_id`로 역추적
- `interface_name` → `interface.name`
- `network`, `netmask`, `gateway` → `ip_subnet`에서 조회
- `dns_primary`, `dns_secondary` → `ip_subnet` 또는 센터 레벨

### 3.3 PortMap (변경)

```
port_maps
├── id (PK)
├── partner_id (FK → partners, indexed)
│
├── src_interface_id (FK → asset_interfaces, SET NULL) ─── ★ 변경
├── dst_interface_id (FK → asset_interfaces, SET NULL) ─── ★ 변경
│
├── protocol (str 20, nullable)
├── port (int, nullable)
├── purpose (str 255, nullable)
├── status (str 30, default "required") ─── "required", "active", "inactive"
│
├── seq (int, nullable)
├── connection_type (str 50, nullable) ─── "physical", "logical"
├── summary (str 500, nullable)
│
├── cable_no (str 100, nullable)
├── cable_request (str 200, nullable)
├── cable_type (str 30, nullable)
├── cable_speed (str 30, nullable)
├── duplex (str 30, nullable)
├── cable_category (str 50, nullable)
│
├── note (text, nullable)
├── created_at, updated_at
│
└── UNIQUE(src_interface_id, dst_interface_id, connection_type, protocol, port)
    ─── connection_type을 포함하여 물리/논리 연결 구분
    ─── 물리 연결: protocol/port NULL 허용, connection_type="physical"로 구분
    ─── 논리 연결: protocol/port로 추가 구분
```

**제거 필드 (src/dst 각 12개, 총 24개):**
- `src_asset_id`, `dst_asset_id` → `interface.asset_id`
- `src_ip`, `dst_ip` → `interface.ips`
- `src_mid`, `dst_mid` → `interface.asset.asset_code`
- `src_rack_no`, `src_rack_unit` → `interface.asset.rack`
- `src_vendor`, `src_model` → `interface.asset.vendor/model`
- `src_hostname`, `src_cluster` → `interface.asset.hostname/cluster`
- `src_slot` → `interface.slot`
- `src_port_name` → `interface.name`
- `src_service_name`, `src_zone`, `src_vlan` → `interface.ips`

## 4. 카탈로그 → 인터페이스 자동 생성

### 생성 규칙

자산 생성 시 `model_id`가 지정되면 `HardwareInterface` 목록을 조회하여 인스턴스를 생성한다.

**fixed 타입:**
```
HardwareInterface: interface_type="1GE", count=48, speed="1G"
→ AssetInterface × 48:
    name: "ge-0/0/{0~47}"
    if_type: "physical"
    speed: "1G"
    hw_interface_id: 원본 ID
    slot: NULL
```

**modular 타입:**
```
HardwareInterface: interface_type="10GE-SFP+", count=4, speed="10G", note="Slot 1"
→ AssetInterface × 4:
    name: "slot1/port{1~4}"
    if_type: "physical"
    speed: "10G"
    slot: "Slot 1"
    oper_status: "not_present"
    hw_interface_id: 원본 ID
```

### 동작 시나리오

| 시나리오 | 동작 |
|----------|------|
| 자산 생성 시 model_id 있음 | 자동 생성 제안 (확인 후 생성) |
| 자산 생성 시 model_id 없음 | 인터페이스 수동 추가만 가능 |
| 자산의 model_id 변경 | 기존 인터페이스 유지, 재생성 여부 사용자 확인 |
| 자동 생성 후 사용자 수정 | 자유 — name, slot, 추가/삭제 모두 가능 |
| 모듈 장착 | 해당 슬롯의 oper_status → "up", 필요 시 포트 추가 |

## 5. ERD 및 데이터 흐름

### 계층 구조

```
┌─────────────────────────────────────────────────────────┐
│ CATALOG LAYER (스펙)                                      │
│                                                           │
│  ProductCatalog ──1:N──→ HardwareInterface                │
│   (vendor, name)          (type, count, speed,            │
│                            capacity_type: fixed/modular)  │
└──────────┬────────────────────────┬──────────────────────┘
           │ model_id               │ hw_interface_id
           ▼                        ▼
┌──────────────────────────────────────────────────────────┐
│ INSTANCE LAYER (자산)                                      │
│                                                           │
│  Asset ──1:N──→ AssetInterface ──1:N──→ AssetIP           │
│   │              │  ├ name, if_type                        │
│   │              │  ├ slot, slot_position                  │
│   │              │  ├ speed, media_type, mac               │
│   │              │  ├ admin/oper_status                    │
│   │              │  └ parent_id (self FK → LAG)            │
│   │              │                       │                 │
│   │              │                       ▼                 │
│   │              │                   IpSubnet              │
│   │              │                                         │
│   ├ AssetRelation (HOSTS 등)                               │
│   ├ AssetRelatedPartner                                    │
│   └ center_id → Center → Room → Rack                      │
└──────────────────────┬───────────────────────────────────┘
                       │ src/dst_interface_id
                       ▼
┌──────────────────────────────────────────────────────────┐
│ CONNECTION LAYER (연결)                                    │
│                                                           │
│  PortMap                                                  │
│   ├ src_interface_id ──→ AssetInterface                    │
│   ├ dst_interface_id ──→ AssetInterface                    │
│   ├ protocol, port, status                                │
│   └ cable_no, cable_type, cable_speed                     │
└──────────────────────────────────────────────────────────┘
```

### 주요 조회 패턴

| 질문 | 조회 경로 |
|------|----------|
| 이 자산의 IP 목록 | Asset → interfaces → ips |
| 이 IP가 어느 자산/인터페이스에? | AssetIP → interface → asset |
| 이 자산의 물리 연결 | Asset → interfaces → portmaps (src or dst) |
| 이 서브넷 사용률 | IpSubnet → asset_ips → count |
| bond0 멤버는? | AssetInterface(lag) ← AssetInterface(physical).parent_id |
| 이 랙에 있는 자산들의 포트맵 | Rack → assets → interfaces → portmaps |
| 카탈로그 스펙 대비 실제 포트 수 | HardwareInterface.count vs AssetInterface(hw_interface_id=X).count |

### 화면 연동

```
IP 인벤토리 화면                자산 상세 화면              포트맵 화면
┌──────────────┐           ┌──────────────────┐      ┌──────────────┐
│ Subnet A     │           │ Server-X         │      │ Connection#1 │
│  10.1.1.0/24 │◄─────────│  ge-0/0/1        │─────►│ src: ge-0/0/1│
│  사용: 12/254 │          │   └ 10.1.1.10    │      │ dst: ge-0/0/2│
│  여유: 242   │           │  ge-0/0/2        │      │ cable: UTP-01│
└──────────────┘           │  bond0           │      └──────────────┘
                           │   └ 10.1.2.1     │
                           └──────────────────┘
```

## 6. 영향 범위

### 변경 대상 모델
- `AssetInterface` — 신설
- `AssetIP` — `asset_id` → `interface_id` 전환, 네트워크 필드 제거
- `PortMap` — src/dst 텍스트 24개 필드 제거, interface FK 추가

### 변경 대상 서비스/라우터
- `asset_ip_service` — interface 기반으로 전환
- `port_map_service` (또는 기존 라우터 내 로직) — interface FK 기반 전환
- `asset_service` — 자산 생성 시 인터페이스 자동 생성 로직 추가
- 신규: `asset_interface_service` — 인터페이스 CRUD, 본딩 관리

### 변경 대상 API
- `GET/POST /assets/{id}/interfaces` — 신규
- `GET/POST /assets/{id}/ips` — interface 경유 조회로 변경
- `GET/POST /port-maps` — interface FK 기반으로 변경
- IP 인벤토리 API — 서브넷별 사용률에 interface 정보 포함

### 변경 대상 UI
- 자산 상세 — 인터페이스 서브패널 추가 (1차: physical, lag, virtual)
- IP 관리 — 인터페이스 선택 후 IP 할당
- 포트맵 — 자산 선택 → 인터페이스 선택으로 2단계 전환
- IP 인벤토리 — 서브넷별 할당 현황에 자산/인터페이스 표시

### Asset 모델 중복 필드 정리

인터페이스 기반 전환 후 Asset 테이블의 아래 필드는 이중 저장이 되므로 제거한다:

- `service_ip`, `mgmt_ip` → AssetIP에서 is_primary + ip_type으로 조회
- `hostname` → AssetIP.hostname 또는 Asset 레벨 유지 (장비 식별자로서 의미가 다를 수 있음 — 유지)

### Alembic 마이그레이션
- `asset_interfaces` 테이블 생성
- `asset_ips` 테이블: `asset_id` 컬럼 제거, `interface_id` 추가, 네트워크 필드 제거
- `port_maps` 테이블: src/dst 텍스트 24개 컬럼 제거, `src_interface_id`/`dst_interface_id` 추가

## 7. 공통 그리드 복사/붙여넣기 컴포넌트

### 현황

- AG-Grid Community v32.0.0 사용 중
- `contract_detail.js`에 paste 핸들러 2종 존재 (forecast용, ledger용)
- `reports.js`에 HTML 테이블 copy 핸들러 존재
- **통합된 copy+paste 핸들러 없음**, 각 페이지가 개별 구현

### 목표

인터페이스/IP/포트맵 등 대량 데이터 입력이 필요한 모든 그리드에서 사용할 수 있는
공통 `addCopyPasteHandler()` 유틸리티를 `utils.js`에 구현한다.

### 기능 요구사항

| 기능 | 설명 |
|------|------|
| **다중 셀 선택** | AG-Grid range selection 또는 shift+click 기반 |
| **Ctrl+C 복사** | 선택 범위를 TSV(탭 구분) 형태로 클립보드에 복사 |
| **Ctrl+V 붙여넣기** | 현재 셀 위치부터 TSV 데이터를 editable 컬럼에 매핑 |
| **자동 행 추가** | 붙여넣기 시 데이터가 기존 행을 초과하면 새 행 자동 생성 (옵션) |
| **타입 변환** | 숫자 컬럼은 자동 파싱, select 컬럼은 값 매칭 |
| **editable 필드 필터** | readonly 컬럼은 건너뛰고 다음 editable 컬럼에 매핑 |
| **시각적 피드백** | 선택 범위 하이라이트, 붙여넣기 영역 플래시 |
| **Undo** | Ctrl+Z로 마지막 붙여넣기 일괄 되돌리기 |

### API 설계

```javascript
// utils.js에 추가
addCopyPasteHandler(gridElement, gridApi, {
  editableFields: ['name', 'speed', 'ip_address', ...],  // 대상 필드
  autoCreateRows: true,       // 행 자동 추가 여부
  onPaste: (changes) => {},   // 붙여넣기 후 콜백 (API 호출 등)
  onCopy: (data) => {},       // 복사 후 콜백
  typeMap: {                  // 컬럼별 타입 힌트
    port: 'number',
    status: { type: 'enum', values: ['up', 'down'] }
  }
});
```

### 적용 대상

1차: 인터페이스 관리 그리드, AssetIP 관리 그리드, PortMap 그리드
확장: 자산 목록, 카탈로그 목록, 서브넷 목록 등 기존 editable 그리드

### 기존 paste 핸들러 통합

- `contract_detail.js`의 `addPasteHandler()`, `addPasteHandlerLedger()` →
  새 공통 핸들러로 교체하거나, 최소한 동일 인터페이스로 정리

## 8. 후순위 항목

구현 시점은 별도 판단:

- **D~G if_type UI**: vlan, subinterface, loopback, tunnel 인터페이스 관리 화면
- **카탈로그 naming_pattern**: 벤더별 인터페이스 자동 네이밍 규칙
- **인터페이스 일괄 관리**: 그리드에서 다중 인터페이스 복사/붙여넣기
- **PortMap 케이블 vs 정책 분리**: 물리 연결과 논리 연결의 테이블 분리
- **MC-LAG 시각화**: 크로스 장비 LAG 관계 전용 뷰
