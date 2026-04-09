# Excel 연동 작업 지침

> Excel Import/Export 기능 작업 시 참조.

---

## 기본 규칙

- **업로드**: 지정된 템플릿 형식만 허용. 형식 오류 시 명확한 오류 메시지 반환.
- **다운로드**: 현재 그리드 조회 결과를 그대로 Excel로 내보낸다.
- 날짜, 금액 셀 형식을 Excel에서도 유지한다 (텍스트로 저장 금지).
- 업로드 전 유효성 검사를 서버에서 수행하고, 오류 행을 명시하여 반환한다.
- 업로드 오류 응답은 기존 문자열 목록(`errors` / `detail`)을 유지하되, 가능하면 `sheet`, `row`, `column`, `code`를 담은 구조화 목록(`error_details`)도 함께 반환한다.
- Excel 처리 라이브러리: `openpyxl` (파일 생성/읽기), `pandas` (데이터 처리).
- 파일 업로드 시 확장자 및 MIME 타입을 검증한다 (`.xlsx`만 허용).
- 이 문서는 공통 원칙 + 현재 운영 중인 Excel 플로우를 다룬다. 회계/인프라 규칙이 커져서 한 파일이 빠르게 길어지면 `excel-accounting.md`, `excel-infra.md`로 분리하고 이 문서에는 공통 규칙과 문서 지도만 남긴다.
- 분리 트리거 예시:
  - 회계/인프라 중 한쪽만의 규칙 수정이 반복되어 서로 무관한 변경이 잦을 때
  - 시트 정의, 열 매핑, 중복 판정 규칙이 문서 절반 이상을 차지할 때
  - 한쪽 플로우 변경이 다른 쪽 리뷰 가독성을 계속 방해할 때

## Import 3단계

| 단계 | 시트 | 키 컬럼 | API |
| ------ | ------ | --------- | ----- |
| 사전검사 | `영업기회`(+선택 시트 포함) | 업로드 전체 | `POST /api/v1/excel/validate` |
| ① 사업 | `영업기회` | 연도, 번호, 사업유형, 사업명, 진행단계 | `POST /api/v1/excel/import` |
| ② Forecast | `월별계획` | 기간ID(ContractPeriod.id) | `POST /api/v1/excel/import/forecast` |
| ③ Actual | `실적` | 기간ID, 매출/매입, 업체명 | `POST /api/v1/excel/import/transaction-lines` |

- 값 정규화: 진행단계 소수 → 퍼센트 자동 변환 (`0.7`→`70%` 등), 사업유형 대소문자 정규화
- 허용 사업유형: `ContractTypeConfig` 테이블에서 동적 조회 (기본: MA, SI, HW, TS, Prod, ETC)
- 하위 호환: 기존 템플릿의 "구분" 컬럼 헤더도 자동으로 "사업유형"으로 인식
- 전체 Import는 시트 간 연결에 `연도 + 번호`를 사용한다.
- 전체 Import의 overwrite/skip 대상 탐지는 `연도 + 사업명` 기준으로 수행한다.
- 같은 `연도 + 사업명` 조합이 업로드 파일 내부에 중복되거나 기존 DB에 2건 이상 있으면 자동 선택하지 않고 validation error로 중단한다.

## 인프라모듈 Excel Import/Export

### Import

- **scope**: 고객사(`partner_id`) 단위. 라우터는 `partner_id`를 Form 파라미터로 수신.
- **API**: `POST /api/v1/infra-excel/import/preview` (파싱 프리뷰), `POST /api/v1/infra-excel/import/confirm` (DB 저장)
- **도메인**: `inventory` (자산), `subnet` (IP 대역), `portmap` (포트맵)
- **중복 처리**: `on_duplicate` 파라미터로 `skip`(기본) 또는 `overwrite`
- **중복 판정**: 자산은 `asset_name` 기준(업체 범위), 서브넷은 `subnet` 기준, 포트맵은 항상 신규 생성
- **샘플 양식**: `GET /api/v1/infra-excel/template/{domain}`

