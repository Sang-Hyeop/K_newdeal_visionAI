# 스크립트 용도별 목록

현재 기본 실행 진입점은 `run_demo_scenarios.py`입니다. 아래 도구는 전부 매번 실행하는 것이 아닙니다. 분류는 파일명·코드 구조에 따른 용도이며, 목록에 있다는 이유로 현재 모델에 채택된 실험이라는 뜻은 아닙니다. 기존 경로 계산과 개발 기록을 보존하기 위해 .py 파일은 이동하지 않았습니다.

## 시연·실행 (4개)

- [pack_demo_models.py](pack_demo_models.py): Pack Git-excluded demo weights into a shareable zip with SHA-256 checks.
- [run_demo_scenarios.py](run_demo_scenarios.py): One saved-video workflow: independent rules, PPE on every scenario, real detections only.
- [run_proximity_video.py](run_proximity_video.py): Two-class tracking and camera-configured image-plane proximity candidates.
- [run_zone_dwell_video.py](run_zone_dwell_video.py): Detector -> tracker -> configured ROI dwell -> events and annotated video.

## 학습 (4개)

- [train_hood_context_v2.py](train_hood_context_v2.py): One context-crop experiment, preserving v1 and all original train/eval files.
- [train_hoodie_auxiliary.py](train_hoodie_auxiliary.py): Train a separate whole-person hood classifier; never map Normal to PPE SAFE.
- [train_preserved_head.py](train_preserved_head.py): YOLO26 분류 특징층을 유지한 두 클래스 초기화와 추가 학습. 설치 버전 8.4.153 검증용.
- [train_reviewed_pilot.py](train_reviewed_pilot.py): 학습 허용 manifest를 확인하고 지정 초기 가중치로 개발용 학습.

## 데이터 준비·라벨 검수 (28개)

- [build_demo_adaptation_dataset.py](build_demo_adaptation_dataset.py): Build explicitly authorized demo adaptation while preserving old evaluation splits.
- [build_demo_ppe_dataset.py](build_demo_ppe_dataset.py): Explicitly authorized PPE demo adaptation, with unobservable hoods excluded.
- [build_label_examples.py](build_label_examples.py): 육안으로 작성한 수동 라벨 초안을 출력합니다. 학습에서는 제외합니다.
- [build_pilot_datasets.py](build_pilot_datasets.py): 검수 기록에 따라 파일을 선별하고 현장/원본 그룹을 분리한 시험 데이터 초안 생성.
- [build_ppe_failure_contexts.py](build_ppe_failure_contexts.py): Short failure-specific refinement: real image contexts, no generated labels.
- [build_ppe_remaining_dataset.py](build_ppe_remaining_dataset.py): Build reviewed remaining PPE data, preserving the original holdouts.
- [build_related_forklift_dataset.py](build_related_forklift_dataset.py): Build reviewed context crops without promoting model-generated draft labels.
- [build_targeted_forklift_dataset.py](build_targeted_forklift_dataset.py): Build one reviewed, scale-preserving supplemental dataset; protect old splits.
- [draft_related_forklift_labels.py](draft_related_forklift_labels.py): 개발·검증 도구; 실행 인자와 본문 확인
- [extract_review_frames.py](extract_review_frames.py): safety 환경에서 실행: python scripts/extract_review_frames.py
- [filter_scaled_logistics.py](filter_scaled_logistics.py): Conservative source-label gate; exclusion is not proof of a missing driver.
- [index_logistics04_sources.py](index_logistics04_sources.py): 개발·검증 도구; 실행 인자와 본문 확인
- [prepare_corrected_forklift_expansion.py](prepare_corrected_forklift_expansion.py): 직접 시각 검수한 TS07 8장: 960x540 화면 좌표를 원본 좌표로 복원.
- [prepare_full_scene_expansion.py](prepare_full_scene_expansion.py): 전체 CCTV 프레임의 수동 검수 라벨. 애매한 원거리 영역은 일부 이미지에서 명시적으로 마스크.
- [prepare_hard_examples.py](prepare_hard_examples.py): Build a separately versioned, reviewed hard-example dataset from local ZIPs.
- [prepare_hoodie_auxiliary.py](prepare_hoodie_auxiliary.py): Reproduce the sampled hood dataset and normalize mixed YOLO polygons to boxes.
- [prepare_ppe_remaining_review.py](prepare_ppe_remaining_review.py): Prepare raw failed-head crops and existing annotated source candidates for review.
- [prepare_related_forklift_frames.py](prepare_related_forklift_frames.py): Extract diverse train-video candidates; unlabelled frames are not training data.
- [prepare_reviewed_expansion.py](prepare_reviewed_expansion.py): Apply explicitly reviewed expansion decisions; preserve sources and earlier datasets.
- [prepare_reviewed_logistics.py](prepare_reviewed_logistics.py): 검수 승인한 작은 부분집합과 누락/박스 수정 기록을 별도 사본에 적용.
- [prepare_reviewed_ppe.py](prepare_reviewed_ppe.py): 66개 PPE 후보의 시각 검수 결정을 적용한 별도 시험셋 생성.
- [prepare_scaled_logistics.py](prepare_scaled_logistics.py): Build a larger source-labelled draft; sampled review gates training permission.
- [prepare_small_worker_expansion.py](prepare_small_worker_expansion.py): Apply visual decisions to an immutable copy of the previous object dataset.
- [prepare_train_source_expansion.py](prepare_train_source_expansion.py): 개발·검증 도구; 실행 인자와 본문 확인
- [prepare_training_review.py](prepare_training_review.py): 원본 ZIP을 보존하며 학습 전 검토용 표본과 라벨 미리보기를 만듭니다.
- [scan_local_training_sources.py](scan_local_training_sources.py): 개발·검증 도구; 실행 인자와 본문 확인
- [select_error_focus_candidates.py](select_error_focus_candidates.py): Mine 40 unused train-group candidates; predictions do not approve labels.
- [select_small_worker_review.py](select_small_worker_review.py): Select unseen source groups with small workers; outputs are unapproved drafts.

