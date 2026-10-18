# 탭 화면 조립·로그인 후 대시보드 실행
import os
import threading

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
from .sound import beep_html, notify
from .style import BOOT_JS, CSS, make_theme
from .ui import (
    card,
    do_login,
    do_logout,
    header_html,
    kpi_html,
    live_flash_html,
    login_foot,
    login_html,
    recent_alert_html,
    side_brand_html,
    stats_html,
    table_html,
    theme_foot_html,
    title_html,
)

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
        _fill, inputs=[got], outputs=list(outputs) + [got, timer],
        concurrency_limit=1,
    )
    demo._boot_timer = timer


def _cam_wall(cams, dest_key, wall_id="sisun-wall", captions=False, expandable=True):
    """카메라 그리드. dest_key: origin | detect.
    captions=True: 메인 소제목. expandable=False: 클릭 확대 없이 처음부터 크게.
    """
    vids = []
    dests = []
    cam_refs = []
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
        vid_h = 240 if len(cams) > 1 else (680 if not expandable else 420)
        for group in groups:
            with gr.Row(elem_classes="sisun-wall-row"):
                for cam in group:
                    with gr.Column(elem_classes="sisun-cam-slot", scale=1):
                        if captions:
                            gr.HTML(
                                f"<div class='sisun-cam-cap'>{cam_main_label(cam)}</div>"
                            )
                        with gr.Column(elem_classes="sisun-cam"):
                            if not captions:
                                gr.HTML(f"<div class='sisun-cam-tag'>{cam_tag(cam)}</div>")
                            # 파일이 있으면 처음부터 넣고, 없어도 타이머/탭 진입 시 채움
                            initial = _ensure_clip(cam, dest_key)
                            vids.append(
                                gr.Video(
                                    value=initial,
                                    autoplay=False,
                                    loop=True,
                                    include_audio=False,
                                    show_label=False,
                                    height=vid_h,
                                    elem_classes="sisun-cam-vid",
                                    elem_id=f"sisun-video-{wall_id}-{cam['id']}",
                                    buttons=[],
                                )
                            )
                            dests.append(cam[dest_key])
                            cam_refs.append(cam)
    return vids, dests, cam_refs


def _attach_vid_timer(demo, vids, dests, cams, dest_key):
    got = gr.State(False)
    vid_timer = gr.Timer(0.3, active=False)

    def _fill_vids(done):
        n = len(vids)
        if done:
            return tuple(gr.update() for _ in range(n)) + (True, gr.update(active=False))
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
        _fill_vids, inputs=[got], outputs=vids + [got, vid_timer],
        concurrency_limit=None,
    )
    demo._vid_timer = vid_timer