### 제품 카탈로그 Import (글로벌)

- **scope**: 글로벌 (partner_id 불필요). 제품 카탈로그는 업체에 종속되지 않음.
- **도메인**: `spec` (제품+HW스펙), `eosl` (EOS/EOSL 날짜 업데이트)
- **SPEC 시트**: Row 1=헤더, Row 2+=데이터. 컬럼: 제조사, 모델명, 제품유형, 분류, Size(U), 폭/높이/깊이(mm), 무게(kg), 전원수량/유형/W, CPU/메모리/처리량 요약, OS/FW, 스펙URL, 참조URL
- **EOSL 시트**: 제조사, 모델명, EOS일자, EOSL일자, EOSL비고. 기존 등록 제품에 날짜 업데이트. 미등록 제품은 스킵.
- **중복 판정**: vendor+name 기준 (DB 유니크 제약과 동일)
- **Import 동작**: SPEC은 product_catalog + hardware_specs upsert. EOSL은 기존 제품 날짜 update only.
- **샘플 양식**: `GET /api/v1/infra-excel/template/spec`, `GET /api/v1/infra-excel/template/eosl`

### 제품 카탈로그 Import 확장 계획

- 현재 구현된 Import는 `spec`, `eosl`만 지원하며 사실상 하드웨어 중심이다.
- `software`, `model`은 현재 카탈로그 상세 화면 수동 입력이 기준이다.
- 후속으로 kind별 입력 포맷을 분리할 때는 기존 `SPEC` 시트에 모든 속성을 섞지 않는다.

#### 예정 포맷: `SOFTWARE`

- 시트명 후보: `SOFTWARE`
- 핵심 컬럼:
  - 제조사, 제품명, 버전, 상위분류, 자산유형, 분류
  - 에디션, 라이선스유형, 라이선스단위, 배포형태, 실행환경, 지원벤더
  - 참조URL, 비고
- 저장 대상:
  - `product_catalog`
  - `software_spec`

#### 예정 포맷: `MODEL`

- 시트명 후보: `MODEL` 또는 `LLM`
- 핵심 컬럼:
  - 제공자, 모델명, 버전, 상위분류, 자산유형, 분류
  - 모델계열, 모달리티, 배포범위, 컨텍스트윈도우, 엔드포인트형식
  - 참조URL, 기능비고
- 저장 대상:
  - `product_catalog`
  - `model_spec`

#### 확장 규칙

- kind별 importer는 분리한다.
- preview/confirm/audit 흐름은 공통으로 유지한다.
- 새 포맷이 들어와도 `input/spec.xlsx`의 `SPEC/EOSL`는 하드웨어 정제 기준으로 유지한다.

## 분류체계 연동 원칙

- 자산 분류체계는 프로젝트별 override를 수용하므로, Import/Export 양식에 그대로 연결할 때는 먼저 **양식 계약**을 확정해야 한다.
- 현재 단계에서는 자산 화면에서만 최종 분류(leaf node) 선택을 연결했고, Excel 쪽은 아래를 별도 설계 후 구현한다.
  - export에서 분류를 어떤 컬럼 구조로 노출할지
  - import에서 전체 경로를 받을지, 최종 분류만 받을지
  - 레벨 alias(`대구분/중구분/소구분`)를 표시용으로만 쓸지, 검증 키로도 쓸지
  - 미존재 분류를 오류로 막을지, 수동 매핑 단계를 둘지
- 분류체계 export/import 계약이 정해지기 전에는 자산 Excel 양식에 임시 분류 컬럼을 추가하지 않는다.

### Export

- **scope**: 업체(`partner_id`) 단위. 옵션 `project_id`로 프로젝트 자산만 필터 가능.
- **API**: `GET /api/v1/infra-excel/export?partner_id=N&project_id=M`
- **시트 구성**: `01. Inventory`, `05. 네트워크 대역`, `03. Portmap`
- 프로젝트 필터 적용 시 Inventory 시트만 `PeriodAsset` N:M 기반 필터링. IP 대역/포트맵은 업체 전체.
