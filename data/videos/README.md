# 팀 공용 시연 영상

최종 발표·시연에는 핵심 기능별 영상 4개와 모든 기능을 함께 보여주는 종합 영상 1개, 총 5개를 사용한다. 아래 구성은 2026-10-14 사용자 확정 기준이며, 이전 7개 영상 구성을 대체한다.

## 발표 영상 구성

1. **지게차와 작업자 충돌 위험 감지** — `1_forklift_worker_collision_risk.mp4`
2. **위험구역 ROI 침범 감지** — `2_restricted_zone_intrusion.mp4`
3. **안전모 미착용 감지** — `3_PPE_Helmet.mp4`
4. **위험구역 체류시간 감지** — `4_hazard_zone_dwell.mp4`
5. **모든 기능 종합 시연** — `5_Logistics Warehouse.mp4`

1~4번은 각 핵심 기능을 중심으로 시연하고, 5번은 네 기능을 통합한 결과를 보여준다. 발표 번호·파일명·실행 번호는 위 목록과 **동일**하다.

## 파일 및 공유 안내

- 이 폴더는 시연·개발 점검용 원본 영상을 보관한다. 생성된 감지 결과 영상은 프로젝트의 `outputs/`에 별도로 저장한다.
- 학습 이미지·라벨·ZIP·모델 가중치와 생성 결과는 원본 영상과 구분해 별도로 공유한다.
- Git으로 공유하는 영상은 해당 파일이 포함된 브랜치나 커밋을 내려받아 사용한다.
- 파일 버전을 비교할 때는 현재 파일의 SHA-256·크기·길이를 확인한다. `configs/demo-videos.json`에 현재 5개 원본의 파일명·SHA-256·크기·길이를 기록했다.
- 과거 7개 구성의 영상 번호·프레임 수·길이는 현재 파일의 정보로 간주하지 않는다.

## 실행

기본 진입점:

```bash
python handoff.py run --video 1   # … ~ --video 5
```

직접 실행기:

- 1·3·4·5번: `scripts/run_demo_scenarios.py --videos <N>`
- 2번 ROI 침범: `scripts/run_intrusion_review.py`

설정 기준: `configs/demo-scenarios.json`, `configs/team-runtime-index.json`
