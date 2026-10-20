# 역할: 로그인·메인·카메라·사건·이력·통계 화면과 갱신 흐름을 연결합니다.
# 탭 화면 조립·로그인 후 대시보드 실행
import os
import uuid
import threading
import time

import gradio as gr

from .config import (
    CAMERAS,
    CAM_BY_ID,
    DATA_ROOT,
    INK_TITLE,
    LOCAL,
    SCENARIOS,
    SITES,
    TABS,
    TITLE,
    VIDEO_DIR,
    cam_main_label,
    cam_side_label,
    cam_tag,
)
from .events import get_df, live_part, live_positions, load_df, peek_df
from .media import camera_detect, camera_origin
from .timeline import playback_inputs
from .sound import beep_html, notify, reset_notify_state, write_beep
from .style import BOOT_JS, CSS, make_theme
from .ui import (
    cam_danger_overlay_html,
    card,
    danger_overlay_updates,
    do_login,
    do_logout,
    header_html,
    kpi_html,
    live_flash_html,
    login_foot,
    login_html,
    side_brand_html,
    table_html,
    theme_foot_html,
    title_html,
)

# 독립 알림 버스: 사이드 탭·영상 DOM과 무관. #1 세션 시작 시각부터 실시간으로 진행.
_ALERT_BUS = {"on": False, "t0": None, "epoch": 0}


def _alert_bus_reset():
    """로그인·새로고침 시 알림 타임라인만 0부터."""
    _ALERT_BUS["epoch"] = int(_ALERT_BUS.get("epoch") or 0) + 1
    _ALERT_BUS["t0"] = time.monotonic()


def _alert_bus_elapsed():
    t0 = _ALERT_BUS.get("t0")
    if t0 is None:
        return 0.0
    return max(0.0, time.monotonic() - float(t0))


def _alert_bus_start():
    _ALERT_BUS["on"] = True
    if _ALERT_BUS.get("t0") is None:
        _ALERT_BUS["t0"] = time.monotonic()
    return gr.update(active=True)


def _alert_bus_stop():
    _ALERT_BUS["on"] = False
    _ALERT_BUS["t0"] = None
    return gr.update(active=False)


def _alert_bus_tick():
    """탭과 무관하게 #1과 같은 경과초로 주의/위험 알림."""
    if not _ALERT_BUS.get("on"):
        return gr.update()
    elapsed = _alert_bus_elapsed()
    if elapsed <= 0:
        return ""
    view = get_df()
    if view is None:
        view = peek_df()
    if view is None:
        return gr.update()
    positions = {cam["id"]: elapsed for cam in CAMERAS}
    part = live_positions(view, positions)
    kind = notify(part)
    # None = 변경 없음. "" = 목록 갱신만(소리 없음). hot/warn = 소리+목록.
    if kind is None:
        return gr.update()
    return beep_html(kind)


_ICON_DIR = os.path.join(os.path.dirname(__file__), "packaging", "icons")
_FAVICON = next(
    (
        os.path.join(_ICON_DIR, name)
        for name in ("sisun.png", "sisun.ico")
        if os.path.isfile(os.path.join(_ICON_DIR, name))
    ),
    None,
)

_BOOT_TIMERS = []
_DATA_BOOT_STARTED = False


def _start_data_boot():
    """로그인 성공 후에만 이벤트 적재·영상 워밍 시작."""
    global _DATA_BOOT_STARTED
    if _DATA_BOOT_STARTED:
        return
    _DATA_BOOT_STARTED = True

    def _run():
        try:
            load_df()
        except Exception:
            pass
        # 첫 판정 패널·첫 위험음 지연 완화 (백그라운드 1회)
        try:
            from .criteria_runtime import criteria_cache

            criteria_cache()
        except Exception:
            pass
        try:
            write_beep()
        except Exception:
            pass
        for cam in CAMERAS:
            try:
                camera_origin(cam)
            except Exception:
                pass
            try:
                camera_detect(cam)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()


def _login_flow(uid, pw):
    return do_login(uid, pw)


