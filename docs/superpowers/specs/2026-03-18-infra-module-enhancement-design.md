# 인프라모듈 고도화 설계

> 작성일: 2026-03-18
> 상태: 승인 대기
> 선행 완료: 모듈화 마이그레이션 (`2026-03-18-modular-migration-design.md`)

---

## 1. 목적

인프라모듈의 CRUD 기반 구조를 실무 업무 플로우에 맞게 고도화한다.

- 프로젝트 중심의 기술 인벤토리 관리 화면 체계 확립
- 영업모듈과의 연결 (ProjectContractLink)
- 프로젝트 횡단 인벤토리 검색
- 운영 현황판 (대시보드)
- 모듈별 감사 로그 분리

**범위 외**: 태스크 관리, 간트 차트, 메시징, 알림, 일정 관리, 협업 기능

---

## 2. 실제 사업 구조와 엔티티 관계

### 사업 구조

```
고객사 (Customer, 공통모듈)
  └── 프로젝트 (Project, 인프라모듈) — 기술 수행 단위
        ├── 자산, IP, 포트맵, 정책, 담당자
        └── 연결된 계약들 (ProjectContractLink, 공통모듈)
              ├── SI 본계약 (Contract → Period Y26)
              ├── HW 구매계약 (Contract → Period Y26)
              └── 유지보수계약 (Contract → Period Y26-Y28)
```

### 관계 정의

- **Customer : Project = 1 : N** — 고객사별 여러 프로젝트
- **Project : Contract = 1 : N** — 하나의 프로젝트에 여러 계약 (유지보수 패턴)
- 연결은 `ProjectContractLink` 매핑 테이블 (common 소유)로 처리
- Contract 없는 Project, Project 없는 Contract 모두 허용 (nullable)

### ProjectContractLink 모델 (common 모듈)

```python
class ProjectContractLink(TimestampMixin, Base):
    __tablename__ = "project_contract_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))
    is_primary: Mapped[bool] = mapped_column(default=False)  # 주 계약 표시
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "contract_id"),)
```

- `ForeignKey`는 테이블명 문자열 참조 → infra/accounting 모델 import 불필요
- **모듈 import 규칙 완전 준수** (common이 소유, DB 레벨 FK만 사용)
- 양쪽 모듈 중 하나만 활성이면 테이블은 비어있을 뿐 (무해)

---

## 3. 화면 구조와 메뉴 설계

### 전체 네비게이션

```
[공통]
  거래처

[영업관리] (accounting 활성 시)
  내 사업
  사업관리
  대시보드
  보고서

[프로젝트관리] (infra 활성 시)
  프로젝트                ← 인프라 홈
  인벤토리
    ├── 자산 검색
    ├── IP 검색
    └── 포트맵 검색
  정책 관리
  현황판

[관리]
  사용자
  시스템설정
```

### 3.1 프로젝트 목록 (인프라 홈)

AG Grid 기반 프로젝트 목록. 고객사 필터/그룹핑 포함.

| 컬럼 | 설명 |
|------|------|
| 프로젝트코드 | 클릭 시 프로젝트 상세로 이동 |
| 프로젝트명 | |
| 고객사 | 필터/그룹핑 가능 |
| 상태 | planned/active/completed |
| 기간 | 시작일 ~ 종료일 |
| 자산 수 | 요약 |
| 단계 | 현재 활성 단계 표시 |

### 3.2 프로젝트 상세 (핵심 화면)

프로젝트 선택 시 진입. 탭 구조로 모든 하위 정보를 관리.

```
┌─────────────────────────────────────────────────────┐
│ [프로젝트명]  고객사: OO전자  상태: 구축 진행 중     │
│ 기간: 2026-01 ~ 2026-12                              │
├──────┬──────┬──────┬──────┬──────┬────────┬────────┤
│ 개요 │ 자산 │ IP   │포트맵│ 정책 │담당자  │ 변경이력│
└──────┴──────┴──────┴──────┴──────┴────────┴────────┘
```

