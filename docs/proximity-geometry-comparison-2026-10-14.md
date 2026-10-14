# 단일 CCTV 거리 기준점 비교 — 1단계

사용자 요청: 실제 치수·카메라 정보 없이 현재 5번 영상에서 차선책을 순서대로 비교한다. 기존 박스 경계 방식(A)과 지게차 아래변 중앙 방식(B)을 비교했다. 운영 설정과 기존 결과 영상은 바꾸지 않았다. B는 실험용 CLI 옵션으로만 실행한다.

## 비교 조건

- 동일 원본 해시, 실제 객체/PPE 캐시, 추적기, 탑승 확인, ROI 안팎, 자기 차량 제외 규칙을 유지한다.
- 작업자 발점에서 지게차 박스 아래변 중앙까지 거리를 계산하고 동일 작업자 높이로 정규화한다.
- 임계값은 WARNING 1.0, CRITICAL 0.3과 기존 히스테리시스를 유지한다. 새 기준점에 맞춰 검증된 임계값이 아니다.
- 870개 샘플에서 객체 검출·PPE·체류 이벤트가 기존과 완전히 같음을 검사했다. 근접 위험만 새 기하 기준으로 다시 계산했다.
- 오른쪽 점선은 ROI 정책 때문에 알림에서 제외된 쌍의 비교용 거리다. 점선으로 경보 이벤트를 만들지 않는다.

## 18.54초 비교

위쪽 P0:1–F0:13: CRITICAL(0.187) → SAFE(2.194).
위쪽 P0:32–F0:13: CRITICAL(0.255) → SAFE(3.322).
아래쪽 P0:4–F0:13: SAFE(1.285) → SAFE(1.424).
아래쪽 P0:30–F0:13: SAFE(1.608) → SAFE(1.614).

값은 사람 높이로 정규화한 화면상 거리이며 미터가 아니다. SAFE는 해당 실험 규칙 결과이며 실제 안전 확인이 아니다. 전체에서 표시 대상 쌍의 판정이 달라진 관측은 107건이다. 오탐 감소 건수나 정확도 개선율로 해석하지 않는다.

## 결과와 재현

핵심 구간 14~23초: outputs/reviews/5_geometry_bottom_center_focus.mp4.
전체 약 181초: outputs/reviews/5_geometry_bottom_center_full.mp4.
비교 수치: outputs/diagnostics/presentation5_geometry_comparison_2026-10-14/comparison_summary.json.
원시 실험 이벤트: outputs/diagnostics/presentation5_bottom_center_comparison_2026-10-14/video7/.

```bash
conda activate safety
python scripts/run_demo_scenarios.py --videos 7 --ppe-final --sample-fps 5 --reuse-run outputs/diagnostics/presentation5_filtered_detection_cache_2026-10-14 --reuse-objects --proximity-geometry bottom_center --output outputs/diagnostics/geometry_new_run
python scripts/compare_proximity_geometry.py --before outputs/diagnostics/presentation5_integrated_review_2026-10-14/video7 --after outputs/diagnostics/geometry_new_run/video7 --output outputs/diagnostics/geometry_new_comparison
```

## 판단과 후속

문제 장면에서는 박스 상단 때문에 짧게 나온 거리가 크게 달라졌다. 그러나 점 하나 방식은 차량 측면·포크 끝의 가까운 작업자를 놓칠 수 있다. 이를 보여주는 회귀 테스트도 추가했다. 테스트 231개 및 두 비교 MP4 전체 디코딩을 통과했다. 채택하지 않고 experimental_not_promoted로 남긴다.

다음 단계는 이 비교를 사용자와 검토하고 측면 접근 사례에서도 과소평가되는지 확인하는 것이다. 이동 방향은 추가 비교 항목이며 아직 위험 대상을 방향으로 제외하지 않는다. 바닥 원근 보정도 아직 적용하지 않았다. 평가 항목 3·6·7·8에 기여한다.