def make_main(cams):
    """메인 관제: 전 카메라 원본 영상 + KPI는 0부터 실시간 증가."""
    with gr.Blocks() as demo:
        kpis = gr.HTML(kpi_html(None))
        sound = gr.HTML(elem_classes="t2-sound")
        playing = gr.State(False)
        playheads = gr.JSON(value={}, visible=False)
        ready = gr.State(False)
        vids, dests, cam_refs = _cam_wall(cams, "origin", wall_id="sisun-wall", captions=True)
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        timer = gr.Timer(0.4, active=False)

        def _paths():
            out = []
            for cam, dest in zip(cam_refs, dests):
                path = _ensure_clip(cam, "origin") if dest == cam["origin"] else _existing(dest)
                out.append(path if path else gr.update())
            return out

        def _start(force):
            if force:
                load_df(force=True)
            paths = _paths()
            return (
                tuple(paths)
                + (True, {}, True, "", kpi_html(None), gr.update(active=True))
            )

        def begin():
            return _start(False)

        def refresh():
            return _start(True)

        def stop():
            n = len(vids)
            return tuple(gr.update() for _ in range(n)) + (
                False, {}, False, "", kpi_html(None), gr.update(active=False),
            )

        def tick(on, positions, is_ready):
            if not on or not is_ready:
                return gr.update(), gr.update()
            view = get_df()
            if view is None:
                view = peek_df()
            if view is None:
                return gr.update(), kpi_html(None)
            part = live_positions(view, positions)
            return beep_html(notify(part)), kpi_html(part)

        outs = vids + [playing, playheads, ready, sound, kpis, timer]
        timer.tick(
            tick, inputs=[playing, playheads, ready], outputs=[sound, kpis],
            js=playback_inputs("sisun-wall", cams), concurrency_limit=1,
        )
        btn.click(refresh, outputs=outs)
        _attach_vid_timer(demo, vids, dests, cam_refs, "origin")
        demo._live_begin = begin
        demo._live_stop = stop
        demo._live_outs = outs
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
        vids, dests, _cams = _cam_wall(
            [cam], "detect", wall_id=f"sisun-wall-{cam_id}", expandable=False,
        )
        log = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        sound = gr.HTML(elem_classes="t2-sound")
        timer = gr.Timer(0.4, active=False)

        def _paths():
            out = []
            for dest in dests:
                path = _ensure_clip(cam, "detect") if dest == cam["detect"] else _existing(dest)
                out.append(path if path else gr.update())
            return out

        def _start(force):
            view = peek_df() if not force else load_df(force=True)
            empty = view.iloc[0:0] if view is not None and len(view) else view
            paths = _paths()
            return (
                tuple(paths)
                + (True, {}, True, "", "", table_html(empty, allow_empty=True), gr.update(active=True))
            )

        def begin():
            return _start(False)

        def refresh():
            return _start(True)

        def stop():
            n = len(vids)
            return tuple(gr.update() for _ in range(n)) + (
                False, {}, False, "", "", "", gr.update(active=False),
            )

        def tick(on, positions, is_ready):
            if not on or not is_ready:
                return gr.update(), gr.update(), gr.update()
            view = get_df()
            if view is None:
                view = load_df()
            elapsed = float((positions or {}).get(cam_id, 0.0))
            part = live_part(view, cam_id, None, elapsed)
            return (
                beep_html(notify(part)),
                live_flash_html(part, elapsed),
                table_html(part, allow_empty=True),
            )

        outs = vids + [playing, playheads, ready, sound, banner, log, timer]
        timer.tick(
            tick, inputs=[playing, playheads, ready], outputs=[sound, banner, log],
            js=playback_inputs(f"sisun-wall-{cam_id}", [cam]), concurrency_limit=1,
        )
        btn.click(refresh, outputs=outs)
        demo._live_begin = begin
        demo._live_stop = stop
        demo._live_outs = outs
    return demo


def make_data():
    with gr.Blocks() as demo:
        gr.HTML(title_html("종합 데이터"), elem_classes="t2-title-block")
        stats = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        sound = gr.HTML(elem_classes="t2-sound")

        def _load():
            view = load_df(force=True)
            return beep_html(notify(view)), stats_html(view)

        outs = [sound, stats]
        _attach_boot(demo, outs, lambda view: (beep_html(notify(view)), stats_html(view)))
        btn.click(_load, outputs=outs)
    return demo


def make_alerts():
    with gr.Blocks() as demo:
        gr.HTML(title_html("통합 알람 · 창고 · 카메라 · 시각"), elem_classes="t2-title-block")
        box = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        sound = gr.HTML(elem_classes="t2-sound")

        def _from(view):
            col = "grade" if "grade" in view.columns else "status"
            danger = view[view[col].isin(["주의", "위험"])]
            return beep_html(notify(danger)), recent_alert_html(danger, limit=30)

        def _load(force=False):
            return _from(load_df(force=force))

        _attach_boot(demo, [sound, box], _from)
        btn.click(lambda: _load(True), outputs=[sound, box])
    return demo


