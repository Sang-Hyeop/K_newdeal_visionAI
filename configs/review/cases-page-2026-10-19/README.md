# 경보·조치 관리 화면 확인 (2026-10-19)

평가 항목 5(관제 업무 흐름·조회·확인)에 기여.

## 캡처
- `cases-desktop-1440.png` — 사이드바 CAM06 아래 메뉴, 요약·필터·목록
- `cases-list-detail.png` — 목록+상세(조치 버튼·이력)
- `bell-thin.png` — 종 창(중요도·위치·최초·조치 관리·음소거)

## 검증 메모
- 단위 테스트 33 passed (`alert_response` / `alert_ops` / `alert_sound`)
- 배정 유지: 동일 link 재조회·전이 후 `담당자 C` 유지, 처리자 `김상협`
- 메모 필수: acting without note → 거부
- request_id 멱등: 중복 POST → `duplicate: true`, 이력 1회
- 마이그레이션: 유효 배정 83건 유지, 재실행 시 재배정 없음
