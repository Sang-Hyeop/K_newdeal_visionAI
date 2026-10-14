# 대시보드 한글 라벨·JSON/CSV 계약 (2026-10-14)

브랜치: `feat/backend-event-log-review`  
합의 상태: 담당자 검토 대기  
실제 화면 적용: 없음 (표시 모듈·문서·샘플만)

## 산출물

| 항목 | 경로 |
| --- | --- |
| 공통 매핑 JSON | `configs/dashboard-labels.ko.json` |
| 필드 계약 초안 | `docs/event-log-field-contract.md` |
| 라벨 설명 | `docs/dashboard-ko-labels.md` |
| 표시/CSV 함수 | `backend_v1/dashboard_labels.py` |
| 샘플 | `backend_v1/samples/display/` |
| 테스트 | `backend_v1/test_dashboard_labels.py` |

## 검증

- 라벨·UTF-8·CSV 테스트 및 `test_backend.py` 실행
- API `http://127.0.0.1:8010` 이벤트 total=6139 유지 확인
- 원본 logs/DB/모델/영상 미수정

## 미합의

`docs/event-log-field-contract.md` §8 질문 목록 참고.
