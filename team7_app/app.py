# 탭 화면 조립·로그인 후 대시보드 실행
import os
import threading
import time

import gradio as gr

from .config import (
    DATA_ROOT,
    INK_TITLE,
    LOCAL,
    SCENARIOS,
    TABS,
    TITLE,
    VIDEO_DIR,
    VIDEO_FILES,
    WAREHOUSE_VIDEO,
    ZONES,
)
from .events import live_part, load_df, peek_df
from .media import demo_clip, origin_clip
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


def _existing(dest_name):
    dest = os.path.join(LOCAL, dest_name)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return dest
    return None


def _attach_boot(demo, outputs, build):
    """로그인 전에는 타이머를 안 돌림. 데이터 채워지면 바로 멈춤."""
    n = len(outputs)
    got = gr.State(False)
    timer = gr.Timer(0.5, active=True)

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
        concurrency_limit=None,
    )
    demo._boot_timer = timer

def make_main(cams):
    with gr.Blocks() as demo:
        kpis = gr.HTML()
        sound = gr.HTML(elem_classes="t2-sound")
        vids = []
        dests = []
        with gr.Column(elem_id="sisun-wall", elem_classes="sisun-wall"):
            gr.HTML(
                "<button type='button' class='sisun-wall-x' aria-label='close'>×</button>"
            )
            groups = [cams[:3], cams[3:]]
            for group in groups:
                with gr.Row(elem_classes="sisun-wall-row"):
                    for zone, dest in group:
                        with gr.Column(elem_classes="sisun-cam", scale=1):
                            gr.HTML(
                                f"<div class='sisun-cam-tag'>{zone['name']} · {zone['cam']}</div>"
                            )
                            vids.append(
                                gr.Video(
                                    value=None,
                                    autoplay=False,
                                    loop=True,
                                    include_audio=False,
                                    show_label=False,
                                    height=240,
                                    elem_classes="sisun-cam-vid",
                                    buttons=[],
                                )
                            )
                            dests.append(dest)
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        outs = [sound, kpis]
        _attach_boot(demo, outs, lambda view: (beep_html(notify(view)), kpi_html(view)))
        btn.click(
            lambda: (lambda v: (beep_html(notify(v)), kpi_html(v)))(load_df(force=True)),
            outputs=outs,
        )
        got = gr.State(False)
        vid_timer = gr.Timer(0.3, active=False)

        def _fill_vids(done):
            n = len(vids)
            if done:
                return tuple(gr.update() for _ in range(n)) + (True, gr.update(active=False))
            values = []
            ready = True
            for dest in dests:
                path = _existing(dest)
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
        demo._kpi_outs = outs
        demo._vid_timer = vid_timer
    return demo


def make_data():
    with gr.Blocks() as demo:
        gr.HTML(title_html("통합데이터"), elem_classes="t2-title-block")
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


def make_area(title, clip_fn, area_id, sids=None):
    with gr.Blocks() as demo:
        gr.HTML(title_html(title), elem_classes="t2-title-block")
        playing = gr.State(False)
        started_at = gr.State(0.0)
        ready = gr.State(False)
        banner = gr.HTML()
        vid = gr.Video(
            value=None, autoplay=False, loop=True,
            include_audio=False, show_label=False, height=640,
            elem_classes="sisun-cctv",
        )
        log = gr.HTML()
        btn = gr.Button("새로고침", elem_classes="t2-refresh")
        sound = gr.HTML(elem_classes="t2-sound")
        timer = gr.Timer(0.4, active=False)

        def _clip_path():
            try:
                path = clip_fn() if callable(clip_fn) else clip_fn
            except Exception:
                path = None
            return path if path and os.path.isfile(str(path)) else None

        def _start(force):
            view = peek_df() if not force else load_df(force=True)
            empty = view.iloc[0:0] if view is not None and len(view) else view
            return (
                _clip_path(), True, time.time(), True, "", "",
                table_html(empty, allow_empty=True),
                gr.update(active=True),
            )

        def begin():
            return _start(False)

        def refresh():
            return _start(True)

        def stop():
            return gr.update(), False, 0.0, False, "", "", "", gr.update(active=False)

        def tick(on, t0, is_ready):
            if not on or not is_ready:
                return gr.update(), gr.update(), gr.update()
            elapsed = time.time() - t0
            part = live_part(load_df(), area_id, sids, elapsed)
            return (
                beep_html(notify(part)),
                live_flash_html(part, elapsed),
                table_html(part, allow_empty=True),
            )

        outs = [vid, playing, started_at, ready, sound, banner, log, timer]
        timer.tick(
            tick, inputs=[playing, started_at, ready], outputs=[sound, banner, log],
            concurrency_limit=None,
        )
        btn.click(refresh, outputs=outs)
        demo._live_begin = begin
        demo._live_stop = stop
        demo._live_outs = outs
    return demo


