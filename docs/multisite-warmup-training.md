# 111장 학습 및 초기 bias 학습률 비교

v11: 확대111장(train92/val8/test11), v6초기화, AdamW0.0001,12epoch,640,freeze0. 같은개발시험conf0.25/IoU0.5에서 사람TP9/FP5/FN9, 지게차TP9/FP5/FN2. 기존v6는사람TP12/FP5/FN6, 지게차TP10/FP2/FN1. 확대학습만으로개선되지않았다.

설치된Ultralytics8.4.153 trainer.py를검사해warmup단계bias그룹의초기학습률이0.1인점을확인했다. 이는기본lr0.0001과별개이고,명시적AdamW설정에서는auto optimizer분기의0.0보정이실행되지않는다. 이전의낮은학습률설명은이초기설정을포함하지못했다. 스크립트에--warmup-bias-lr를추가했고실제값을snapshot에저장한다. 기본값을생략한기존실험재현은유지하므로앞으로의명령어에는명시적으로값을넣는다.

v12: v11과전체데이터111장의이미지/라벨SHA및초기가중치SHA동일,실행args차이는출력명/경로외warmup_bias_lr 0.1→0.0001뿐. 같은시험사람TP11/FP6/FN7, 지게차TP10/FP2/FN1. v11보다좋지만v6의사람누락을넘지못해experimental_not_promoted. 초기설정의영향을보는한번의개발실험이며전체실패의유일원인이거나새현장개선을입증한것은아니다.

v6/v11및v6/v12는각각전진·후진의0/5/10/15/20초대표프레임을같은640/conf0.25로비교했다. v11전진10초작업자/지게차누락과등화장치사람오탐,후진10초설비지게차오탐을육안확인. v12후진10초는실제지게차를검출하고그설비오탐이사라졌지만전진10초작업자/지게차누락과등화장치오탐은남았다. 개별장면개선을전체정확도로확대해석하지않는다.

v12후진전체구간5fps106프레임근접실행: SAFE4/UNKNOWN18 쌍관측,확인가능쌍없는프레임102/106,상태변화6회,WARNING/CRITICAL0. 누락/ID분절로연속감시가부족하다. SAFE는해당관측쌍의영상상규칙후보이고전역안전보장이아니다. 전진전체근접실행은반복하지않았다. 시연영상은학습에서제외했으나개발확인에반복사용했으므로독립최종평가가아니다.

재현(safety,저장소루트):
```sh
python scripts/train_reviewed_pilot.py --dataset logistics --data-path data/reviewed_pilot/logistics_multisite_v1 --weights models/pilot_v6_corrected_forklift/person_forklift.pt --epochs 12 --learning-rate 0.0001 --warmup-bias-lr 0.0001 --run-name logistics_pilot_v12_low_bias_warmup
```

모델v11/v12와원본은보존. v11모델포함8파일및v12모델/영상포함13파일SHA복구사본저장. 동일디스크백업이며외부백업은아니다. 코드/설정/평가기록로컬Git체크포인트,이번단계GitHub push/main병합없음.

다음비교방향: 기존사람특징및분류층을정확히보존하는초기화에보정된warmup_bias_lr0.0001을적용한다. 이전v8은기존76장/다른학습률/기본bias warmup이어서이조합의결과가아니다. 현재시연용모델자동교체없음,다음실험아직시작하지않음.
