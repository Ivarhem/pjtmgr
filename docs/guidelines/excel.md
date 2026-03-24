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

### Export

- **scope**: 업체(`partner_id`) 단위. 옵션 `project_id`로 프로젝트 자산만 필터 가능.
- **API**: `GET /api/v1/infra-excel/export?partner_id=N&project_id=M`
- **시트 구성**: `01. Inventory`, `05. 네트워크 대역`, `03. Portmap`
- 프로젝트 필터 적용 시 Inventory 시트만 `PeriodAsset` N:M 기반 필터링. IP 대역/포트맵은 업체 전체.
