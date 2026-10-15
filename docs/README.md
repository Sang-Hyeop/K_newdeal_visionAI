# 현재 프로젝트 문서

현재 발표 영상은 1~5번이며 실행은 프로젝트 최상위의 `handoff.py`로 통일합니다. 이 폴더는 현재 운영·판정 기준과 최종 검증 근거만 보관합니다. 이전 리뷰·학습 실험·초안은 삭제했으며 Git 이력에서 확인할 수 있습니다.

## 먼저 읽을 문서

- [설치·실행·팀원 연동](github-team-quickstart.md)
- [영상 1~5 기능과 판정 기준](demo-feature-show-plan-2026-10-07.md)
- [이벤트·관측 출력 계약](detection-output-contract.md)
- [백엔드 API 명세](../backend_v1/API_SPEC.md)

## 개발·라벨링 기준

- [공통 감지 코드 구성](../src/README.md)

- [감지 담당 목표와 범위](detection-goal.md)
- [라벨링 기준](labeling-policy-v2.md)
- [사용자 확인 설비 오라벨 수정과 재학습 과제](equipment-annotation-correction-2026-10-13.md)
- [ROI·상태 표시 문구](roi-wording-2026-10-07.md)
- [평가 체크리스트](evaluation-checklist.md)
- [Git 협업](CONTRIBUTING.md), [체크포인트 정책](checkpoint-policy.md)

## 현재 결과와 검증

- [현재 작업 상태·남은 과제](progress-2026-10-14.md)
- [5번 차량·탑승자 처리 방법과 한계](video5-vehicle-rider-recovery-2026-10-14.md)
- [GitHub 설치 검증](checkpoints/2026-10-14/github-runtime-verification.json)
- [정리 후 실행 검증](checkpoints/2026-10-14/five-video-cleanup/verification.json)

모델·원본·설정·결과의 실제 경로는 [실행 인덱스](../configs/team-runtime-index.json)가 기준입니다. `python handoff.py list`로 영상별 연결을 확인합니다. 날짜가 포함된 문서라도 위 목록에 남긴 문서는 현재 참조 문서입니다. 날짜별 진행 일지·실패 실험을 계속 새 문서로 추가하지 말고 해당 문서를 갱신합니다.
