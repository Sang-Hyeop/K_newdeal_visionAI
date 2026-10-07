# 팀원용: 브랜치·시연 영상 받는 방법 (2026-10-07)

저장소: https://github.com/Sang-Hyeop/K_newdeal_visionAI  
작업 브랜치: `fix/proximity-detection-audit`  
( main 병합 전이면 **이 브랜치**를 받아야 최신 코드·영상이 보입니다.)

---

## 처음 clone 하는 경우

```bash
git clone https://github.com/Sang-Hyeop/K_newdeal_visionAI.git
cd K_newdeal_visionAI
git switch fix/proximity-detection-audit
conda activate safety
python -m pip install -r requirements.txt
```

시연 MP4 7개는 `data/videos/`에 있습니다.

---

## 이미 clone 한 경우

```bash
cd <저장소경로>
git status          # 로컬 수정 있으면 먼저 커밋 또는 stash
git fetch origin
git switch fix/proximity-detection-audit
git pull --ff-only origin fix/proximity-detection-audit
```

영상 확인:

```bash
ls -lh data/videos
# 7_Logistics Warehouse.mp4 는 약 3분 / 약 21MB 버전
```

메타데이터(해시·길이): `configs/demo-videos.json`

---

## Git에 없는 것 (별도 공유)

- 모델 가중치 `models/**/*.pt`
- 대용량 학습 이미지/라벨, 개인 경로 datasets
- 로컬 `outputs/` 전체 실행 결과 (샘플 일부는 `docs/team-samples/2026-10-07/`에 있음)

모델이 없으면 감지 실행은 못 하고, **JSONL 샘플로 로그·대시보드 연동**은 가능합니다.  
→ `docs/team-integration-pack-2026-10-07.md`

---

## PR / main 동기화

- 지금은 PR을 나중에 올려도 됩니다. 브랜치 push만으로도 팀원이 위 명령으로 받을 수 있습니다.
- main에 병합된 뒤에는:

```bash
git switch main
git pull --ff-only origin main
```

---

## 문제 해결

| 증상 | 확인 |
|---|---|
| 영상이 없다 | 브랜치가 `fix/proximity-detection-audit`인지, `git pull` 했는지 |
| 코드가 예전이다 | `git log -1 --oneline` 이 팀 공유 커밋과 같은지 |
| 모델 경로 오류 | `.pt` 별도 전달 여부 |
| 큰 7번 영상만 없다/다르다 | `configs/demo-videos.json`의 sha256과 로컬 파일 비교 |
