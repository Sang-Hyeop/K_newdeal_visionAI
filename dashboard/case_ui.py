# 역할: 경보·조치 관리 화면의 목록·필터·상세 영역을 구성합니다.
# 경보·조치 관리 페이지 셸 HTML (데이터는 /sisun/alert-cases API)


def cases_shell_html() -> str:
    return """
<div id="sisun-cases-root" class="sisun-cases-root">
  <div class="sisun-cases-title">경보·조치 관리</div>
  <p class="sisun-cases-demo">반복 관측은 사건 단위로 묶습니다. 담당자 A~D는 최초 생성 시 자동 배정됩니다.</p>
  <p class="sisun-cases-demo" id="sisun-cases-storage">연결 상태 확인 중</p>
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


def case_display_payload(payload, frame, episodes, start):
    """사건 API에만 표시용 시각을 추가합니다. 원본·사건 키·집계는 수정하지 않습니다."""
    import math
    from datetime import timedelta
    from . import shared_cases

    live = {ep.get("link_key"): ep for ep in episodes}
    index = {}
    if frame is not None:
        from .timeline import event_seconds
        for row, seconds in zip(frame.to_dict("records"), event_seconds(frame)):
            if isinstance(seconds, (int, float)) and math.isfinite(seconds) and seconds >= 0:
                index[(str(row.get("area", "")), str(row.get("event_id", "")))] = float(seconds)

    def clock(seconds):
        if seconds is None:
            return ""
        millis = round(seconds * 1000)
        hours, rest = divmod(millis, 3600000)
        minutes, rest = divmod(rest, 60000)
        whole, fraction = divmod(rest, 1000)
        return f"{hours:02}:{minutes:02}:{whole:02}" + (f".{fraction:03}".rstrip("0") if fraction else "")

    def decorate(state):
        item = dict(state)
        ep = live.get(item.get("link_key")) or {}
        event_ids = ep.get("event_ids", item.get("event_ids", []))
        values = [index[(str(item.get("cam_id", "")), str(eid))]
                  for eid in event_ids
                  if (str(item.get("cam_id", "")), str(eid)) in index]
        # 에피소드의 상대 시각은 표시시계 기준일 수 있으므로 원본 경과초만 사용합니다.
        first = min(values) if values else None
        last = max(values) if values else None
        item["video_first_position"] = clock(first)
        item["video_last_position"] = clock(last)
        # 현재 세션의 재생 기준 시각이며 실제 처리 시각과 구분합니다.
        item["playback_first_at"] = ((start + timedelta(seconds=first)).isoformat(sep=" ", timespec="seconds")
                                     if ep and first is not None else "")
        item["playback_last_at"] = ((start + timedelta(seconds=last)).isoformat(sep=" ", timespec="seconds")
                                    if ep and last is not None else "")
        return item

    result = dict(payload)
    if "cases" in result:
        result["cases"] = [decorate(c) for c in result["cases"]]
    if result.get("state"):
        result["state"] = decorate(result["state"])
    result["storage_mode"] = "shared" if shared_cases.enabled() else "local"
    return result