def make_alerts():
    with gr.Blocks() as demo:
        gr.HTML(title_html("통합 알람 · 시각 · 위치 · 카메라"), elem_classes="t2-title-block")
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
    picks = ["전체"] + [s["name"] for s in SCENARIOS]
    with gr.Blocks() as demo:
        gr.HTML(title_html("이벤트 이력 · 유형으로 찾기"), elem_classes="t2-title-block")
        gr.HTML(f"<div class='t2-pick-label' style='{INK_TITLE}'>유형 고르기</div>", elem_classes="t2-title-block")
        btns = []
        with gr.Row():
            for name in picks:
                btns.append(gr.Button(name, elem_classes="t2-pick-btn"))
        box = gr.HTML()

        def _from(view, name="전체"):
            name = str(name or "전체").strip()
            if name != "전체":
                sid = next((s["id"] for s in SCENARIOS if s["name"] == name), None)
                if sid is None:
                    return card("그 유형을 찾지 못했습니다.")
                view = view[view["scenario"] == sid]
            return table_html(view, newest_first=True)

        def _load(name="전체"):
            return _from(load_df(), name)

        _attach_boot(demo, [box], lambda view: (_from(view, "전체"),))
        for name, btn in zip(picks, btns):
            btn.click(lambda n=name: _load(n), outputs=box)
    return demo


def launch():
    os.environ.setdefault("GRADIO_DEFAULT_CONCURRENCY_LIMIT", "40")
    main_files = [
        (ZONES[0], WAREHOUSE_VIDEO, "main_A.mp4"),
        (ZONES[1], VIDEO_FILES["collision"], "main_B.mp4"),
        (ZONES[2], VIDEO_FILES["zone"], "main_C.mp4"),
        (ZONES[3], VIDEO_FILES["dwell"], "main_D.mp4"),
        (ZONES[4], VIDEO_FILES["ppe"], "main_E.mp4"),
    ]
    clip_fns = {
        "A": lambda: demo_clip(num=5),
        "collision": lambda: demo_clip("collision"),
        "zone": lambda: demo_clip("zone"),
        "dwell": lambda: demo_clip("dwell"),
        "ppe": lambda: demo_clip("ppe"),
    }

    def _warm():
        try:
            load_df()
        except Exception:
            pass
        for _zone, fname, dest in main_files:
            try:
                origin_clip(fname, dest)
            except Exception:
                pass
        for fn in clip_fns.values():
            try:
                fn()
            except Exception:
                pass

    threading.Thread(target=_warm, daemon=True).start()
    main_cams = [(zone, dest) for zone, _fname, dest in main_files]
    demos = [
        (TABS[0]["name"], make_main(main_cams)),
        (TABS[1]["name"], make_area("A구역", clip_fns["A"], "A", ["collision", "ppe", "dwell"])),
        (TABS[2]["name"], make_area("B구역", clip_fns["collision"], "B", ["collision"])),
        (TABS[3]["name"], make_area("C구역", clip_fns["zone"], "C", ["zone"])),
        (TABS[4]["name"], make_area("D구역", clip_fns["dwell"], "D")),
        (TABS[5]["name"], make_area("E구역", clip_fns["ppe"], "E", ["ppe"])),
        (TABS[6]["name"], make_alerts()),
        (TABS[7]["name"], make_history()),
        (TABS[8]["name"], make_data()),
    ]
    allowed = [str(DATA_ROOT), str(VIDEO_DIR), LOCAL, str(DATA_ROOT / "outputs")]
    os.makedirs(LOCAL, exist_ok=True)
    theme = make_theme()
    with gr.Blocks(title=TITLE, theme=theme, css=CSS, js=BOOT_JS) as app:
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
                with gr.Column(elem_id="sisun-side", elem_classes="sisun-side", scale=0, min_width=200):
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
                            if i in (6, 7):
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

            side_outs = panels + side_btns + live_outs + [head]
            for idx, btn in enumerate(side_btns):
                btn.click(
                    lambda uid, idx=idx: pick(idx, uid),
                    inputs=[user_st],
                    outputs=side_outs,
                    concurrency_limit=None,
                )
        outs = [login_box, dash_box, err, head, user_st]
        hide_js = """() => {
  var hello = document.querySelector('.sisun-hello');
  var g = document.getElementById('sisun-gate');
  if (g && hello && /님/.test(hello.textContent || '')) {
    g.classList.add('sisun-login-off');
    g.classList.remove('sisun-login-on');
    g.style.setProperty('display','none','important');
    g.style.setProperty('visibility','hidden','important');
    g.style.setProperty('pointer-events','none','important');
    g.style.setProperty('z-index','-1','important');
  }
}"""
        go.click(do_login, inputs=[uid, pw], outputs=outs).then(None, js=hide_js)
        pw.submit(do_login, inputs=[uid, pw], outputs=outs).then(None, js=hide_js)
        logout_btn.click(
            do_logout,
            outputs=[login_box, dash_box, err, head, user_st, uid, pw],
        )
    inbrowser = os.environ.get("SISUN_DESKTOP") != "1"
    port = int(os.environ.get("SISUN_UI_PORT", "7860"))
    app.queue(default_concurrency_limit=40)
    app.launch(
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
