# Architecture Guard

목표: 프로젝트 구조 붕괴 방지

---

## 1. 책임 분리

프로젝트는 다음 레이어를 분리한다.

- **Interface** — UI, API 엔드포인트, CLI (입출력 변환만)
- **Application Logic** — 비즈니스 규칙, 유효성 검사, 워크플로우
- **Domain Model** — 엔티티, 값 객체, 도메인 규칙
- **Data Access** — DB 쿼리, 외부 API 호출, 파일 I/O

레이어 간 의존 방향: Interface → Application → Domain ← Data Access

---

## 2. 비즈니스 로직 위치

비즈니스 로직은 Application Logic 레이어에 집중한다.

다음 위치에 비즈니스 로직이 있으면 구조 문제다.

- UI / template
- controller / router
- 데이터 접근 레이어

router는 요청 파싱 → 서비스 호출 → 응답 반환만 한다.

---

## 3. 순환 의존성 금지

모듈 간 순환 import는 허용하지 않는다.
순환이 발생하면 책임 분리가 잘못된 신호다.

해결 방법:
- 공통 의존 모듈 추출
- 의존 방향 역전 (인터페이스/프로토콜)
- TYPE_CHECKING 분기 (타입 힌트 전용)

---

## 4. 단일 책임

하나의 모듈은 하나의 책임을 가진다.

다음은 구조 문제 신호다.

- 함수가 50줄을 넘김
- import가 10개를 넘김
- 하나의 클래스가 여러 역할 수행
- 파일명으로 역할을 설명할 수 없음