#### 개요 탭

**요약 카드 영역:**

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ 자산      │ │ IP 할당   │ │ 정책 준수 │ │ 산출물    │
│ 127 대    │ │ 342/500  │ │ 89%      │ │ 8/12 완료 │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

**프로젝트 단계 추적:**

```
분석 ──●── 설계 ──●── 구축 ──◐── 시험 ──○── 안정화 ──○
       ✓         ✓       진행중
```

- 각 단계 클릭 시 산출물 목록 표시
- 산출물별 제출 여부 체크박스
- 단계 상태: not_started / in_progress / completed

**연결된 계약 (양쪽 모듈 활성 시에만 표시):**

| 계약코드 | 계약명 | 유형 | 상태 | 주계약 |
|----------|--------|------|------|--------|
| C-2026-001 | OO전자 SI본계약 | SI | 계약완료 | ✓ |
| C-2026-030 | OO전자 유지보수 | MA | 90% | |

- 계약 연결/해제 기능
- 계약코드 클릭 시 영업모듈 사업 상세로 이동

#### 자산 탭

AG Grid: 유형/역할/환경/상태 필터, 장비 상세 스펙(40+ 컬럼).
CRUD + Excel Import/Export.

#### IP/네트워크 탭

상단: 서브넷 목록 Grid
하단: 선택된 서브넷의 IP 할당 목록 (또는 전체 IP)
IP 중복 검증 자동 실행.

#### 포트맵 탭

출발/도착 자산, 포트, 프로토콜, 케이블 정보.
AG Grid + CRUD.

#### 정책 탭

좌측: 적용 대상 정책 정의 목록
우측: 선택된 정책의 자산별 적용 상태 매트릭스 (compliant/non_compliant/exception/not_checked)
증적 기록(evidence_note) 입력 가능.

#### 담당자/업체 탭

거래처(공통 Customer) + AssetContact 매핑 관리.
자산별 담당자 배정/해제.

#### 변경이력 탭

해당 프로젝트 범위의 감사 로그 (module='infra' 필터).

### 3.3 인벤토리 (프로젝트 횡단 조회)

모든 배포(본사 + standalone)에 포함.

| 화면 | 내용 |
|------|------|
| 자산 검색 | 전체 자산 AG Grid. 프로젝트/고객사/유형/역할 필터 |
| IP 검색 | 전체 IP AG Grid. 프로젝트/서브넷/대역 필터 |
| 포트맵 검색 | 전체 포트맵 AG Grid. 프로젝트/자산 필터 |

프로젝트 상세의 각 탭과 동일한 Grid이되, **프로젝트 필터가 추가**된 형태.

### 3.4 정책 관리

| 화면 | 내용 |
|------|------|
| 정책 정의 관리 | PolicyDefinition CRUD. 프로젝트 무관, 전사 정책 기준. ISO27001/NIST/ISMS-P 참조 |
| 정책 적용 현황 | 프로젝트별 준수율 요약. 프로젝트 선택 시 상세 매트릭스 |

### 3.5 현황판 (대시보드)

KPI 측정용이 아닌 **운영 현황 파악** 용도.

