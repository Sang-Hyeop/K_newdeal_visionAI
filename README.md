# 시선 — 기존 CCTV 기반 AI 안전관제

작업자·지게차·안전모를 검출하고, 근접 위험·구역 침범·체류를 판정해 이벤트와 관제 화면으로 연결하는 팀 프로젝트다.
최종 발표 구성은 기능별4개+종합1개다. 새 입력 파일명과 기존1~7번 실행설정의 대응은 아직 갱신 전이다.

## 먼저 확인할 자료
- [현재 폴더·모델·최신 결과 위치](docs/workspace-guide.md)
- [감지 담당 목표](docs/detection-goal.md)
- [기존 영상별 기준과 변경 이력](docs/demo-feature-show-plan-2026-10-07.md)
- [최신 종합 영상 리뷰 기준](docs/video7-batch-review-2026-10-13.md)
- [10/14 폴더 정리 결과](docs/cleanup-2026-10-14.md)
- [백엔드·대시보드 연동 계약](docs/team-integration-pack-2026-10-07.md)
- [개발 도구 안내](scripts/README.md)

## 작업 환경과 구조
Python은 /opt/anaconda3/envs/safety/bin/python을 사용한다. src/는 감지·후처리, configs/는 실행설정, data/는 원본과 라벨, models/는 가중치, outputs/는 생성 결과다.
통합 실행 진입점은 scripts/run_demo_scenarios.py다. 새 발표영상 구성과 카메라 설정을 맞춘 뒤 실행한다. 기존 명령과1~7번 번호는 과거 runbook에서 확인할 수 있다.

최종 PPE는 models/ppe_final/ppe_helmet_v6_960.pt다. 객체 기본 모델과 각 카메라의 보완 모델은 configs/에 정의돼 있다. 하나의 프로그램에서 여러 모델을 연결하며 단일 .pt 통합이 완료된 상태는 아니다.

## 검증과 협업
판정·이벤트 검사는 safety 환경에서 python -m unittest discover -s tests -q로 수행한다. 영상 학습 노출에 따른 시연환경 개선과 독립현장 성능을 구분한다. 보정 없는 거리에는 미터를 표시하지 않고 미확인을 전체 현장 안전으로 해석하지 않는다.
작업브랜치·PR·병합 절차는 docs/CONTRIBUTING.md를 따른다. 모델·학습데이터·생성 결과는 Git과 별도 보관한다. 기존 사용자 영상 변경과 이번 정리 저장을 구분한다.
