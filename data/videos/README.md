# 팀 공용 확정 시연 영상 1~6

기존 7개 구성은 폐기했습니다. 1~4번 기능별·5번 통합 시연에 6번 주차장 화재를 추가한 현재 구성입니다.

1. `1_forklift_worker_collision_risk.mp4`: 사람·지게차 근접만.
2. `2_restricted_zone_intrusion.mp4`: 사람·ROI 침범·안전모 PPE.
3. `3_PPE_Helmet.mp4`: 사람·안전모 PPE만.
4. `4_hazard_zone_dwell.mp4`: 사람·체류시간만(차량 조건은 내부 유지).
5. `5_Logistics Warehouse.mp4`: 근접·ROI·체류·PPE 통합.
6. `6_parking_lot_fire.mp4`: 불꽃·반복 관측 기반 화재 의심만.

실행은 `python handoff.py run --video N`으로 통일합니다. 현재 결과는 outputs/reviews/*_latest.mp4와 outputs/events/presentationN/을 같은 경로에서 갱신합니다. `--fresh`는 신규 추론이며 기본 캐시 재생과 구분합니다.

configs/demo-videos.json은 기존1~5번 입력 해시, configs/review/fire-current.json은6번 입력 해시를 보관합니다. 전체6개 확정 스냅샷은 configs/final-model-lock.json입니다. 화재6번은 현재 로컬 실행·이벤트·백엔드·화면에 연결됐으며 기존 공개 Release에는 아직 포함하지 않았습니다.

6번은1280×720/30fps/12초 편집 영상입니다. CCTV 시계가 도약하므로 재생4초 첫 검출을 실제 화재 발생 후4초 경보로 표현하지 않습니다. 연기만으로 알리지 않고 미검출을 안전/진화완료로 판정하지 않습니다.