def _after_login(user):
    if not user:
        return tuple(gr.update() for _ in _BOOT_TIMERS)
    _start_data_boot()
    return tuple(gr.update(active=True) for _ in _BOOT_TIMERS)


def _existing(dest_name):
    dest = os.path.join(LOCAL, dest_name)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return dest
    return None


def _ensure_clip(cam, dest_key):
    """origin/detect 파일이 없으면 즉시 생성·복사."""
    dest_name = cam[dest_key]
    path = _existing(dest_name)
    if path:
        return path
    try:
        if dest_key == "origin":
            camera_origin(cam)
        else:
            camera_detect(cam)
    except Exception:
        pass
    return _existing(dest_name)


def _attach_boot(demo, outputs, build):
    n = len(outputs)
    got = gr.State(False)
    timer = gr.Timer(1.0, active=False)

    def _empty():
        return tuple(gr.update() for _ in range(n))

    def _pack(result):
        if not isinstance(result, tuple):
            result = (result,)
        return result

    def _fill(done):
        if done:
            return tuple(list(_empty()) + [True, gr.update(active=False)])
        view = peek_df()
        if view is None:
            return tuple(list(_empty()) + [False, gr.update()])
        return tuple(list(_pack(build(view))) + [True, gr.update(active=False)])

    timer.tick(
        _fill,
        inputs=[got],
        outputs=list(outputs) + [got, timer],
        concurrency_limit=1,
    )
    demo._boot_timer = timer


def _cam_wall(
    cams, dest_key, wall_id="sisun-wall", captions=False, expandable=True, alerts=False
):
    """카메라 그리드. dest_key: origin | detect.
    captions=True: 메인 소제목. expandable=False: 클릭 확대 없이 처음부터 크게.
    alerts=True: 영상 하단 위험 오버레이 칸.
    """
    vids = []
    dests = []
    cam_refs = []
    alert_boxes = []
    wall_cls = ["sisun-wall"]
    if not expandable:
        wall_cls.append("sisun-wall-solo")
    elif captions:
        wall_cls.append("sisun-wall-main")
    with gr.Column(elem_id=wall_id, elem_classes=wall_cls):
        # 메인 확대는 유튜브형 시어터(JS). X 버튼은 쓰지 않음.
        if len(cams) == 1:
            groups = [cams]
        elif len(cams) <= 3:
            groups = [cams]
        else:
            groups = [cams[:3], cams[3:]]
        # 메인 6칸은 CSS로 남은 세로를 채움(고정 height 제거). 단일은 큰 높이.
        if captions and len(cams) > 1:
            vid_h = None
        elif len(cams) > 1:
            vid_h = 240
        else:
            vid_h = 680 if not expandable else 420
        for group in groups:
            with gr.Row(elem_classes="sisun-wall-row"):
                for cam in group:
                    with gr.Column(elem_classes="sisun-cam-slot", scale=1):
                        if captions:
                            gr.HTML(
                                f"<div class='sisun-cam-cap' data-cam='{cam['id']}'>"
                                f"<span class='sisun-cam-cap-label'>{cam_main_label(cam)}</span>"
                                f"</div>"
                            )
                        with gr.Column(elem_classes="sisun-cam"):
                            if not captions:
                                gr.HTML(
                                    f"<div class='sisun-cam-tag'>{cam_tag(cam)}</div>"
                                )
                            if alerts:
                                alert_boxes.append(
                                    gr.HTML(
                                        cam_danger_overlay_html(False),
                                        elem_classes="sisun-cam-alert",
                                    )
                                )
                            # 파일이 있으면 처음부터 넣고, 없어도 타이머/탭 진입 시 채움
                            initial = _ensure_clip(cam, dest_key)
                            vid_kw = dict(
                                value=initial,
                                autoplay=False,
                                loop=True,
                                include_audio=False,
                                show_label=False,
                                elem_classes="sisun-cam-vid",
                                elem_id=f"sisun-video-{wall_id}-{cam['id']}",
                                buttons=[],
                            )
                            if vid_h is not None:
                                vid_kw["height"] = vid_h
                            vids.append(gr.Video(**vid_kw))
                            dests.append(cam[dest_key])
                            cam_refs.append(cam)
    return vids, dests, cam_refs, alert_boxes


