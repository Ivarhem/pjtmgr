# Legacy Classification Template

이 폴더는 기존 `분류체계 노드 트리 + 카탈로그/자산 연동` 구조를 나중에 다시 참고하거나 재활용할 수 있도록 보관한 스냅샷이다.

운영 경로와 분리된 참고용 복사본이며, 여기의 파일은 런타임에서 직접 import되지 않는다.

## 포함 범위

- 카탈로그 트리 UI
  - [infra_product_catalog.js](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/static/js/infra_product_catalog.js)
  - [product_catalog.html](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/templates/product_catalog.html)
- 글로벌/프로젝트 분류체계 UI
  - [system.js](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/static/js/system.js)
  - [system.html](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/templates/system.html)
  - [infra_project_classifications.js](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/static/js/infra_project_classifications.js)
  - [infra_project_classifications.html](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/templates/infra_project_classifications.html)
- 자산/카탈로그 연동 로직
  - [infra_assets.js](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/static/js/infra_assets.js)
  - [asset_service.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/services/asset_service.py)
  - [product_catalog_service.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/services/product_catalog_service.py)
- 분류체계 서비스/라우터/모델
  - [classification_service.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/services/classification_service.py)
  - [classification_nodes.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/routers/classification_nodes.py)
  - [classification_schemes.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/routers/classification_schemes.py)
  - [classification_node.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/models/classification_node.py)
  - [classification_scheme.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/models/classification_scheme.py)
  - [classification_node.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/schemas/classification_node.py)
  - [classification_scheme.py](/c:/Users/JBM/Desktop/projmgr/docs/inframgr-reference/legacy-classification-template/app/modules/infra/schemas/classification_scheme.py)

## 용도

- 예전 트리형 분류 UX를 다시 참고할 때
- 속성 기반 레이아웃 UI와 비교할 때
- 노드 기반 분류 로직을 특정 화면에서 재활용할 때

## 주의

- 이 폴더의 파일은 스냅샷이다.
- 운영 코드 변경이 자동 반영되지 않는다.
- 실제 재사용 시에는 필요한 부분만 골라서 새 구조에 맞게 옮기는 것을 전제로 한다.
