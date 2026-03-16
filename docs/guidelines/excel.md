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
| ③ Actual | `실적` | 기간ID, 매출/매입, 거래처명 | `POST /api/v1/excel/import/transaction-lines` |

- 값 정규화: 진행단계 소수 → 퍼센트 자동 변환 (`0.7`→`70%` 등), 사업유형 대소문자 정규화
- 허용 사업유형: `ContractTypeConfig` 테이블에서 동적 조회 (기본: MA, SI, HW, TS, Prod, ETC)
- 하위 호환: 기존 템플릿의 "구분" 컬럼 헤더도 자동으로 "사업유형"으로 인식
- 전체 Import는 시트 간 연결에 `연도 + 번호`를 사용한다.
- 전체 Import의 overwrite/skip 대상 탐지는 `연도 + 사업명` 기준으로 수행한다.
- 같은 `연도 + 사업명` 조합이 업로드 파일 내부에 중복되거나 기존 DB에 2건 이상 있으면 자동 선택하지 않고 validation error로 중단한다.
