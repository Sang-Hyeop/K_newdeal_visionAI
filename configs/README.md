# 현재 설정

발표 번호 1~5의 연결 기준은 team-runtime-index.json입니다. demo-videos.json은 원본 해시, github-runtime.json은 배포 자료 해시입니다.

카메라별 ROI·판정은 cameras/, 객체 후처리는 video*-object-review.json, 최종 PPE 경로는 demo-ppe-model.json 및 ppe-final-model.json입니다. demo-scenarios.json과 video*-object-review.json의 번호는 과거 내부 번호이므로 직접 실행 번호로 사용하지 않습니다. 실행은 handoff.py로 통일합니다.

review/demo-adaptation-v1.json과 review/full-scene-v1.json은 정답 검증에서 참조합니다. 제거하지 않습니다. 일부 라이브러리의 선택 기능에 대한 설정은 남지만 현재 확정 실행 경로는 team-runtime-index.json만 기준으로 합니다.
