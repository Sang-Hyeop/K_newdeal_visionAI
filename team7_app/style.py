# 화면 색·로그인 CSS·시계 JS·Gradio 테마
import gradio as gr

from .config import PAGE_BG

CSS = """
@import url("https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800&display=swap");
html {
  --sisun-page: #0f172a; --sisun-header-bg: #020617; --sisun-side-bg: #0b1220;
  --sisun-title: #f8fafc; --sisun-card-bg: #1e293b; --sisun-card-fg: #f8fafc;
  --sisun-table-fg: #f8fafc; --sisun-table-bg: #1e293b; --sisun-th-bg: #334155; --sisun-muted: #cbd5e1;
  --sisun-line: #334155; --sisun-accent: #2563eb;
}
html.sisun-light {
  --sisun-page: #f1f5f9; --sisun-header-bg: #ffffff; --sisun-side-bg: #e8eef6;
  --sisun-title: #0f172a; --sisun-card-bg: #ffffff; --sisun-card-fg: #0f172a;
  --sisun-table-fg: #0f172a; --sisun-table-bg: #ffffff; --sisun-th-bg: #e2e8f0; --sisun-muted: #475569;
  --sisun-line: #cbd5e1; --sisun-accent: #2563eb;
}
footer { display: none !important; }
.gradio-container { max-width: 100% !important; padding: 0 18px 28px 18px !important; }
.t2-refresh, .t2-refresh button {
  background: #fbbf24 !important; color: #111827 !important;
  border: 2px solid #111827 !important; font-weight: 800 !important;
}
.tab-nav button.selected, .tab-nav button[aria-selected="true"] {
  background: #2563eb !important; color: #fff !important;
}
.t2-page-title { font-size: 1.35rem; font-weight: 800; margin: 0 0 8px 0; line-height: 1.3; }
.t2-table { width: 100%; border-collapse: collapse; font-size: 14px; }

/* 소리 빈칸·제목 상자: Gradio 테두리/여백을 화면에서 없앰 */
.t2-sound, .t2-sound.block, .t2-sound .block, .t2-sound .html-container, .t2-sound .prose {
  display: none !important; height: 0 !important; min-height: 0 !important;
  padding: 0 !important; margin: 0 !important; border: none !important; overflow: hidden !important;
}
.t2-title-block, .t2-title-block.block, .t2-title-block .block,
.t2-title-block .html-container, .t2-title-block .prose {
  border: none !important; background: transparent !important; box-shadow: none !important;
  padding: 0 !important; margin: 0 0 8px 0 !important; min-height: 0 !important;
}
.gradio-container .block:has(.html-container) {
  border: none !important; background: transparent !important; box-shadow: none !important;
  padding: 0 !important; min-height: 0 !important;
}
.html-container, .prose { border: none !important; min-height: 0 !important; padding: 0 !important; background: transparent !important; }

html, body, .gradio-container { background: var(--sisun-page) !important; color: var(--sisun-card-fg) !important; }
.tab-nav { background: var(--sisun-card-bg) !important; border: 1px solid var(--sisun-line) !important; border-radius: 10px !important; padding: 6px !important; }
.tab-nav button { color: var(--sisun-card-fg) !important; font-weight: 700 !important; opacity: 1 !important; }
.sisun-title, .sisun-sub, .sisun-meta, .t2-page-title { color: var(--sisun-title) !important; }
.t2-card, .t2-kpi { background: var(--sisun-card-bg) !important; border: 1px solid var(--sisun-line) !important; color: var(--sisun-card-fg) !important; border-radius: 12px; padding: 14px 16px; }
.t2-muted { color: var(--sisun-muted) !important; }
.t2-table th, .t2-table td {
  border: 1px solid #94a3b8 !important; padding: 8px 10px !important;
  color: #f8fafc !important; background: #1e293b !important;
}
.t2-table th { background: #334155 !important; }
.t2-pick-label { font-size: 16px; font-weight: 800; margin: 0 0 10px 0; color: #f8fafc !important; }
.t2-pick-btn, .t2-pick-btn button {
  background: #334155 !important; color: #ffffff !important;
  border: 1px solid #94a3b8 !important; font-weight: 700 !important;
}
.t2-stats-wrap { min-height: 72vh; }
.t2-stat-track {
  flex: 1; height: 32px; background: #334155; border-radius: 8px; overflow: hidden;
}
.t2-time-col { min-width: 44px; flex: 1; height: 100%;
  display: flex; flex-direction: column; align-items: center; justify-content: flex-end;
}
@keyframes sisunPulse {
  0%, 100% { opacity: 1; filter: brightness(1); }
  50% { opacity: .82; filter: brightness(1.25); }
}
.sisun-flash {
  text-align: center; font-weight: 900; letter-spacing: .14em;
  padding: 16px 12px; border-radius: 12px; margin: 0 0 12px 0;
  animation: sisunPulse .4s ease-in-out infinite;
}
.sisun-flash-hot {
  background: #ef4444 !important; color: #ffffff !important;
  font-size: 48px; line-height: 1.1;
  box-shadow: 0 0 0 6px rgba(239,68,68,.5), 0 0 48px #ef4444;
}
.sisun-flash-warn {
  background: #f59e0b !important; color: #111827 !important;
  font-size: 48px; line-height: 1.1;
  box-shadow: 0 0 0 6px rgba(245,158,11,.5), 0 0 48px #f59e0b;
}

/* #7 통합 알람, #8 이벤트 이력만 흰 바탕 */
.sisun-paper {
  --sisun-title: #111827; --sisun-card-bg: #ffffff; --sisun-card-fg: #111827;
  --sisun-table-fg: #111827; --sisun-table-bg: #ffffff; --sisun-th-bg: #e2e8f0; --sisun-muted: #334155;
  background: #ffffff !important; color: #111827 !important;
}
.sisun-paper, .sisun-paper .block, .sisun-paper .column, .sisun-paper .form,
.sisun-paper .panel, .sisun-paper .html-container, .sisun-paper .prose {
  background: #ffffff !important; color: #111827 !important;
}
.sisun-paper .t2-page-title, .sisun-paper .t2-pick-label { color: #111827 !important; }
.sisun-paper .t2-card, .sisun-paper .t2-kpi {
  background: #ffffff !important; color: #111827 !important; border: 1px solid #475569 !important;
}
.sisun-paper .t2-muted { color: #334155 !important; }
.sisun-paper .t2-table th, .sisun-paper .t2-table td {
  background: #ffffff !important; color: #111827 !important; border: 1px solid #475569 !important;
}
.sisun-paper .t2-table th { background: #e2e8f0 !important; color: #111827 !important; }
.sisun-paper .t2-pick-btn, .sisun-paper .t2-pick-btn button {
  background: #e2e8f0 !important; color: #111827 !important; border: 1px solid #475569 !important;
}
.sisun-paper .label-wrap, .sisun-paper .block-label, .sisun-paper .block-title, .sisun-paper .block-info {
  color: #334155 !important;
}
#sisun-gate.sisun-login-on:not(.hide), .sisun-login-on:not(.hide) {
  --body-text-color: #f8fafc !important;
  --block-label-text-color: #cbd5e1 !important;
  --block-title-text-color: #f8fafc !important;
  --block-info-text-color: #94a3b8 !important;
  --input-text-color: #ffffff !important;
  --input-background-fill: transparent !important;
  --input-border-color: rgba(186,210,255,.55) !important;
  --background-fill-primary: transparent !important;
  --background-fill-secondary: transparent !important;
  font-family: "Noto Sans KR", sans-serif !important;
  position: fixed !important; inset: 0 !important; z-index: 2147483000 !important;
  color: #f8fafc !important; overflow: hidden !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  min-height: 100vh !important; height: 100vh !important; width: 100vw !important;
  margin: 0 !important; padding: 0 !important;
  background:
    radial-gradient(900px 520px at 78% 8%, rgba(37,99,235,.28), transparent 58%),
    radial-gradient(700px 480px at 8% 92%, rgba(30,64,175,.22), transparent 55%),
    #050816 !important;
}
#sisun-gate.hide, .sisun-login-on.hide, #sisun-gate.sisun-login-off, .sisun-login-off {
  display: none !important;
  visibility: hidden !important;
  pointer-events: none !important;
  z-index: -1 !important;
  position: absolute !important;
  inset: auto !important;
  width: 0 !important;
  min-height: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
}
#sisun-gate > *:not(.sisun-login-card),
.sisun-login-on > *:not(.sisun-login-card),
.sisun-login-on .form:not(.sisun-login-card),
.sisun-login-on .gap:not(.sisun-login-card) {
  display: flex !important; align-items: center !important; justify-content: center !important;
  flex: 1 1 auto !important; width: 100% !important; height: 100% !important;
  margin: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important;
}
.sisun-login-on, .sisun-login-on .block, .sisun-login-on .html-container, .sisun-login-on .prose,
.sisun-login-on .form, .sisun-login-on .column {
  background: transparent !important; border: none !important; box-shadow: none !important;
}
.sisun-login-card .form, .sisun-login-card .gap {
  gap: 14px !important;
}
.sisun-login-bg {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
}
.sisun-login-bg svg { width: 100%; height: 100%; display: block; }
.sisun-login-brand {
  text-align: center; padding: 0 0 8px 0; position: relative; z-index: 1;
}
.sisun-login-kicker {
  font-size: 13px; letter-spacing: .28em; font-weight: 700; color: #93c5fd; margin-bottom: 8px;
}
.sisun-login-name {
  font-size: 34px; font-weight: 800; letter-spacing: .02em; line-height: 1.1;
  color: #ffffff; margin: 0 0 6px 0;
}
.sisun-login-on .sisun-login-card, .sisun-login-card {
  width: 420px !important; max-width: 90vw !important;
  flex: 0 0 auto !important; height: auto !important;
  border: 1px solid rgba(186,210,255,.28) !important; border-radius: 18px !important;
  padding: 28px 28px 24px 28px !important;
  background: rgba(8,16,48,.42) !important;
  backdrop-filter: blur(16px) saturate(1.15) !important;
  box-shadow: 0 20px 50px rgba(0,0,0,.35) !important;
  margin: auto !important; position: relative !important; z-index: 1 !important;
}
.sisun-login-card .block { padding: 0 !important; margin: 0 !important; min-height: 0 !important; }
.sisun-login-card .block-label, .sisun-login-card .label-wrap,
.sisun-login-card .block-info { display: none !important; }
#sisun-gate input:not([type="checkbox"]), #sisun-gate textarea,
.sisun-login-on input:not([type="checkbox"]), .sisun-login-on textarea,
.sisun-login-card input:not([type="checkbox"]), .sisun-login-card textarea {
  background: transparent !important; color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important; caret-color: #ffffff !important;
  border: 1.5px solid rgba(186,210,255,.55) !important; border-radius: 999px !important;
  box-shadow: none !important;
  font-size: 18px !important; min-height: 64px !important; height: 64px !important;
  padding: 18px 24px !important;
}
#sisun-gate input:not([type="checkbox"]):focus, .sisun-login-on input:not([type="checkbox"]):focus {
  border-color: #60a5fa !important; box-shadow: 0 0 0 3px rgba(59,130,246,.25) !important;
}
#sisun-gate input::placeholder, .sisun-login-on input::placeholder {
  color: #94a3b8 !important; -webkit-text-fill-color: #94a3b8 !important; opacity: 1 !important;
}
.sisun-login-meta {
  display: flex; align-items: center; justify-content: space-between;
  margin: 2px 2px 4px 2px; font-size: 13px; color: #cbd5e1;
}
.sisun-login-keep { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.sisun-login-keep input[type="checkbox"] {
  width: 15px; height: 15px; min-height: 15px !important; height: 15px !important;
  border-radius: 3px !important; padding: 0 !important; accent-color: #60a5fa;
}
.sisun-login-forgot { color: #cbd5e1; }
.sisun-login-btn { margin-top: 6px !important; }
.sisun-login-btn button, .sisun-login-btn button * {
  background: #ffffff !important; color: #0b1220 !important; -webkit-text-fill-color: #0b1220 !important;
  border: none !important; font-weight: 700 !important;
  font-size: 17px !important; min-height: 50px !important; border-radius: 999px !important;
}
.sisun-login-err {
  margin: 0; padding: 0 8px; text-align: center;
  color: #fca5a5; font-weight: 700; font-size: 13px;
  background: transparent; border: none;
}

/* 안 보이는 곳에 CCTV 영상을 미리 받아 둠. 재생은 하지 않음 */
.sisun-preload {
  position: fixed !important; left: -9999px !important; top: 0 !important;
  width: 8px !important; height: 8px !important; overflow: hidden !important;
  opacity: 0 !important; pointer-events: none !important; z-index: -1 !important;
}
.sisun-preload, .sisun-preload .block, .sisun-preload .html-container {
  min-height: 0 !important; padding: 0 !important; margin: 0 !important;
  border: none !important; background: transparent !important;
}

.sisun-header {
  display: grid; grid-template-columns: minmax(160px,1fr) auto minmax(160px,1fr);
  align-items: center; gap: 10px 16px;
  min-height: 56px; padding: 8px 16px; margin: 0 -18px 12px -18px;
  background: var(--sisun-header-bg) !important;
  border-bottom: 1px solid var(--sisun-line) !important; color: var(--sisun-card-fg);
}
.sisun-h-left, .sisun-h-right { display: flex; align-items: center; gap: 12px; min-width: 0; }
.sisun-h-right { justify-content: flex-end; flex-wrap: wrap; font-size: 13px; }
.sisun-h-center { text-align: center; }
.sisun-h-title { font-size: 1.35rem; font-weight: 800; line-height: 1.15; color: var(--sisun-title); letter-spacing: .02em; }
.sisun-h-sub { font-size: 12px; font-weight: 600; color: var(--sisun-muted); margin-top: 2px; }
.sisun-brand { display: inline-flex; align-items: center; gap: 8px; font-weight: 800; font-size: 15px; color: var(--sisun-title); white-space: nowrap; }
.sisun-brand-mark {
  width: 10px; height: 10px; border-radius: 2px; background: var(--sisun-accent);
  display: inline-block; flex: 0 0 10px;
}
.sisun-weather { white-space: nowrap; font-size: 13px; font-weight: 600; color: var(--sisun-muted); }
.sisun-hello { font-weight: 700; white-space: nowrap; }
.sisun-notice { color: var(--sisun-muted); white-space: nowrap; font-size: 12px; }
#sisun-clock { font-weight: 700; white-space: nowrap; }
@media (max-width: 1100px) {
  .sisun-header { grid-template-columns: 1fr 1fr; }
  .sisun-h-center { grid-column: 1 / -1; order: -1; }
}
.sisun-dash-row,
.sisun-dash-row > .form,
.sisun-dash-row > .gap {
  display: flex !important; flex-direction: row !important;
  flex-wrap: nowrap !important; align-items: stretch !important;
  width: 100% !important; min-width: 0 !important;
}
.sisun-body { min-width: 0 !important; flex: 1 1 auto !important; }
.sisun-body .tab-nav, .sisun-tabs .tab-nav, .sisun-body [role="tablist"] {
  display: none !important; height: 0 !important; overflow: hidden !important;
  padding: 0 !important; margin: 0 !important; border: none !important;
}
#sisun-side, .sisun-side {
  flex: 0 0 200px !important; min-width: 200px !important; max-width: 200px !important;
  background: var(--sisun-side-bg) !important; border: 1px solid var(--sisun-line) !important;
  border-radius: 10px !important; padding: 10px 8px 8px 8px !important; margin: 0 14px 0 0 !important;
  align-self: stretch !important; min-height: calc(100vh - 80px);
  display: flex !important; flex-direction: column !important;
}
#sisun-side .gap { gap: 4px !important; display: flex !important; flex-direction: column !important; flex: 1 1 auto !important; }
.sisun-side-brand {
  display: flex; align-items: center; gap: 8px;
  font-weight: 800; font-size: 14px; color: var(--sisun-title);
  padding: 4px 8px 10px 8px; border-bottom: 1px solid var(--sisun-line); margin-bottom: 6px;
}
.sisun-side-nav { flex: 1 1 auto !important; }
.sisun-side-nav .gap { gap: 2px !important; }
#sisun-side .sisun-side-btn { margin: 0 !important; padding: 0 !important; border: none !important; }
#sisun-side .sisun-side-btn button {
  width: 100% !important; min-height: 38px !important; border-radius: 8px !important;
  font-size: 13px !important; font-weight: 700 !important;
  text-align: left !important; justify-content: flex-start !important;
  background: transparent !important; color: var(--sisun-card-fg) !important;
  border: none !important; padding: 8px 10px 8px 12px !important; box-shadow: none !important;
}
#sisun-side .sisun-side-btn button::before {
  content: ""; display: inline-block; width: 8px; height: 8px; margin-right: 8px;
  border: 1.5px solid currentColor; border-radius: 2px; flex: 0 0 8px; opacity: .7;
}
.sisun-side-nav .sisun-side-btn:nth-child(1) button::before { border-radius: 1px; }
.sisun-side-nav .sisun-side-btn:nth-child(n+2):nth-child(-n+6) button::before { border-radius: 50%; }
.sisun-side-nav .sisun-side-btn:nth-child(7) button::before { border-radius: 8px 8px 2px 2px; }
.sisun-side-nav .sisun-side-btn:nth-child(8) button::before { height: 2px; border-top-width: 4px; border-bottom-width: 0; }
.sisun-side-nav .sisun-side-btn:nth-child(9) button::before { width: 10px; height: 6px; }
#sisun-side .primary button, #sisun-side button.primary {
  background: var(--sisun-accent) !important; color: #ffffff !important;
}
.sisun-theme {
  display: flex; align-items: center; gap: 8px; cursor: pointer;
  padding: 10px 8px; margin-top: 8px; border-top: 1px solid var(--sisun-line);
  color: var(--sisun-card-fg); font-size: 12px; font-weight: 700; user-select: none;
}
.sisun-theme-ico { width: 18px; text-align: center; font-size: 14px; }
.sisun-theme-label { flex: 1; }
.sisun-theme-sw {
  width: 34px; height: 18px; border-radius: 999px; background: #334155;
  border: 1px solid var(--sisun-line); position: relative; flex: 0 0 34px;
}
.sisun-theme-knob {
  position: absolute; top: 1px; left: 1px; width: 14px; height: 14px; border-radius: 50%;
  background: #e2e8f0; transition: left .15s ease;
}
html.sisun-light .sisun-theme-sw { background: #2563eb; }
html.sisun-light .sisun-theme-knob { left: 17px; background: #fff; }
.sisun-logout-btn { margin-top: 6px !important; }
.sisun-logout-btn button {
  width: 100% !important; min-height: 40px !important; border-radius: 8px !important;
  background: #1e293b !important; color: #e2e8f0 !important;
  border: 1px solid var(--sisun-line) !important; font-weight: 800 !important;
}
html.sisun-light .sisun-logout-btn button {
  background: #ffffff !important; color: #0f172a !important;
}
html.sisun-light .t2-table th, html.sisun-light .t2-table td {
  background: var(--sisun-table-bg) !important; color: var(--sisun-table-fg) !important;
  border-color: var(--sisun-line) !important;
}
html.sisun-light .t2-table th { background: var(--sisun-th-bg) !important; }
html.sisun-light .t2-pick-btn, html.sisun-light .t2-pick-btn button {
  background: #e2e8f0 !important; color: #0f172a !important; border-color: var(--sisun-line) !important;
}
.sisun-wall-row,
.sisun-wall-row > .gap {
  display: flex !important; flex-wrap: nowrap !important;
  align-items: stretch !important; min-width: 0 !important;
}
.sisun-cam { min-width: 0 !important; flex: 1 1 0 !important; }
.sisun-wall { position: relative !important; margin-top: 10px; }
.sisun-wall > .block:has(.sisun-wall-x) {
  position: absolute !important; top: 0; right: 0; z-index: 30;
  width: auto !important; min-height: 0 !important;
  padding: 0 !important; margin: 0 !important;
  background: transparent !important; border: none !important;
}
.sisun-wall-x {
  display: none; align-items: center; justify-content: center;
  width: 44px; height: 44px; border: none; border-radius: 10px;
  background: #334155; color: #ffffff; font-size: 28px; font-weight: 800;
  line-height: 1; cursor: pointer;
}
.sisun-wall.sisun-focus .sisun-wall-x { display: flex; }
.sisun-cam {
  position: relative !important; aspect-ratio: 16 / 9;
  background: #020617 !important; border: 1px solid #475569 !important;
  border-radius: 12px !important; overflow: hidden !important; cursor: pointer;
}
.sisun-cam > .block:has(.sisun-cam-tag) {
  position: absolute !important; top: 8px; left: 8px; z-index: 4;
  width: auto !important; min-height: 0 !important;
  padding: 0 !important; margin: 0 !important;
  background: transparent !important; border: none !important;
}
.sisun-cam-tag {
  background: rgba(2,6,23,.78); color: #fff; font-weight: 800; font-size: 13px;
  padding: 4px 10px; border-radius: 999px;
}
.sisun-cam video {
  width: 100% !important; height: 100% !important;
  object-fit: contain !important; background: #000 !important;
}
.sisun-cam .block, .sisun-cam .video-container, .sisun-cam .wrap,
.sisun-cam .container, .sisun-cam .sisun-cam-vid {
  height: 100% !important; min-height: 0 !important;
  border: none !important; background: transparent !important;
}
.sisun-wall.sisun-focus .sisun-wall-row:not(:has(.sisun-cam-on)) {
  display: none !important; height: 0 !important; min-height: 0 !important;
}
.sisun-wall.sisun-focus .sisun-cam { display: none !important; }
.sisun-wall.sisun-focus .sisun-cam.sisun-cam-on {
  display: block !important; flex: 1 1 100% !important;
  width: 100% !important; max-width: 100% !important;
  aspect-ratio: auto; min-height: 68vh; cursor: default;
}

"""

