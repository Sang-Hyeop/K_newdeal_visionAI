# 로컬 작업트리 정리 메모 (2026-10-07)

Codex 학습/실험과 Cursor 문서 작업을 섞지 않기 위한 메모입니다.

---

## Git에 올려도 되는 것 (이번 문서 패키지)

- `docs/team-integration-pack-2026-10-07.md`
- `docs/pr-draft-2026-10-07.md`
- `docs/roi-wording-2026-10-07.md`
- `docs/team-branch-setup-2026-10-07.md`
- `docs/worktree-notes-2026-10-07.md`
- `docs/team-handoff-index-2026-10-07.md`
- `docs/demo-feature-show-plan-2026-10-07.md` (시연 규칙 권위 + Codex 대조)
- `docs/team-samples/2026-10-07/**` (JSONL 앞부분 샘플)

## Codex ↔ Cursor 시연 규칙 맞출 때

1. 시연 ON/OFF는 `docs/demo-feature-show-plan-2026-10-07.md` (§6 Codex 대조 포함)
2. Codex가 돌린 증거는 `docs/checkpoints/2026-10-07/` + `docs/progress-2026-10-07.md`
3. **시연 문서만** GitHub에 올릴 때 아래 Codex 구현/학습 WIP와 **절대 섞지 않음**

## Git에 올리지 않는 것 (Codex 구현·학습 WIP — 방해 금지)

Codex가 `demo-feature-show-plan` 기준으로 다시 맞추는 중이면 아래를 **커밋·삭제·리셋하지 말 것**.

- `configs/demo-scenarios.json`, `configs/cameras/warehouse-summary.json`
- `src/forklift_proximity.py`, `src/scenario_zone.py`, `src/scenario_render.py`
- `src/lane_hazard.py`, `src/zone_dwell.py`, `src/event_contract.py` 수정분
- `tests/test_scenario_plan.py`
- PPE/객체 학습·진단 스크립트 수정분, `outputs/training/**`, `_local_archive/**`

학습·시나리오 구현이 끝나고 채택할 코드만 **별도 커밋**합니다.

---

## 정리 명령 (필요할 때만)

작업트리만 보고 싶을 때:

```bash
git status -sb
git stash push -u -m "wip-codex-ppe" -- scripts src/ppe_person_crop.py src/ppe_recall_ensemble.py tests/test_ppe_recall_ensemble.py
```

되돌리기:

```bash
git stash pop
```

강제 삭제는 하지 않습니다.