```
┌─ 프로젝트 현황 ────────────────────────────────────┐
│                                                      │
│  [프로젝트 단계 요약]                                │
│  분석: 0건 │ 설계: 1건 │ 구축: 3건 │ 안정화: 1건    │
│                                                      │
│  [미제출 산출물 알림]                                │
│  - OO전자 IDC: 구축 단계 산출물 3건 미제출           │
│  - △△은행 클라우드: 설계 단계 산출물 1건 미제출     │
│                                                      │
├─ 자산/정책 현황 ────────────────────────────────────┤
│                                                      │
│  [프로젝트별 요약 Grid]                              │
│  프로젝트    │ 자산 │ IP할당률 │ 정책준수율 │ 단계   │
│  OO전자 IDC  │ 127  │ 68%     │ 89%       │ 구축   │
│  △△은행     │  45  │ 92%     │ 75%       │ 설계   │
│                                                      │
├─ 정책 미준수 항목 ──────────────────────────────────┤
│                                                      │
│  [non_compliant + not_checked 항목 목록]             │
│  프로젝트 │ 자산명    │ 정책          │ 상태          │
│  OO전자   │ WEB-01   │ 패스워드 정책  │ non_compliant │
│  OO전자   │ DB-03    │ 접근제어 정책  │ not_checked   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

핵심 정보:
- 프로젝트별 단계 진행 현황 (어디까지 왔는지)
- 미제출 산출물 (뭐가 빠졌는지)
- 자산/IP/정책 수치 요약 (규모 파악)
- 정책 미준수/미점검 항목 (즉시 조치 필요한 것)

---

## 4. 감사 로그 모듈 분리

### AuditLog 모델 변경

기존 AuditLog에 `module` 필드 추가:

```python
module: Mapped[str | None] = mapped_column(String(20), nullable=True)
# "common", "accounting", "infra"
```

### 조회 분리

- 영업모듈 감사 로그: `module='accounting'` 필터
- 인프라모듈 변경이력 탭: `module='infra'` + project 범위 필터
- 관리자 전체 로그: 필터 없음 (기존 audit_logs 화면)

---

## 5. 영업모듈 변경 사항 (최소)

기존 영업모듈에 대한 변경은 최소화한다:

1. **사업 상세 페이지**: "연결된 프로젝트" 섹션 추가 (인프라모듈 활성 시에만 표시)
   - ProjectContractLink를 통해 연결된 프로젝트 목록
   - 프로젝트 연결/해제 UI
   - 프로젝트명 클릭 시 인프라모듈 프로젝트 상세로 이동

2. **사업 목록**: "프로젝트" 컬럼 추가 (인프라모듈 활성 시에만, 연결된 프로젝트명 표시)

---

## 6. Standalone 배포 시 동작

| 항목 | 본사 (전체) | 현장 (common+infra) |
|------|------------|-------------------|
| 프로젝트 목록 | 전체 | export된 프로젝트만 |
| 인벤토리 검색 | 전체 횡단 | 현장 프로젝트 범위 |
| 정책 관리 | 전사 정의 | export된 정의만 |
| 현황판 | 전체 프로젝트 | 현장 프로젝트만 |
| 연결된 계약 | 표시 | 미표시 (회계모듈 비활성) |
| 거래처 관리 | 전체 | 현장에서 생성/수정 가능 |

---

## 7. 구현 우선순위

### Phase 1: 기반 (필수)

1. ProjectContractLink 모델 + migration
2. AuditLog에 module 필드 추가
3. 프로젝트 상세 화면 고도화 (탭 구조, 개요 탭 — 단계 추적/산출물 체크)
4. 네비게이션 메뉴 그룹 분리 (영업관리/프로젝트관리 시각적 구분)

### Phase 2: 핵심 화면

5. 인벤토리 횡단 조회 (자산/IP/포트맵 검색 화면)
6. 정책 관리 화면 (정의 관리 + 적용 현황)
7. 프로젝트 상세 — 연결된 계약 섹션

### Phase 3: 현황판/보고서

8. 인프라 현황판 (운영 현황 파악용)
9. 보고서 (자산 인벤토리 Export, 정책 점검 리포트)
10. 영업모듈 사업 상세에 "연결된 프로젝트" 섹션

---

## 8. 산출물 미제출 알림

- **로그인 시 알림**: 사용자가 접근 가능한 프로젝트 중, in_progress 단계에 미제출 산출물이 있으면 로그인 직후 알림 표시
- **옵션 제어**: 사용자별 설정(UserPreference)으로 알림 비활성화 가능
- 알림 형태: 현황판 상단 배너 또는 토스트. 페이지 차단(모달)은 하지 않음

---

## 9. 정책 준수율 공식

```
준수율 = compliant / (전체 적용 건수 - not_applicable) × 100
```

- `not_applicable`은 분모에서 제외
- `not_checked`는 미점검이므로 분모에 포함 (준수율 하락 요인)
- 현황판에서 프로젝트별 준수율 표시, 정책 관리 화면에서 상세 매트릭스

---

## 10. Excel Import/Export

### 참조 템플릿

`input/template.xlsx` — 실제 SI 현장에서 사용하는 실무 양식. 주요 시트:

| 템플릿 시트 | 인프라 모델 | 컬럼 수 |
|------------|------------|---------|
| `01. Inventory` | Asset | 35 (장비명세/논리구성/HW구성/자산정보) |
| `03. Portmap` | PortMap | 42 (Start/End/Cable 3영역) |
| `05. 네트워크 대역 정의` | IpSubnet | 10 (Zone/VLAN/IP/Netmask/Gateway) |
| `98. IP마스터_Hostname` | AssetIP | 19 (Hostname 기준 IP 할당) |
| `98. IP마스터_IP` | AssetIP | 21 (IP 기준 역조회) |
| `Security_Requirement` | PolicyDefinition | 10 (보안도메인/요구사항/ISO/NIST/ISMS-P) |
| `WBS` | ProjectPhase + Deliverable | 32 (단계/Task/산출물/일정) |

### Import 전략

회계모듈의 3단계 Import 패턴을 참고하되, 인프라 특성에 맞게 조정:

1. **파일 업로드** — Excel 파일 선택, 대상 프로젝트 지정
2. **시트 매핑 검증** — 템플릿 시트 자동 인식, 헤더 매칭 검증, 미매핑 컬럼 경고
3. **프리뷰 + 확인** — 파싱 결과 미리보기, 중복/오류 표시, 확인 후 저장

### Import 대상 (Phase 순서)

| 우선순위 | 대상 | 시트 |
|----------|------|------|
| Phase 1 | Asset (자산) | `01. Inventory` |
| Phase 1 | IpSubnet (네트워크 대역) | `05. 네트워크 대역 정의` |
| Phase 2 | PortMap (포트맵) | `03. Portmap` |
| Phase 2 | AssetIP (IP 할당) | `98. IP마스터_Hostname` 또는 `98. IP마스터_IP` |
| Phase 3 | PolicyDefinition (보안요건) | `Security_Requirement` |

### Export

프로젝트 단위로 동일 템플릿 형식의 Excel Export 제공. 각 시트에 해당 프로젝트의 데이터를 채워서 다운로드.

### 컬럼 매핑 (01. Inventory → Asset)

| 템플릿 컬럼 | Asset 필드 |
|-------------|-----------|
| Seq | (자동 생성) |
| 센터 | center |
| 운영구분 | operation_type |
| 장비관리번호 MID | equipment_id |
| Rack No. | rack_no |
| 랙내 위치 | rack_unit |
| 단계 | phase |
| 입고일 | received_date |
| 대분류 | category (또는 asset_type) |
| 소분류 | subcategory |
| 제조사 | vendor |
| 모델명 | model |
| Serial No. | serial_no |
| Hostname | hostname |
| 클러스터 | cluster |
| 업무명 | service_name |
| Zone | zone |
| Service IP | service_ip |
| MGMT IP | mgmt_ip |
| Size(unit) | size_unit |
| LC수량 | lc_count |
| HA수량 | ha_count |
| UTP수량 | utp_count |
| 전원수량 | power_count |
| 전원Type | power_type |
| Firmware Version | firmware_version |
| 자산 구분 | asset_class |
| 자산 번호 | asset_number |
| 도입년도 | year_acquired |
| 관리부서 | dept |
| 담당자(정) | primary_contact_name |
| 담당자(부) | secondary_contact_name |
| 유지보수업체 | maintenance_vendor |
| 비고 | note |