## 평가·진단 (29개)

- [assess_targeted_forklift_gate.py](assess_targeted_forklift_gate.py): Compare fixed development gates; never promote a checkpoint automatically.
- [audit_dense_reverse_target.py](audit_dense_reverse_target.py): Every-frame target diagnostic; interpolated reference boxes never enter inference.
- [audit_downloaded_data.py](audit_downloaded_data.py): 개발·검증 도구; 실행 인자와 본문 확인
- [audit_object_multiscale_recall.py](audit_object_multiscale_recall.py): Recall diagnostic using real multiscale detections; never edit test labels.
- [audit_person_crop_support.py](audit_person_crop_support.py): Shadow-only crop support audit; never suppress production detections.
- [audit_pilot_predictions.py](audit_pilot_predictions.py): 개발용 test의 고정 신뢰도/IoU 조건에서 TP/FP/FN 측정. 작은 표본의 진단용.
- [audit_ppe_bare_head_sequence.py](audit_ppe_bare_head_sequence.py): Interpolated bare-head review diagnostic; not exhaustive manual GT.
- [audit_ppe_exact_frames.py](audit_ppe_exact_frames.py): Exact source frames and reviewed primary head references. Adaptation only.
- [audit_ppe_remaining_heads.py](audit_ppe_remaining_heads.py): Actual fixed-threshold head recall on reviewed crops; adaptation diagnostic.
- [audit_ppe_video_heads.py](audit_ppe_video_heads.py): Evaluate reviewed visible heads against real predictions, not state counts.
- [audit_related_video_overlap.py](audit_related_video_overlap.py): 개발·검증 도구; 실행 인자와 본문 확인
- [audit_training_pool.py](audit_training_pool.py): safety 환경에서 실행. 전체 PPE 구조 검사/검수판과 물류 후보 인덱스를 생성.
- [calibrate_pilot_thresholds.py](calibrate_pilot_thresholds.py): val에서만 클래스별 신뢰도를 진단. 작은 표본이므로 운영 임계값으로 승인하지 않는다.
- [compare_person_sources.py](compare_person_sources.py): Compare separately evaluated person sources without tuning or training.
- [compare_related_v16_outputs.py](compare_related_v16_outputs.py): Collect fixed-condition v15/v16 diagnostics; never promote automatically.
- [compare_validation_input_settings.py](compare_validation_input_settings.py): Compare reused validation samples only; never change production thresholds.
- [diagnose_detector_regression.py](diagnose_detector_regression.py): Compare fixed-test errors and training distribution; no automatic label edits.
- [diagnose_proximity_gaps.py](diagnose_proximity_gaps.py): Audit raw detector predictions against saved ROI/tracker observations; no training.
- [diagnose_v9_regression.py](diagnose_v9_regression.py): Compare v6/v9 at object level; never edit held-out labels.
- [evaluate_demo_adaptation.py](evaluate_demo_adaptation.py): Evaluate a demo-adapted checkpoint with unchanged tracking/thresholds.
- [evaluate_hoodie_auxiliary.py](evaluate_hoodie_auxiliary.py): Evaluate the externally trained hood model on the reviewed source6 hood track.
- [evaluate_targeted_forklift.py](evaluate_targeted_forklift.py): Evaluate the precommitted target gate, without selecting or modifying weights.
- [probe_forklift_v9.py](probe_forklift_v9.py): Fixed representative-frame diagnostic; no ground-truth accuracy claim.
- [probe_proximity_tiles.py](probe_proximity_tiles.py): 개발·검증 도구; 실행 인자와 본문 확인
- [run_pilot_videos.py](run_pilot_videos.py): 두 시험 모델로 보관 영상 검출. 위험 판단 이전의 영상/JSONL 출력.
- [validate_completed_v15.py](validate_completed_v15.py): Wait for the active training run, then evaluate without promoting a model.
- [validate_ppe_person_crop.py](validate_ppe_person_crop.py): Compare full-frame and person-crop PPE on a saved video; no risk alerts.
- [validate_related_v16.py](validate_related_v16.py): Wait for the active training run, then evaluate without promoting a model.
- [validate_tracked_ppe.py](validate_tracked_ppe.py): Saved-video person tracking and per-observation PPE; no risk decisions.

## 결과 재계산·렌더링 (6개)

- [refine_ppe_cached_heads.py](refine_ppe_cached_heads.py): Add real contextual head inferences to saved observations; no GT-dependent crops.
- [render_lane_events.py](render_lane_events.py): Render stored lane observations without changing detections or decisions.
- [render_ppe_events.py](render_ppe_events.py): Render saved real PPE observations without repeating inference or decisions.
- [replay_hood_auxiliary.py](replay_hood_auxiliary.py): Opt-in hood inference on cached real detections; preserve risk warnings and veto SAFE.
- [replay_ppe_candidate_tracks.py](replay_ppe_candidate_tracks.py): Use real pre-confirmation body boxes for PPE, reusing same-frame head evidence.
- [replay_ppe_rules.py](replay_ppe_rules.py): Re-evaluate policies over saved real model observations without inference.

