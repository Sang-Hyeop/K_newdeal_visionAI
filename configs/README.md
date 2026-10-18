# 현재 설정

원본 파일·발표·실행 번호는 모두 1~6입니다. 기존 demo-videos.json은 1~5번 입력을 보관하고 6번은 review/fire-current.json에 기록합니다. team-runtime-index.json은 현재 모델·코드·결과의 연결 기준, demo-videos.json은 원본 해시, github-runtime.json은 배포 자료와 현재 로컬 결과의 해시 기준입니다.

- cameras/: 현재 ROI·판정 및 거리 계산 기준. forward-proximity.json은 5번 근접 판정의 공통 기반으로도 사용합니다.
- video1·3·4·5-object-review.json: 해당 영상의 객체 검수 설정. 2번은 전용 실행기를 사용합니다.
- demo-scenarios.json: 영상별 활성 기능.
- demo-object-model.json: 현재 객체 모델 묶음과 해시.
- demo-ppe-model.json, ppe-final-model.json: 현재 PPE 실행 모델·정책.
- ppe-user-approved-policy-2026-10-15.json: 현재 기본 실행에서 사용하는 사용자 확정 PPE 정책. 임의 변경하지 않습니다.
- review/demo-adaptation-v1.json, review/full-scene-v1.json: 학습 정답·설비 오라벨 회귀 검증 원천이므로 보존합니다.

구 7개 영상의 중복 설정과 미사용 선택 기록은 삭제했습니다. Release ZIP 내부 archive_path는 배포 호환성을 위해 유지하며 현재 로컬 경로와 구분합니다.

승인 파일의 runtime_implementation_status는 승인 당시 기록이며, 실제 적용 상태·상반신 검색 범위는 demo-ppe-model.json의 runtime이 기준입니다. 숫자 임곗값은 변경하지 않았습니다.

review/ppe-balanced-800.json은 현재 PPE의800장 선정·학습·전체영상 비교·선택 가중치SHA 기록입니다. 4회차 학습 후 영상 기준으로1회차를 선택했습니다.

review/ppe-balanced-1200.json은 새원본400장을 추가한600/600 학습 기록입니다. 이미지 지표는 개선됐으나 실제3/5번 회귀로 가중치를 채택하지 않았습니다. 현재 기본 모델은800장 학습 결과입니다.

final-model-lock.json은 2026-10-17 사용자 확정에 따른 7개 모델·모델 보조 파일·승인 정책의 SHA와 6개 원본/최신 결과 스냅샷입니다. review/의800/1200/1600/1000장 및 화재 비교 JSON은 모델 선정의 근거이므로 실행 대안으로 취급하거나 삭제하지 않습니다.

학습 자료는 data/ppe·forklift·fire·shared로 정리했습니다. data-catalog.json은 실제 폴더 수량·이전→현재 경로·참조 검증 결과의 기준입니다. final-model-lock.json은 모델 확정 당시 스냅샷이며 학습폴더 이동으로 가중치/정책을 바꾸지 않았습니다. 과거 기록에 들어있는 manifest 해시는 당시 스냅샷이며 이번 경로 메타데이터 수정 전후를 구분합니다.
