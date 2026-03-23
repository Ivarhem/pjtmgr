# 회계모듈 작업 지침

> 회계모듈(accounting) 작업 시 참조. 용어 정의와 데이터 원칙을 포함한다.

---

## 도메인 용어

| 용어 | 설명 |
| --- | --- |
| 계약 (Contract) | 수주 추진 또는 계약 완료된 사업 건 (원장의 1행) |
| 계약유형 (contract_type) | DB 동적 관리 (ContractTypeConfig 테이블). 기본: MA, SI, HW, TS, Prod, ETC |
| 진행단계 (stage) | 수주 확률: 계약완료, 90%, 70%, 50%, 10%, 실주 |
| 계획 여부 (is_planned) | 연초 보고 사업 여부 (ContractPeriod). True=계획사업, False=수시사업 |
| 실주 | stage 값. 수주 실패 건. 매출 목표 집계 시 손실 매출로 분류 |
| 계약기간 (ContractPeriod) | 계약 주기 단위 버전. 달력 연도가 아닌 계약 시작 연도 기준 |
| 담당자 (ContractContact) | Period별 영업/세금계산서 담당자. ContractPeriod 레벨에 귀속 |
| 매출처 (Period.customer) | ContractPeriod별 매출처. 미지정 시 Contract.end_customer 사용 |
| 입금 매칭 (ReceiptMatch) | Receipt를 매출 라인(TransactionLine)에 매핑. FIFO 자동(귀속기간 내) + 수동 |
| 선수금 | 입금 배분 합계 > 매출 확정 합계일 때의 초과 금액 (AR 음수) |
| GP | Gross Profit = 매출 합계 - 매입 합계 |
| GP% | GP / 매출 x 100 |
| 미수금 | 이번 달까지 도래한 매출 확정 합계 - 매칭완료(ReceiptMatch) 합계. 사업 상세 GP 요약에서는 미래 귀속월 제외. 사업 상세, 대시보드, 보고서, Excel Export 모두 동일 공식을 사용 |
| 용어 설정 (TermConfig) | 관리자 커스터마이징 가능한 UI 용어 라벨 (term_configs 테이블) |

---

## 데이터 원칙

- 계약 삭제는 **관리자(admin) 전용**. 일반 사용자는 상태를 cancelled로 변경.
- 금액은 **정수(원 단위, VAT 별도)**. 부동소수점 사용 금지.
- 월 범위는 `YYYY-MM-01` 문자열로 저장.
- `created_by`는 라우터에서 `get_current_user`를 통해 서비스로 전달.
- FIFO 자동 배분은 입금의 `revenue_month`가 속하는 **ContractPeriod 범위 내** 매출만 대상. 기간 간 배분 격리.
- 완료된 귀속기간(`is_completed`)의 데이터는 생성/수정/삭제 불가 (프론트+백엔드 이중 보호).
- 미수금은 모든 화면/보고서/Export에서 `매출 확정 - 배분완료(ReceiptMatch)` 단일 공식을 유지한다. raw `Receipt.amount`는 입금 지표로만 사용한다.
