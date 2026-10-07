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
- `docs/team-samples/2026-10-07/**` (JSONL 앞부분 샘플)

## Git에 올리지 않는 것 (학습/실험 WIP)

아래는 Codex·로컬 실험 중일 수 있으므로 **문서 PR/커밋에 섞지 않음**.

- `scripts/audit_pilot_predictions.py` 등 수정 중 파일
- `scripts/render_ppe_events.py`, `scripts/validate_tracked_ppe.py` 수정분
- `src/ppe_person_crop.py` 수정분
- `src/ppe_recall_ensemble.py`, `tests/test_ppe_recall_ensemble.py` (untracked)
- `outputs/training/**` 학습 로그·가중치
- `_local_archive/**` 대용량 백업 영상

학습이 끝나고 채택할 코드만 따로 커밋합니다.

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