BOOT_JS = """
() => {
  var collect = function(root, sel, out) {
    if (!root) return;
    if (root.querySelectorAll) {
      root.querySelectorAll(sel).forEach(function(el) { out.push(el); });
    }
    var all = root.querySelectorAll ? root.querySelectorAll("*") : [];
    all.forEach(function(el) { if (el.shadowRoot) collect(el.shadowRoot, sel, out); });
  };
  var allOf = function(sel) {
    var out = [];
    collect(document, sel, out);
    return out;
  };
  window.__sisunSound = true;
  var seenOn = new WeakMap();
  var syncCctv = function() {
    allOf("video").forEach(function(v) {
      v.muted = true;
      v.defaultMuted = true;
      v.volume = 0;
      v.preload = "auto";
      v.setAttribute("playsinline", "true");
      if (v.closest(".sisun-preload")) {
        v.pause();
        if (v.readyState < 2) {
          try { v.load(); } catch (e) {}
        }
        return;
      }
      var box = v.getBoundingClientRect();
      var on = box.width > 8 && box.height > 8;
      var was = seenOn.get(v) === true;
      if (on && !was) {
        try { v.currentTime = 0; } catch (e) {}
        v.play().catch(function(){});
      } else if (!on) {
        v.pause();
        if (v.readyState < 2) {
          try { v.load(); } catch (e) {}
        }
      }
      seenOn.set(v, on);
    });
  };
  syncCctv();
  var tick = function() {
    var el = document.getElementById("sisun-clock");
    if (el) el.textContent = new Date().toLocaleString("ko-KR", {hour12: false});
  };
  tick();
  setInterval(tick, 1000);
  var lastWx = "--";
  var wxKo = {0:"맑음",1:"맑음",2:"구름조금",3:"흐림",45:"안개",48:"안개",51:"이슬비",53:"이슬비",55:"이슬비",61:"비",63:"비",65:"비",71:"눈",73:"눈",75:"눈",80:"소나기",81:"소나기",95:"뇌우",96:"뇌우"};
  var wxIco = {0:"☀",1:"☀",2:"⛅",3:"☁",45:"🌫",48:"🌫",51:"🌦",53:"🌦",61:"🌧",63:"🌧",65:"🌧",71:"❄",73:"❄",80:"🌦",95:"⛈"};
  var paintWx = function() {
    var el = document.getElementById("sisun-weather");
    if (el) el.textContent = lastWx;
  };
  var loadWx = function() {
    fetch("https://api.open-meteo.com/v1/forecast?latitude=36.0190&longitude=129.3435&current=temperature_2m,weather_code&timezone=Asia/Seoul")
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var cur = d && d.current ? d.current : null;
        if (!cur || cur.temperature_2m == null) return;
        var code = String(cur.weather_code);
        var ico = wxIco[code] || "·";
        var name = wxKo[code] || "날씨";
        lastWx = ico + " " + Number(cur.temperature_2m).toFixed(1) + "° " + name;
        paintWx();
      })
      .catch(function() { paintWx(); });
  };
  loadWx();
  setInterval(loadWx, 15 * 60 * 1000);
  var applyTheme = function(mode) {
    var light = mode === "light";
    document.documentElement.classList.toggle("sisun-light", light);
    try { sessionStorage.setItem("sisun-theme", light ? "light" : "dark"); } catch (e) {}
    var row = document.getElementById("sisun-theme-row");
    if (row) {
      var lab = row.querySelector(".sisun-theme-label");
      var ico = row.querySelector(".sisun-theme-ico");
      if (lab) lab.textContent = light ? "Light Mode" : "Dark Mode";
      if (ico) ico.textContent = light ? "☀" : "☽";
    }
  };
  try { applyTheme(sessionStorage.getItem("sisun-theme") || "dark"); } catch (e) { applyTheme("dark"); }
  var bindTheme = function() {
    var row = document.getElementById("sisun-theme-row");
    if (!row || row.__sisunBound) return;
    row.__sisunBound = true;
    row.addEventListener("click", function() {
      var now = document.documentElement.classList.contains("sisun-light") ? "dark" : "light";
      applyTheme(now);
    });
  };
  bindTheme();
  document.addEventListener("pointerdown", function() {
    try {
      var ctx = window.__sisunCtx || new (window.AudioContext || window.webkitAudioContext)();
      window.__sisunCtx = ctx;
      if (ctx.state === "suspended") ctx.resume();
    } catch (e) {}
    syncCctv();
  });
  var syncSide = function() {
    var tabs = allOf(".sisun-tabs .tab-nav button");
    if (!tabs.length) tabs = allOf(".sisun-body [role='tab']");
    var sides = allOf(".sisun-side-btn");
    tabs.forEach(function(t, i) {
      if (!sides[i]) return;
      var on = t.getAttribute("aria-selected") === "true" || t.classList.contains("selected");
      sides[i].classList.toggle("sisun-side-on", on);
    });
  };
  var wallClick = function(e) {
    var path = e.composedPath ? e.composedPath() : [];
    var hitX = null, hitCam = null, wall = null;
    path.forEach(function(n) {
      if (!n || !n.classList) return;
      if (n.classList.contains("sisun-wall-x")) hitX = n;
      if (n.classList.contains("sisun-cam")) hitCam = n;
      if (n.classList.contains("sisun-wall")) wall = n;
    });
    if (!wall && e.target && e.target.closest) {
      if (e.target.closest(".sisun-wall-x")) hitX = e.target.closest(".sisun-wall-x");
      hitCam = e.target.closest(".sisun-cam");
      wall = e.target.closest(".sisun-wall");
    }
    if (hitX && wall) {
      wall.classList.remove("sisun-focus");
      wall.querySelectorAll(".sisun-cam-on").forEach(function(el) {
        el.classList.remove("sisun-cam-on");
      });
      e.preventDefault();
      e.stopPropagation();
      syncCctv();
      return;
    }
    if (hitCam && wall && !wall.classList.contains("sisun-focus")) {
      wall.classList.add("sisun-focus");
      hitCam.classList.add("sisun-cam-on");
      e.preventDefault();
      e.stopPropagation();
      syncCctv();
    }
  };
  document.addEventListener("click", wallClick, true);
  syncSide();
  var timer = null;
  var hideGate = function() {
    var g = document.getElementById("sisun-gate");
    if (!g) return;
    var off = g.classList.contains("hide") || g.classList.contains("sisun-login-off");
    if (off) {
      g.style.setProperty("display", "none", "important");
      g.style.setProperty("visibility", "hidden", "important");
      g.style.setProperty("pointer-events", "none", "important");
      g.style.setProperty("z-index", "-1", "important");
    } else {
      g.style.removeProperty("display");
      g.style.removeProperty("visibility");
      g.style.removeProperty("pointer-events");
      g.style.removeProperty("z-index");
    }
  };
  var watch = new MutationObserver(function() {
    hideGate();
    syncCctv();
    syncSide();
    paintWx();
    bindTheme();
    try { applyTheme(sessionStorage.getItem("sisun-theme") || "dark"); } catch (e) {}
    if (timer) clearTimeout(timer);
    timer = setTimeout(function() { hideGate(); syncCctv(); syncSide(); paintWx(); }, 80);
  });
  hideGate();
  watch.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "style"] });
}
"""

def make_theme():
    return gr.themes.Soft(primary_hue="blue").set(
        body_background_fill=PAGE_BG,
        background_fill_primary=PAGE_BG,
        background_fill_secondary="#1e293b",
        block_background_fill="#1e293b",
        block_border_color="#334155",
        body_text_color="#e2e8f0",
        block_title_text_color="#e2e8f0",
        block_label_text_color="#cbd5e1",
    )
