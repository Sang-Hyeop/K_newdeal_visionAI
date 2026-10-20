# 역할: 경보·조치 관리 화면의 목록·필터·상세 영역을 구성합니다.
# 경보·조치 관리 페이지 셸 HTML (데이터는 /sisun/alert-cases API)


def cases_shell_html() -> str:
    return """
<div id="sisun-cases-root" class="sisun-cases-root">
  <div class="sisun-cases-title">경보·조치 관리</div>
  <p class="sisun-cases-demo">반복 관측은 사건 단위로 묶습니다. 담당자 A~D는 최초 생성 시 자동 배정됩니다.</p>
  <div class="sisun-cases-actions" role="group" aria-label="사건 조회 범위">
    <button type="button" id="cases-open" aria-pressed="true">미완료 사건</button>
    <button type="button" id="cases-all" aria-pressed="false">전체 경보</button>
  </div>
  <div id="sisun-cases-summary" class="sisun-cases-summary"></div>
  <div class="sisun-cases-filters" id="sisun-cases-filters"></div>
  <div class="sisun-cases-body">
    <div id="sisun-cases-list" class="sisun-cases-list"></div>
    <div id="sisun-cases-detail" class="sisun-cases-detail">
      <div class="sisun-cases-empty">사건을 선택하면 상세·조치가 표시됩니다</div>
    </div>
  </div>
</div>
"""
