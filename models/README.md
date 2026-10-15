# 현재 발표용 모델과 후속 검토 모델

설치: `python scripts/setup_runtime.py` / 검증: `python handoff.py check --models`.

- `pilot_v16_related/person_forklift.pt`: 사람·지게차 기본.
- `demo_object_adaptation_v1/best.pt`: 시연 장면 보완.
- `pretrained/yolo26n.pt`: 사람 검출.
- `ppe_final/ppe_helmet_v6_960.pt`: 현재 최종 PPE. 같은 폴더의 config.json과 ppe_duplicate_filter.py도 필요합니다.
- `experiments/forklift_real_context_v2/weights/best.pt`: 현재 차량 검출 보완. experiments라는 폴더명과 관계없이 현재 발표 영상의 객체 검수 설정에서 사용하는 모델입니다.
- `nvidia_object_adaptation_v1/best.pt`: 차량 교차 확인.

후속 검토용 `experiments/ppe_expanded_1577/weights/best.pt`와 학습 기록도 보존합니다. 아직 발표 모델로 교체하지 않았습니다. 미채택 63장 보완 실험 모델은 삭제했습니다. 정확한 영상별 모델 목록과 해시는 configs/team-runtime-index.json 및 configs/github-runtime.json에 있습니다. 가중치는 GitHub Releases에서 배포하며 Git 이력에는 포함하지 않습니다.
