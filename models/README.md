# 모델 가중치

현재 모델 구성은 configs/demo-object-model.json, configs/demo-ppe-model.json, configs/demo-hood-model.json에 있습니다. 실파일 7개와 SHA-256은 docs/checkpoints/2026-10-07/model-share-manifest.json을 확인합니다. 후드 v1을 유지하며 hoodie_context_v2는 미채택 실험입니다.

.pt는 Git에서 제외되고 별도로 공유합니다. scripts/pack_demo_models.py로 채택된 모델을 묶습니다. 이전 모델은 성능 비교·복구용으로 보존하며 자동 삭제하지 않습니다.