def _attach_vid_timer(demo, vids, dests, cams, dest_key):
    got = gr.State(False)
    vid_timer = gr.Timer(0.3, active=False)

    def _fill_vids(done):
        n = len(vids)
        if done:
            return tuple(gr.update() for _ in range(n)) + (
                True,
                gr.update(active=False),
            )
        values = []
        ready = True
        for cam, dest in zip(cams, dests):
            path = _ensure_clip(cam, dest_key)
            if path:
                values.append(path)
            else:
                values.append(gr.update())
                ready = False
        if ready:
            return tuple(values) + (True, gr.update(active=False))
        return tuple(values) + (False, gr.update())

    vid_timer.tick(
        _fill_vids,
        inputs=[got],
        outputs=vids + [got, vid_timer],
        concurrency_limit=None,
    )
    demo._vid_timer = vid_timer


def make_main(cams):
    """메인 관제: KPI는 로그인 직후·새로고침에서만 0부터. 영상 루프로는 리셋하지 않음."""
    with gr.Blocks() as demo:
        kpis = gr.HTML(kpi_html(None))
        sound = gr.HTML(elem_classes="t2-sound")
        playing = gr.State(False)
        playheads = gr.JSON(value={}, visible=False)
        ready = gr.State(False)
        vids, dests, cam_refs, alert_boxes = _cam_wall(
            cams,
            "origin",
            wall_id="sisun-wall",
            captions=True,
            alerts=True,
        )
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        timer = gr.Timer(0.4, active=False)
        # 카메라별 재생 위치 최고값. 루프(currentTime 감소)여도 KPI는 유지.
        # await_restart: 새로고침 직후 영상이 아직 중간이면 KPI를 0으로 유지.
        # epoch: 새로고침과 타이머 틱 레이스로 이전 결과가 덮어쓰는 것 방지.
        kpi_session = {
            "started": False,
            "max_pos": {},
            "await_restart": False,
            "epoch": 0,
        }
        idle_alerts = tuple(cam_danger_overlay_html(False) for _ in alert_boxes)

        def _paths():
            out = []
            for cam, dest in zip(cam_refs, dests):
                path = (
                    _ensure_clip(cam, "origin")
                    if dest == cam["origin"]
                    else _existing(dest)
                )
                # 같은 경로여도 Gradio가 갱신을 건너뛰지 않게 update로 보냄
                out.append(gr.update(value=path) if path else gr.update())
            return out

        def _as_time(value):
            try:
                t = float(value)
            except (TypeError, ValueError):
                return None
            if t < 0 or t != t:
                return None
            return t

        def _bump_epoch():
            kpi_session["epoch"] = int(kpi_session.get("epoch") or 0) + 1
            return kpi_session["epoch"]

        def _effective_positions(positions):
            raw = positions if isinstance(positions, dict) else {}
            if kpi_session.get("await_restart"):
                # 재생 위치가 아직 안 오면 대기. 오면 집계 시작.
                # (예전: t<2.5 만 인정 → 첫 보고가 이미 3초 넘으면 KPI가 영원히 0)
                vals = [t for t in (_as_time(v) for v in raw.values()) if t is not None]
                if not vals:
                    return {}
                if any(t < 2.5 for t in vals):
                    kpi_session["max_pos"] = {}
                kpi_session["await_restart"] = False
            out = dict(kpi_session["max_pos"])
            for cam_id, value in raw.items():
                t = _as_time(value)
                if t is None:
                    continue
                prev = float(out.get(cam_id, 0.0))
                # 루프로 되감김 → 최고 위치 유지. 그 외에는 전진만 반영.
                if t + 1.0 < prev:
                    continue
                if t > prev:
                    out[cam_id] = t
            kpi_session["max_pos"] = out
            return out

        def new_session():
            """로그인 직후 한 번: KPI·알림을 0부터 다시 셈."""
            from .events import rebase_display_clock

            rebase_display_clock()
            kpi_session["started"] = False
            kpi_session["max_pos"] = {}
            kpi_session["await_restart"] = True
            _bump_epoch()
            _alert_bus_reset()
            reset_notify_state()

        def begin():
            paths = _paths()
            if not kpi_session["started"]:
                kpi_session["started"] = True
                kpi_session["max_pos"] = {}
                kpi_session["await_restart"] = True
                _bump_epoch()
                _alert_bus_reset()
                reset_notify_state()
                kpi = kpi_html(None)
                alerts = idle_alerts
                sound_html = f"<div class='sisun-restart-videos' data-reset-token='{uuid.uuid4().hex}' hidden></div>"
            else:
                kpi = gr.update()
                alerts = tuple(gr.update() for _ in alert_boxes)
                sound_html = gr.update()
            return (
                tuple(paths)
                + (True, {}, True, sound_html, kpi)
                + alerts
                + (gr.update(active=True),)
            )

        def refresh():
            """새로고침: 영상을 처음으로 되돌리고 KPI·알림을 0부터 다시 셈."""
            from .events import rebase_display_clock

            rebase_display_clock()
            load_df(force=True)
            kpi_session["started"] = True
            kpi_session["max_pos"] = {}
            kpi_session["await_restart"] = True
            _bump_epoch()
            _alert_bus_reset()
            reset_notify_state()
            paths = _paths()
            # 같은 파일이어도 브라우저 재생위치를 0으로 돌리도록 JS 마커
            restart = f"<div class='sisun-restart-videos' data-reset-token='{uuid.uuid4().hex}' hidden></div>"
            return (
                tuple(paths)
                + (True, {}, True, restart, kpi_html(None))
                + idle_alerts
                + (gr.update(active=True),)
            )

        def stop():
            """다른 탭/로그아웃 시 메인 틱만 멈춤. KPI·누적 위치는 유지."""
            n = len(vids)
            return (
                tuple(gr.update() for _ in range(n))
                + (
                    False,
                    gr.update(),
                    True,
                    gr.update(),
                    gr.update(),
                )
                + tuple(gr.update() for _ in alert_boxes)
                + (gr.update(active=False),)
            )

        def tick(on, positions, is_ready):
            n_alert = len(alert_boxes)
            noop = (gr.update(),) + tuple(gr.update() for _ in range(n_alert))
            if not on or not is_ready:
                return noop
            epoch = int(kpi_session.get("epoch") or 0)
            view = get_df()
            if view is None:
                view = peek_df()
            if view is None:
                return (kpi_html(None),) + idle_alerts
            raw = positions if isinstance(positions, dict) else {}
            effective = _effective_positions(raw)
            # 틱 도중 새로고침이 끼면 이전 집계로 KPI를 덮지 않음
            if (
                kpi_session.get("await_restart")
                or int(kpi_session.get("epoch") or 0) != epoch
            ):
                return (kpi_html(None),) + idle_alerts
            part = live_positions(view, effective)
            kpi_out = kpi_html(part)
            overlays = danger_overlay_updates(view, cam_refs, raw, window=12.0)
            if (
                kpi_session.get("await_restart")
                or int(kpi_session.get("epoch") or 0) != epoch
            ):
                return noop
            return (kpi_out,) + tuple(overlays)

        # sound: 새로고침 마커용. 종·소리는 독립 alert_sound 버스.
        outs = vids + [playing, playheads, ready, sound, kpis] + alert_boxes + [timer]
        tick_evt = timer.tick(
            tick,
            inputs=[playing, playheads, ready],
            outputs=[kpis] + alert_boxes,
            js=playback_inputs("sisun-wall", cams),
            concurrency_limit=1,
        )
        # 클릭 즉시 영상 되감기 + 진행 중 틱 취소 → 로딩만 되고 안 바뀌는 레이스 완화
        btn.click(
            refresh,
            outputs=outs,
            cancels=[tick_evt],
            concurrency_limit=1,
            js="() => { try { window.sisunRestartMainVideos && window.sisunRestartMainVideos(); } catch (e) {} }",
        )
        _attach_vid_timer(demo, vids, dests, cam_refs, "origin")
        demo._live_begin = begin
        demo._live_stop = stop
        demo._live_outs = outs
        demo._kpi_new_session = new_session
    return demo


