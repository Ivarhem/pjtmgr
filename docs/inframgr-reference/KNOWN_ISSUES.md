# Known Issues

> 현재는 설계/구현 준비 단계이므로, 구현 착수 전 인지된 제약과 주의사항을 기록한다.
> 수정 완료 시 해당 항목을 제거한다.

---

## 구현 상태

- 전체 도메인 백엔드 CRUD 구현 완료 (Project, Asset, ProjectPhase/Deliverable, IpSubnet, AssetIP, PortMap, Partner/Contact/AssetContact, PolicyDefinition/Assignment).
- User 관리(DB 기반 인증) 구현 완료. 부트스트랩 admin 자동 생성, 비밀번호 변경/초기화 지원.
- 프론트엔드 기반 구축 완료 (base 레이아웃, 로그인, 프로젝트 목록 AG Grid). 나머지 도메인 화면은 미구현.

## Excel Import/Export

- MVP 범위에서 제외되었다.
- 향후 추가 시 템플릿 형식, 중복 정책, 부분 실패 처리 전략을 별도 정의해야 한다.

## 감사 로그

- MVP 범위에서 제외되었다.
- 생성/수정 시점 추적만 기본 제공하고, 행 단위 변경 이력은 후속 단계에서 설계한다.

## 권한

- 초기 설계는 `admin` / `user` 2단계 기준이다.
- 자산 단위 편집 권한, 프로젝트별 읽기 범위 분리는 후속 확장 대상이다.

## 외부 연동

- CMDB, NMS, Excel, 메신저, 알림 시스템 연동은 구현하지 않는다.

## 화면 설계

- AG Grid 중심 화면은 데이터 밀도에 유리하지만 모바일 최적화 범위는 제한적일 수 있다.
