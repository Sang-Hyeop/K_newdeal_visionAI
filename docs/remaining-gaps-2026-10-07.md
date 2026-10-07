# 남은 갭 · 해결 방안 (2026-10-07)

시연 규칙 구현은 대체로 끝났고, 아래는 **아직 남거나 의도적으로 미룬 항목**이다.

| 상태 | 의미 |
|---|---|
| 진행중/가능 | 지금 코드·인계로 손댈 수 있음 |
| 보류 | 데이터·보정·일정 이유로 의도적 미룸 |
| 완료 | 이번 브랜치에서 처리됨 |

---

## 1. 완료된 갭 (참고)

| 항목 | 처리 |
|---|---|
| 후드 메인 미활성 | `run_demo_scenarios.py --hood-auxiliary` |
| 3번 “미구현” 문서 | 시연계획 갱신 · `forklift_forklift_proximity` |
| 합쳐진 지게차 박스 거리 | UNKNOWN (`merged_or_duplicate_vehicle_boxes`) |
| PPE–지게차 과겹침 | UNKNOWN (`possible_operator_or_equipment_person_box`) |
| 팀 실행 안내 | `docs/demo-scenario-runbook-2026-10-07.md` |
| pt 해시 목록 | `docs/checkpoints/2026-10-07/model-share-manifest.json` |
| pt 묶음 스크립트 | `scripts/pack_demo_models.py` |

품질 가드 샘플 효과(캐시 재계산, 정확도 주장 아님):

- video3 검출 지게차 쌍 79개 중 **30개**가 합침/중복으로 판정 불가(unreliable)
- video7 PPE에서 지게차 과겹침으로 **WARNING 93건** → UNKNOWN 후보

---

## 2. 아직 부족한 것 + 해결 방안

### A. 인계 행정 (진행중)

| 부족 | 해결 방안 | 담당 |
|---|---|---|
| 팀이 `.pt` 없음 | `python scripts/pack_demo_models.py`로 zip 생성 후 드라이브/메신저 공유. 수신 측은 zip README의 SHA 대조 | 사용자 |
| PR / main 미병합 | `docs/pr-draft-2026-10-07.md` 링크로 PR 생성 후 리뷰·병합 | 저장소 소유자 |
| 백엔드/대시보드 실연동 | `docs/team-integration-pack-2026-10-07.md` + `docs/team-samples/` JSONL로 파서·배너 연결 | 팀 |

### B. 품질 (가능 · 재학습 최소화)

| 부족 | 해결 방안 | 비고 |
|---|---|---|
| 설비→사람 오탐(지게차와 안 겹침) | 일괄 모양/정지 필터는 **금지**(실제 앉은 작업자 보존). 독립 현장에서 hard-negative 소량 검수 후 학습 후보만 | 데이터 필요 |
| PPE 미착용 미탐/오탐 | 머리 연결·임계는 유지. 새 검수 프레임 없으면 재학습 반복하지 않음 | experimental PPE 유지 |
| 후드+WARNING 공존 | 정책: WARNING 보존(후드 FP가 실제 위험 지우지 않게). 후드 트랙만 UNKNOWN 강제하려면 별도 승인 | 정책 선택지 |
| 3번 박스 합침 근본 | 검출/NMS·추적 품질. 후처리는 이미 UNKNOWN 가드 | 학습/추적 후속 |
| 4번 실영상 유차량 CRITICAL | 해당 구간 샘플로 재실행·육안 확인 | 검증 작업 |

### C. 의도적 보류

| 부족 | 왜 보류 | 언제 다시 |
|---|---|---|
| 단일 `.pt` 통합 | 단독 교체 시 고정평가 회귀 | 통합 학습 설계 후 |
| `distance_meters` / 캘리브레이션 | 검증된 보정 없음. 가짜 m 금지 | 기준점 확보 후 |
| 후진=orientation 상태 | centroid만으로 오판 위험 | 검출 안정 후 고도화 |
| 새 현장 일반화 증명 | 시연 적응 ≠ 독립 현장 | 시연 외 영상 확보 후 |

---

## 3. 바로 다음 실행 순서 (추천)

1. `conda activate safety && python scripts/pack_demo_models.py`
2. 생성된 `outputs/checkpoints/demo_models_share_*.zip` 팀 공유
3. `docs/pr-draft-2026-10-07.md`에서 PR 생성
4. (선택) 설비 오탐·4번 유차량 구간만 육안 검수 리스트 작성

자동 검사:

```bash
python -m unittest discover -s tests -p 'test_*.py' -q
```