def make_camera(cam):
    """카메라 1대 상세: 감지 영상 + 해당 구역 이벤트 라이브."""
    cam_id = cam["id"]
    title = cam_side_label(cam)
    with gr.Blocks() as demo:
        gr.HTML(title_html(f"{title} · 감지 관제"), elem_classes="t2-title-block")
        playing = gr.State(False)
        playheads = gr.JSON(value={}, visible=False)
        ready = gr.State(False)
        banner = gr.HTML()
        vids, dests, _cams, _alerts = _cam_wall(
            [cam],
            "detect",
            wall_id=f"sisun-wall-{cam_id}",
            expandable=False,
        )
        log = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        timer = gr.Timer(0.4, active=False)

        def _paths():
            out = []
            for dest in dests:
                path = (
                    _ensure_clip(cam, "detect")
                    if dest == cam["detect"]
                    else _existing(dest)
                )
                out.append(path if path else gr.update())
            return out

        def _start(force):
            view = peek_df() if not force else load_df(force=True)
            empty = view.iloc[0:0] if view is not None and len(view) else view
            paths = _paths()
            return tuple(paths) + (
                True,
                {},
                True,
                "",
                table_html(empty, allow_empty=True),
                gr.update(active=True),
            )

        def begin():
            return _start(False)

        def refresh():
            return _start(True)

        def stop():
            n = len(vids)
            return tuple(gr.update() for _ in range(n)) + (
                False,
                {},
                False,
                "",
                "",
                gr.update(active=False),
            )

        def tick(on, positions, is_ready):
            if not on or not is_ready:
                return gr.update(), gr.update()
            view = get_df()
            if view is None:
                view = load_df()
            elapsed = float((positions or {}).get(cam_id, 0.0))
            part = live_part(view, cam_id, None, elapsed)
            return (
                live_flash_html(part, elapsed, cam=cam),
                table_html(part, allow_empty=True),
            )

        outs = vids + [playing, playheads, ready, banner, log, timer]
        timer.tick(
            tick,
            inputs=[playing, playheads, ready],
            outputs=[banner, log],
            js=playback_inputs(f"sisun-wall-{cam_id}", [cam]),
            concurrency_limit=1,
        )
        btn.click(refresh, outputs=outs)
        demo._live_begin = begin
        demo._live_stop = stop
        demo._live_outs = outs
    return demo


