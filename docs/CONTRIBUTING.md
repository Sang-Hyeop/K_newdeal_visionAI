# 팀 협업 절차

수업 자료 ‘Git과 협업’의 브랜치·PR·리뷰·병합 후 동기화 절차를 적용합니다.

## 작업 시작

미커밋 변경을 먼저 확인하고 보존합니다. 작업 트리가 깨끗할 때 최신 main에서 작업 브랜치를 만듭니다.

```bash
git status
git switch main
git pull --ff-only origin main
git switch -c feat/작업이름
```

예: `feat/roi-intrusion`, `feat/event-log`, `feat/dashboard`.

## 변경 공유

```bash
git status
git add 수정한파일경로
git diff --cached
git commit -m "변경 내용"
git push -u origin 현재브랜치이름
```

GitHub PR에서 base는 main, compare는 작업 브랜치인지 확인합니다. 변경 내용과 검증 결과를 기록하고 리뷰를 요청합니다. 미완성 작업은 Draft PR로 공유할 수 있습니다.

## 병합 후

리뷰·충돌 해결 후 병합합니다. main 보호 규칙은 아직 설정하지 않았으므로 별도 설정이 필요합니다. 팀원 모두 로컬 변경을 보존한 뒤 동기화합니다.

```bash
git switch main
git pull --ff-only origin main
git fetch --prune origin
```

완료한 로컬 브랜치는 병합 여부를 확인하고 `git branch -d 브랜치이름`으로 삭제합니다. 삭제가 거부되면 강제 삭제하지 말고 이유를 확인합니다.

## 충돌과 되돌리기

양쪽 변경 의도를 확인해 충돌을 해결하고 실행을 검증합니다. 공유된 변경 취소는 revert를 우선 검토합니다. reset --hard와 강제 push는 작업 손실·공유 이력 영향을 먼저 확인합니다.

## 파일 관리

데이터·모델·결과는 별도 공유하고 비밀키는 커밋하지 않습니다. 저장소 안에 다른 저장소를 clone하지 않습니다. 폴더와 이벤트 인터페이스 변경은 팀에 공유합니다.
