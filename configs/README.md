# 현재 설정

원본 파일·발표·실행 번호는 모두 1~5입니다. team-runtime-index.json은 현재 모델·코드·결과의 연결 기준, demo-videos.json은 원본 해시, github-runtime.json은 배포 자료와 현재 로컬 결과의 해시 기준입니다.

- cameras/: 현재 ROI·판정 및 거리 계산 기준. forward-proximity.json은 5번 근접 판정의 공통 기반으로도 사용합니다.
- video1·3·4·5-object-review.json: 해당 영상의 객체 검수 설정. 2번은 전용 실행기를 사용합니다.
- demo-scenarios.json: 영상별 활성 기능.
- demo-object-model.json: 현재 객체 모델 묶음과 해시.
- demo-ppe-model.json, ppe-final-model.json, ppe-recall-review-policy.json: 현재 PPE 실행 모델·정책.
- ppe-user-approved-policy-2026-10-15.json: 후속 비교에서 사용할 사용자 확정 PPE 정책. 임의 변경하지 않습니다.
- review/demo-adaptation-v1.json, review/full-scene-v1.json: 학습 정답·설비 오라벨 회귀 검증 원천이므로 보존합니다.

구 7개 영상의 중복 설정과 미사용 선택 기록은 삭제했습니다. Release ZIP 내부 archive_path는 배포 호환성을 위해 유지하며 현재 로컬 경로와 구분합니다.