def make_data():
    """운영 통계는 저장 사건 기준. 원본 관측 행을 사고 건수로 세지 않는다."""
    from .operations import operations_html

    with gr.Blocks() as demo:
        gr.HTML(title_html("운영 통계"), elem_classes="t2-title-block")
        period = gr.Dropdown(
            ["전체", "오늘 등록"], value="전체", label="사건 등록 기간"
        )
        stats = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        _attach_boot(demo, [stats], lambda _view: (operations_html(),))
        period.change(operations_html, inputs=[period], outputs=[stats])
        btn.click(operations_html, inputs=[period], outputs=[stats])
    return demo


def make_cases():
    """경보·조치 관리: 사건 목록·상세·단계 처리 (데이터는 API)."""
    from .case_ui import cases_shell_html

    with gr.Blocks() as demo:
        gr.HTML(cases_shell_html())
    return demo


def make_history():
    site_names = [s["name"] for s in SITES]
    picks = ["전체"] + site_names + [s["name"] for s in SCENARIOS]
    with gr.Blocks() as demo:
        gr.HTML(
            title_html("이벤트 이력 · 창고·유형으로 찾기"),
            elem_classes="t2-title-block",
        )
        btns = []
        # 두 그룹은 같은 격자 크기를 쓰며 기존 단일 조건 조회를 유지합니다.
        for label, names in (
            ("창고", ["전체"] + site_names),
            ("유형", [s["name"] for s in SCENARIOS]),
        ):
            gr.HTML(
                f"<div class='t2-pick-label' style='{INK_TITLE}'>{label}</div>",
                elem_classes="t2-title-block",
            )
            with gr.Row(elem_classes="t2-history-picks"):
                for name in names:
                    btns.append(gr.Button(name, elem_classes="t2-pick-btn"))
        gr.HTML("<p>화재의 확인 중·관측 소실은 경보와 구분한 상태 기록입니다.</p>")
        box = gr.HTML()

        def _from(view, name="전체"):
            from .events import part_site

            name = str(name or "전체").strip()
            if name == "전체":
                return table_html(view, newest_first=True, include_fire_status=True)
            site = next((s for s in SITES if s["name"] == name), None)
            if site is not None:
                return table_html(
                    part_site(view, site["id"]),
                    newest_first=True,
                    include_fire_status=True,
                )
            sid = next((s["id"] for s in SCENARIOS if s["name"] == name), None)
            if sid is None:
                return card("조건을 찾지 못했습니다.")
            return table_html(
                view[view["scenario"] == sid],
                newest_first=True,
                include_fire_status=True,
            )

        def _load(name="전체"):
            return _from(load_df(), name)

        _attach_boot(demo, [box], lambda view: (_from(view, "전체"),))
        for name, btn in zip(picks, btns):
            btn.click(lambda n=name: _load(n), outputs=box)
    return demo


