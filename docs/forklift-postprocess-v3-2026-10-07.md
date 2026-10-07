# 지게차 실패 검수·추적 및 근접 판정 보완

모델 재학습 없이 남은 실패를 직접 검수했다. 가중치와 평가 정답은 변경하지 않았다. 전체 독립 성능이나 미탐0을 주장하지 않는다.

## 확인한 원인

기존 test50 미탐4개를 같은 가중치의640/1280 실제 추론으로 확인했다. source07 실내 적재 차량과 Nvidia 작은 차량2개는1280에서 기존 정답 IoU0.5/conf0.25를 충족했다. 공장safe_3_tr9는 부분 검출과 넓은 정답 외곽 범위 차이가 있고, 실외 트럭 옆 지게차는 배경이 포함된 위치 오류가 남는다. 정답을 축소해 점수를 올리지 않았다.

후진425/450/475/500/525프레임의 수동1fps 기준점도 확인했다. 부분 범위 검출 또는 적절한 전체 차량 박스 누락이 남는다. 차량 부품이 가려진 상태에서 상자만 보이는 부분을 검출 성공으로 인정하지 않는다. 상세9개 검수 결과는 체크포인트 failure-audit.json에 보존했다.

## 구현 및 검증

- `--forklift-specialist-imgsz 640 1280`: 두 해상도의 현재 프레임 실제 추론을 보완 결합한다. 기존0.25 이상 검출 보존; 사람/PPE클래스 변경 없음. 기본CLI는640로 유지하고 검토 실행에서만 두 해상도를 명시한다.
- `--forklift-geometric-association`: 영상2/3 지게차에만 신뢰도 가중치를 뺀 위치 중심 ByteTrack연결. 사람 추적 설정은 유지한다. 동일 관측 기준점에서 후진 목표 차량의 ID가2개→1개로 유지됐다. 매 프레임 정답ID를 검수한 IDF1평가는 아니다.
- 같은 차량의 부분·전체 박스가 다른 차량ID로 생성된 영상3 frame295에서 거짓 CRITICAL을 확인했다. 작은 박스의 겹침 비율0.65 이상이면 중복 또는 충돌로 겹친 차량을 구분할 수 없는 쌍으로 UNKNOWN처리한다. 기존0.8보다 보수적이며 실제 겹친 차량도 미확인으로 바뀔 수 있다. 검출 박스 자체를 삭제하지 않고 두 차량이 가까운 별도 박스일 때 경고는 유지한다.
- 관측을 놓치면 미확인; 추정 위치로 실제 검출 박스를 꾸미지 않는다. 거리 기준은 미보정 화면상 거리이며 m는null.
- 140개 자동 테스트 통과. 동일 캐시 프레임별 head_detections/PPE이벤트가 이전 결과와 완전히 같은지 검증했다. 이번 작업은 후드 문제를 수정한 단계가 아니다.

샘플링된 연동 검토: 2번106샘플/5fps, 3번87샘플/약4.795fps. 지게차 제안이 있는 샘플은98→101 및73→77; 오탐도 포함되므로 실제재현율로 해석하지 않는다. 전프레임 검증은 이전 native비교와 구분한다. 3번중복 검토 후 위험상태13→4샘플은 정확도지표가 아니라 보수적 이벤트 판정의 결과다.

## 재현

```sh
cd /Users/sanghyeopkim/Desktop/workspace
conda activate safety
python scripts/run_demo_scenarios.py --videos 2 3 --output outputs/diagnostics/forklift_review_next --reuse-run outputs/diagnostics/scenario_ppe_contract_short --forklift-specialist models/safe_carrying_envelope_v2/best.pt --forklift-specialist-imgsz 640 1280 --forklift-geometric-association
```

결과: `outputs/diagnostics/forklift_multiscale_geometric_v3_checked/video2/demo_h264.mp4`, video3동일경로. 각 영상의summary.json, detections.jsonl, proximity 또는 forklift_proximity/events_v1.jsonl을 팀원이 확인할 수 있다. 복구영상은outputs/checkpoints/forklift_postprocess_v3에 보존했다. 기본모델·다른 카메라 프로필은 교체하지 않았다. main병합 없음.

## 남은 작업

부분 차량/운반 적재물의 박스 기준을 일관되게 검수할 필요가 있다. 검수된 실제차량 부품이 거의 없는 구간은UNKNOWN을 유지한다. 트럭을 포함한 위치 오류와 설비 오탐은 별도 보완 후보. 3번 차량ID 정답과 경고 시점을 직접 검수해야 최종 이벤트 정확도를 말할 수 있다. 고해상도는오탐·중복·처리비용이 늘어 전체기본으로 승격하지 않는다.