def make_history():
    site_names = [s["name"] for s in SITES]
    picks = ["전체"] + site_names + [s["name"] for s in SCENARIOS]
    with gr.Blocks() as demo:
        gr.HTML(title_html("이벤트 이력 · 창고·유형으로 찾기"), elem_classes="t2-title-block")
        gr.HTML(
            f"<div class='t2-pick-label' style='{INK_TITLE}'>창고 · 유형 고르기</div>",
            elem_classes="t2-title-block",
        )
        btns = []
        with gr.Row():
            for name in picks:
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
                return table_html(part_site(view, site["id"]), newest_first=True, include_fire_status=True)
            sid = next((s["id"] for s in SCENARIOS if s["name"] == name), None)
            if sid is None:
                return card("조건을 찾지 못했습니다.")
            return table_html(view[view["scenario"] == sid], newest_first=True, include_fire_status=True)

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
        elif kind == "alerts":
            demos.append((tab["name"], make_alerts()))
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
    paper_idx = {i for i, t in enumerate(TABS) if t.get("kind") in ("alerts", "history")}
    with gr.Blocks(title=TITLE) as app:
        with gr.Column(visible=True, elem_id="sisun-gate", elem_classes="sisun-login-on") as login_box:
            with gr.Column(elem_classes="sisun-login-card"):
                gr.HTML(login_html())
                uid = gr.Textbox(show_label=False, placeholder="아이디", elem_classes="sisun-login-input")
                pw = gr.Textbox(show_label=False, placeholder="비밀번호", type="password", elem_classes="sisun-login-input")
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
                with gr.Column(elem_id="sisun-side", elem_classes="sisun-side", scale=0, min_width=0):
                    gr.HTML(side_brand_html())
                    with gr.Column(elem_classes="sisun-side-nav"):
                        for i, (name, _block) in enumerate(demos):
                            side_btns.append(
                                gr.Button(
                                    name,
                                    elem_classes="sisun-side-btn",
                                    variant="primary" if i == 0 else "secondary",
                                )
                            )
                    gr.HTML(theme_foot_html())
                    logout_btn = gr.Button("Logout", elem_classes="sisun-logout-btn")
                with gr.Column(elem_classes="sisun-body", scale=1):
                    for i, (name, block) in enumerate(demos):
                        with gr.Column(visible=(i == 0), elem_classes="sisun-panel") as panel:
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

            def pick(idx, uid):
                vis = [gr.update(visible=(i == idx)) for i in range(len(panels))]
                btns = [
                    gr.update(variant="primary" if i == idx else "secondary")
                    for i in range(len(side_btns))
                ]
                packed = []
                for i, block in lives:
                    packed.extend(block._live_begin() if i == idx else block._live_stop())
                return vis + btns + packed + [header_html(uid, TABS[idx]["name"])]

            def start_home_live(user):
                """로그인 직후 #1 메인 KPI·라이브 시계 시작."""
                if not user:
                    return tuple(gr.update() for _ in live_outs)
                packed = []
                for i, block in lives:
                    packed.extend(block._live_begin() if i == 0 else block._live_stop())
                return packed

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
        go.click(
            _login_flow, inputs=[uid, pw], outputs=login_outs, concurrency_limit=1,
        ).then(
            _after_login, inputs=[user_st], outputs=_BOOT_TIMERS, concurrency_limit=1,
        ).then(
            start_home_live, inputs=[user_st], outputs=live_outs, concurrency_limit=1,
        ).then(None, js=hide_js)
        pw.submit(
            _login_flow, inputs=[uid, pw], outputs=login_outs, concurrency_limit=1,
        ).then(
            _after_login, inputs=[user_st], outputs=_BOOT_TIMERS, concurrency_limit=1,
        ).then(
            start_home_live, inputs=[user_st], outputs=live_outs, concurrency_limit=1,
        ).then(None, js=hide_js)
        logout_btn.click(
            do_logout,
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
    app.launch(**launch_kw)
