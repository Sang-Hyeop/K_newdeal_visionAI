# 3번 현재 모델 비교 및 리뷰 영상

CVAT문맥 보강v2, 기존far_v4, NVIDIA적응, 기존demo-adaptation을0/4/8/12/16초 대표원본에서 비교. 모두최초부분및두차량이접촉하는장면에서미탐/합친박스한계가있다. CVAT후보는4초의별도차량제안및12초두차량을제공해3번개발리뷰경로로사용한다. 모든모델중최고의독립정답점수로선정한것은아니다.
객체명표시와PPE v6, 기존차량-차량 화면상거리판정 유지. 객체-first표시에서도차량두대의ground-band최근접점연결선·접근단계를표시한다. 미터보정없음.1·2번사람-차량 거리기준과구분. 고정ROI판정아님.
큰합친박스안의실제현재작은두제안(각parent25~85%면적,conf>=.25,서로IoU<.35,union>=parent70%)은별도후보로유지하고큰envelope는진단제안으로분리한다. 새박스를분할생성하지않고모델의실제제안만사용. 이개발휴리스틱도같은차량부분을두차량으로오인할수있어추가리뷰필요. 다른카메라에는활성화하지않았다.
전체18초/87표본:4초두차량CRITICAL,12초두차량SAFE 확인.8초는한대만보이며pairUNKNOWN.시작차량검출및일부가림/추적미확인은남아있다.최종성능완료로주장하지않는다.새학습미실행.170개자동테스트통과.
선정리뷰영상: outputs/diagnostics/video3_review_selected_v2/video3/demo.mp4
영상해시/대표검수: docs/checkpoints/2026-10-13/video3-review/verification.json
모델대표비교: outputs/diagnostics/video3_route_probe, outputs/diagnostics/video3_route_probe_nvidia