def launch():
    os.environ.setdefault("GRADIO_DEFAULT_CONCURRENCY_LIMIT", "40")
    _BOOT_TIMERS.clear()
    demos = []
    for tab in TABS:
        kind = tab.get("kind")
        if kind == "main":
            demos.append((tab["name"], make_main(CAMERAS)))
        elif kind == "camera":
            cam = CAM_BY_ID[tab["camera_id"]]
            demos.append((tab["name"], make_camera(cam)))
        elif kind == "cases":
            demos.append((tab["name"], make_cases()))
        elif kind == "history":
            demos.append((tab["name"], make_history()))
        elif kind == "data":
            demos.append((tab["name"], make_data()))
    for _name, block in demos:
        t = getattr(block, "_boot_timer", None)
        if t is not None:
            _BOOT_TIMERS.append(t)
        vt = getattr(block, "_vid_timer", None)
        if vt is not None:
            _BOOT_TIMERS.append(vt)
    allowed = [str(DATA_ROOT), str(VIDEO_DIR), LOCAL, str(DATA_ROOT / "outputs")]
    os.makedirs(LOCAL, exist_ok=True)
    theme = make_theme()
    paper_idx = {
        i for i, t in enumerate(TABS) if t.get("kind") in ("history", "cases", "data")
    }
    with gr.Blocks(title=TITLE, fill_width=True, fill_height=True) as app:
        with gr.Column(
            visible=True, elem_id="sisun-gate", elem_classes="sisun-login-on"
        ) as login_box:
            with gr.Column(elem_classes="sisun-login-card"):
                gr.HTML(login_html())
                uid = gr.Textbox(
                    show_label=False,
                    placeholder="아이디",
                    elem_classes="sisun-login-input",
                )
                pw = gr.Textbox(
                    show_label=False,
                    placeholder="비밀번호",
                    type="password",
                    elem_classes="sisun-login-input",
                )
                err = gr.HTML()
                gr.HTML(login_foot())
                go = gr.Button("로그인", elem_classes="sisun-login-btn")
        user_st = gr.State("")
        with gr.Column(visible=False) as dash_box:
            head = gr.HTML(header_html())
            lives = []
            side_btns = []
            panels = []
            with gr.Row(elem_classes="sisun-dash-row"):
                with gr.Column(
                    elem_id="sisun-side",
                    elem_classes="sisun-side",
                    scale=0,
                    min_width=0,
                ):
                    gr.HTML(side_brand_html())
                    with gr.Column(elem_classes="sisun-side-nav"):
                        for i, (name, _block) in enumerate(demos):
                            tab = TABS[i] if i < len(TABS) else {}
                            side_btns.append(
                                gr.Button(
                                    name,
                                    elem_id=f"sisun-side-{tab.get('id') or i}",
                                    elem_classes="sisun-side-btn",
                                    variant="primary" if i == 0 else "secondary",
                                )
                            )
                    gr.HTML(theme_foot_html())
                    logout_btn = gr.Button("Logout", elem_classes="sisun-logout-btn")
                with gr.Column(elem_classes="sisun-body", scale=1):
                    for i, (name, block) in enumerate(demos):
                        with gr.Column(
                            visible=(i == 0), elem_classes="sisun-panel"
                        ) as panel:
                            if i in paper_idx:
                                with gr.Column(elem_classes="sisun-paper"):
                                    block.render()
                            else:
                                block.render()
                        panels.append(panel)
                        if hasattr(block, "_live_begin"):
                            lives.append((i, block))

            live_outs = []
            for _i, block in lives:
                live_outs.extend(block._live_outs)

            # 독립 알림 버스: 영상/탭 상태와 무관하게 #1 세션 시계로만 진행
            alert_sound = gr.HTML(elem_classes="t2-sound t2-sound-global")
            alert_timer = gr.Timer(0.4, active=False)
            alert_timer.tick(
                _alert_bus_tick,
                outputs=[alert_sound],
                concurrency_limit=1,
            )

            def pick(idx, uid):
                vis = [gr.update(visible=(i == idx)) for i in range(len(panels))]
                btns = [
                    gr.update(variant="primary" if i == idx else "secondary")
                    for i in range(len(side_btns))
                ]
                packed = []
                for i, block in lives:
                    # 알림은 독립 버스라 탭 전환과 무관. 각 탭 화면 틱만 on/off.
                    packed.extend(
                        block._live_begin() if i == idx else block._live_stop()
                    )
                return vis + btns + packed + [header_html(uid, TABS[idx]["name"])]

            def start_home_live(user):
                """로그인 직후 #1 메인 + 독립 알림 버스 시작."""
                if not user:
                    return list(gr.update() for _ in live_outs) + [gr.update()]
                packed = []
                for i, block in lives:
                    if i == 0 and hasattr(block, "_kpi_new_session"):
                        block._kpi_new_session()
                    packed.extend(block._live_begin() if i == 0 else block._live_stop())
                return packed + [_alert_bus_start()]

            side_outs = panels + side_btns + live_outs + [head]
            for idx, btn in enumerate(side_btns):
                btn.click(
                    lambda uid, idx=idx: pick(idx, uid),
                    inputs=[user_st],
                    outputs=side_outs,
                    concurrency_limit=None,
                )
        login_outs = [login_box, dash_box, err, head, user_st]
        hide_js = """() => {
  var g = document.getElementById('sisun-gate');
  if (!g) return;
  var hello = document.querySelector('.sisun-hello');
  var ok = hello && /님/.test(hello.textContent || '');
  var off = g.classList.contains('sisun-login-off') || g.classList.contains('hide');
  if (!ok && !off) return;
  g.classList.add('sisun-login-off', 'hide');
  g.classList.remove('sisun-login-on');
  g.style.setProperty('display','none','important');
  g.style.setProperty('visibility','hidden','important');
  g.style.setProperty('pointer-events','none','important');
  g.style.setProperty('z-index','-1','important');
  g.style.setProperty('opacity','0','important');
}"""
        home_outs = live_outs + [alert_timer]
        go.click(
            _login_flow,
            inputs=[uid, pw],
            outputs=login_outs,
            concurrency_limit=1,
        ).then(
            _after_login,
            inputs=[user_st],
            outputs=_BOOT_TIMERS,
            concurrency_limit=1,
        ).then(
            start_home_live,
            inputs=[user_st],
            outputs=home_outs,
            concurrency_limit=1,
        ).then(None, js=hide_js)
        pw.submit(
            _login_flow,
            inputs=[uid, pw],
            outputs=login_outs,
            concurrency_limit=1,
        ).then(
            _after_login,
            inputs=[user_st],
            outputs=_BOOT_TIMERS,
            concurrency_limit=1,
        ).then(
            start_home_live,
            inputs=[user_st],
            outputs=home_outs,
            concurrency_limit=1,
        ).then(None, js=hide_js)

        def _logout():
            _alert_bus_stop()
            return do_logout()

        logout_btn.click(
            _logout,
            outputs=[login_box, dash_box, err, head, user_st, uid, pw],
        )
    inbrowser = os.environ.get("SISUN_DESKTOP") != "1"
    port = int(os.environ.get("SISUN_UI_PORT", "7860"))
    app.queue(default_concurrency_limit=40)
    launch_kw = dict(
        inbrowser=inbrowser,
        allowed_paths=allowed,
        theme=theme,
        css=CSS,
        js=BOOT_JS,
        server_name="127.0.0.1",
        server_port=port,
        ssr_mode=False,
        max_threads=40,
    )
    if _FAVICON:
        launch_kw["favicon_path"] = _FAVICON

    # Gradio launch 가 FastAPI 앱을 교체하므로, HTTP 응답이 뜬 뒤에 라우트를 붙인다.
    def _mount_response_route():
        import time as _time
        import urllib.error
        import urllib.request

        from fastapi import Request

        from .alert_response import (
            apply_transition,
            case_detail,
            get_state_by_link,
            get_states_for_event_ids,
            history_for_link,
            list_cases,
            load_logs_into_memory,
            migrate_missing_assignees,
        )

        url = f"http://127.0.0.1:{port}/"
        for _ in range(120):
            try:
                urllib.request.urlopen(url, timeout=0.5)
                break
            except (urllib.error.URLError, TimeoutError, OSError):
                _time.sleep(0.25)
        _time.sleep(0.3)
        fastapi_app = getattr(app, "app", None)
        if fastapi_app is None:
            return
        if any(
            getattr(r, "path", "") == "/sisun/alert-response"
            for r in fastapi_app.routes
        ):
            return

        # 기동 시 조치 이력 1회 적재(폴링마다 재조회하지 않음)
        load_logs_into_memory()
        migrate_missing_assignees()

        @fastapi_app.post("/sisun/alert-response")
        async def _sisun_alert_response(request: Request):
            try:
                data = await request.json()
                result = apply_transition(data if isinstance(data, dict) else {})
                return result
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        @fastapi_app.get("/sisun/alert-response/state")
        async def _sisun_alert_response_state(request: Request):
            q = request.query_params
            link = str(q.get("link_key") or "").strip()
            eids = [x for x in str(q.get("event_ids") or "").split(",") if x.strip()]
            if link:
                return get_state_by_link(link)
            if eids:
                return get_states_for_event_ids(eids)
            return {
                "ok": False,
                "error": "link_key or event_ids required",
                "state": None,
            }

        @fastapi_app.get("/sisun/alert-response/history")
        async def _sisun_alert_response_history(request: Request):
            q = request.query_params
            link = str(q.get("link_key") or "").strip()
            eids = [x for x in str(q.get("event_ids") or "").split(",") if x.strip()]
            return history_for_link(link_key=link, event_ids=eids or None)

        @fastapi_app.get("/sisun/alert-cases")
        async def _sisun_alert_cases(request: Request):
            q = request.query_params
            open_only = str(q.get("open_only") or "1") not in ("0", "false", "False")
            filters = {
                "open_only": open_only,
                "status": str(q.get("status") or "all"),
                "cam_id": str(q.get("cam_id") or "all"),
                "scenario": str(q.get("scenario") or "all"),
                "severity": str(q.get("severity") or "all"),
                "assigned_to": str(q.get("assigned_to") or "all"),
                "date_from": str(q.get("date_from") or ""),
                "date_to": str(q.get("date_to") or ""),
            }
            return list_cases(filters)

        @fastapi_app.get("/sisun/alert-cases/detail")
        async def _sisun_alert_cases_detail(request: Request):
            link = str(request.query_params.get("link_key") or "").strip()
            if not link:
                return {"ok": False, "error": "link_key required"}
            return case_detail(link)

    threading.Thread(target=_mount_response_route, daemon=True).start()
    app.launch(**launch_kw)
