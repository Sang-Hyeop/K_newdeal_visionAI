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
/* 전체화면: Gradio Soft 기본 가운데 고정폭(잘린 느낌) 제거 */
html, body {
  width: 100% !important; max-width: 100% !important;
  margin: 0 !important; padding: 0 !important;
  overflow-x: hidden !important;
}
html .gradio-container,
.gradio-container,
.gradio-container.gradio-container,
main,
.main,
.app,
.wrap,
.contain,
.fillable,
[class*="svelte"] > .main {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
  box-sizing: border-box !important;
}
.gradio-container {
  padding: 0 12px 20px 12px !important;
}
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

/* Gradio 기본 Warning 토스트는 라이트모드 글자색이 깨져서 숨기고 커스텀 스택 사용 */
.toast-wrap,
div.toast-wrap,
.toastify {
  display: none !important;
}

/* 우측 상단 종: 클릭으로 알림창 열기/닫기. 음소거는 창 안 버튼 */
#sisun-bell-wrap {
  position: fixed; top: 10px; right: 28px; z-index: 99999;
  width: auto; pointer-events: none;
  padding: 6px; /* 배지·원형이 잘리지 않게 */
  box-sizing: content-box;
}
.sisun-bell-btn {
  pointer-events: auto;
  position: relative;
  width: 42px; height: 42px; padding: 0; margin: 0;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, .4);
  background: #0f172a;
  color: #f8fafc;
  box-shadow: 0 8px 22px rgba(2, 6, 23, .35);
  cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}
.sisun-bell-btn:hover { border-color: rgba(147, 197, 253, .8); }
.sisun-bell-btn svg { width: 20px; height: 20px; display: block; }
.sisun-bell-btn .sisun-bell-slash { display: none; }
.sisun-bell-btn.is-muted .sisun-bell-on { display: none; }
.sisun-bell-btn.is-muted .sisun-bell-slash { display: block; }
.sisun-bell-badge {
  position: absolute; top: -4px; right: -4px;
  min-width: 18px; height: 18px; padding: 0 5px;
  border-radius: 999px; font-size: 11px; font-weight: 800;
  display: none; align-items: center; justify-content: center;
  background: #ef4444; color: #fff !important;
  border: 2px solid #0f172a;
  pointer-events: none;
}
.sisun-bell-badge.has-items { display: inline-flex; }
.sisun-bell-badge.is-warn { background: #d97706; }

/* 알림창: 기본 숨김. 종 클릭 시에만 표시 */
#sisun-alert-rail {
  position: fixed;
  top: 64px;
  right: 10px;
  width: 220px;
  max-height: min(70vh, 560px);
  bottom: auto;
  z-index: 99990;
  display: none;
  flex-direction: column;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, .28);
  background: rgba(15, 23, 42, .96);
  color: #f8fafc !important;
  box-shadow: 0 12px 32px rgba(2, 6, 23, .4);
  overflow: hidden;
  pointer-events: auto;
}
#sisun-alert-rail.is-open { display: flex; }
.sisun-rail-head {
  flex: 0 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; padding: 8px 10px;
  border-bottom: 1px solid rgba(148, 163, 184, .22);
  font-size: 12px; font-weight: 800;
}
.sisun-rail-actions {
  display: flex; align-items: center; gap: 4px; flex: 0 0 auto;
}
.sisun-rail-mute-btn,
.sisun-rail-read-btn {
  flex: 0 0 auto;
  margin: 0; padding: 3px 7px;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, .4);
  background: rgba(30, 41, 59, .9);
  color: #e2e8f0 !important;
  font-size: 10px; font-weight: 700;
  line-height: 1.2; white-space: nowrap;
  cursor: pointer;
}
.sisun-rail-mute-btn:hover,
.sisun-rail-read-btn:hover {
  border-color: rgba(147, 197, 253, .75);
  color: #fff !important;
}
.sisun-rail-mute-btn.is-muted {
  border-color: rgba(248, 113, 113, .55);
  color: #fecaca !important;
}
.sisun-bell-list,
.sisun-rail-list {
  flex: 1 1 auto; min-height: 0;
  display: flex; flex-direction: column; gap: 6px;
  overflow-x: hidden; overflow-y: auto;
  padding: 8px;
  -webkit-overflow-scrolling: touch;
}
.sisun-bell-empty,
.sisun-rail-empty {
  padding: 14px 6px; text-align: center;
  font-size: 11px; font-weight: 700; opacity: .7; line-height: 1.35;
}
.sisun-toast {
  border-radius: 8px;
  padding: 7px 8px;
  border: 1px solid rgba(148, 163, 184, .25);
  background: rgba(2, 6, 23, .55);
  color: #f8fafc !important;
}
.sisun-toast * { color: inherit !important; }
.sisun-toast-head {
  display: flex; align-items: flex-start; gap: 6px;
  font-size: 12px; font-weight: 800; margin-bottom: 3px;
  line-height: 1.3; word-break: keep-all;
}
.sisun-toast-head > span:last-child {
  flex: 1 1 auto; min-width: 0;
}
.sisun-toast-ico {
  width: 14px; height: 14px; border-radius: 3px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 900; flex: 0 0 auto;
}
.sisun-toast-warn .sisun-toast-ico { background: #fbbf24; color: #111827 !important; }
.sisun-toast-hot .sisun-toast-ico { background: #ef4444; color: #ffffff !important; }
.sisun-toast-text {
  font-size: 11px; font-weight: 700; line-height: 1.3;
  color: #f8fafc !important;
}
.sisun-toast-meta {
  margin-top: 3px;
  font-size: 10px; font-weight: 700; line-height: 1.35;
  opacity: .9;
}
.sisun-toast-ack {
  display: inline-block; margin-top: 4px; padding: 1px 6px;
  border-radius: 4px; font-size: 10px; font-weight: 800;
  border: 1px solid rgba(148, 163, 184, .45);
}
.sisun-toast-ack.is-pending {
  color: #fde68a !important;
  border-color: rgba(251, 191, 36, .55);
}
.sisun-toast-ack.is-done {
  color: #94a3b8 !important;
  border-color: rgba(148, 163, 184, .35);
}
.sisun-toast.is-acked { opacity: .72; }
.sisun-toast-actions {
  display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap;
}
.sisun-toast-actions button {
  margin: 0; padding: 2px 7px;
  border-radius: 5px;
  border: 1px solid rgba(148, 163, 184, .4);
  background: rgba(30, 41, 59, .85);
  color: #e2e8f0 !important;
  font-size: 10px; font-weight: 700; cursor: pointer;
}
.sisun-rail-note {
  padding: 4px 10px 0;
  font-size: 9px; font-weight: 700; line-height: 1.3;
  opacity: .65;
}
html.sisun-light .sisun-bell-btn {
  background: #ffffff; color: #0f172a;
  border-color: #cbd5e1;
  box-shadow: 0 8px 22px rgba(15, 23, 42, .12);
}
html.sisun-light .sisun-bell-badge { border-color: #ffffff; }
html.sisun-light #sisun-alert-rail {
  background: rgba(255, 255, 255, .98);
  color: #0f172a !important;
  border-color: #cbd5e1;
  box-shadow: 0 12px 32px rgba(15, 23, 42, .14);
}
html.sisun-light .sisun-rail-mute-btn,
html.sisun-light .sisun-rail-read-btn {
  background: #f8fafc;
  color: #334155 !important;
  border-color: #cbd5e1;
}
html.sisun-light .sisun-rail-mute-btn:hover,
html.sisun-light .sisun-rail-read-btn:hover {
  color: #0f172a !important;
  border-color: #94a3b8;
}
html.sisun-light .sisun-rail-mute-btn.is-muted {
  border-color: #fca5a5;
  color: #b91c1c !important;
}
html.sisun-light .sisun-toast {
  background: #f8fafc !important;
  color: #0f172a !important;
  border-color: #e2e8f0;
}
html.sisun-light .sisun-toast-text { color: #0f172a !important; }

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
/* login-off 가 login-on 보다 항상 이기도록 (둘 다 붙는 Gradio 갱신 대비) */
#sisun-gate.hide,
#sisun-gate.sisun-login-off,
#sisun-gate.sisun-login-on.sisun-login-off,
#sisun-gate.sisun-login-on.hide,
.sisun-login-on.hide,
.sisun-login-off {
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
  opacity: 0 !important;
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
  margin: 8px 0 0 0; padding: 0 4px; text-align: center;
  color: #ef4444 !important; font-weight: 700; font-size: 13px; line-height: 1.45;
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

:root {
  --sisun-side-w: 200px;
  --sisun-side-gap: 38px; /* 사이드바↔본문 약 1cm */
}
.sisun-header {
  display: grid; grid-template-columns: minmax(160px,1fr) auto minmax(200px,1fr);
  align-items: center; gap: 10px 20px;
  min-height: 56px; padding: 8px 12px; margin: 0 -12px 12px -12px;
  background: var(--sisun-header-bg) !important;
  border-bottom: 1px solid var(--sisun-line) !important; color: var(--sisun-card-fg);
  box-sizing: border-box !important;
  width: calc(100% + 24px) !important;
  max-width: none !important;
  border-radius: 0 !important;
}
/* 왼쪽은 끝에 붙이고, 오른쪽은 종 아이콘 공간 넉넉히 */
html .sisun-header,
html.sisun-side-closed .sisun-header,
html:not(.sisun-side-closed) .sisun-header {
  padding-left: 12px !important;
  padding-right: 88px !important;
}
.sisun-h-left, .sisun-h-right { display: flex; align-items: center; gap: 12px; min-width: 0; }
/* 사이드바 토글 — 둥근 다크 칩 + CSS-only 햄버거/접기 (빈 태그 없이) */
.sisun-side-toggle {
  --sisun-tog-bg: #252c39;
  --sisun-tog-border: rgba(186, 198, 220, .42);
  --sisun-tog-icon: #e8eef8;
  position: relative; flex: 0 0 38px; width: 38px; height: 38px; padding: 0; margin: 0;
  border: 1px solid var(--sisun-tog-border) !important; border-radius: 11px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,0) 45%),
    var(--sisun-tog-bg) !important;
  color: var(--sisun-tog-icon) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.1),
    0 0 0 1px rgba(0,0,0,.28),
    0 4px 14px rgba(0,0,0,.32) !important;
  cursor: pointer; display: inline-flex !important; align-items: center; justify-content: center;
  transition: border-color .18s ease, box-shadow .18s ease, transform .12s ease, background .18s ease;
  -webkit-appearance: none; appearance: none; outline: none;
}
.sisun-side-toggle:hover {
  border-color: rgba(210, 222, 245, .75) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.14),
    0 0 0 1px rgba(37,99,235,.28),
    0 6px 18px rgba(0,0,0,.38) !important;
}
.sisun-side-toggle:active { transform: scale(.96); }
html.sisun-light .sisun-side-toggle {
  --sisun-tog-bg: #eef2f7;
  --sisun-tog-border: rgba(71, 85, 105, .35);
  --sisun-tog-icon: #0f172a;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.9),
    0 1px 2px rgba(15,23,42,.08) !important;
}
/* 열린 상태: « 접기 (버튼 pseudo만 사용 — Gradio HTML sanitize 대비) */
.sisun-side-toggle::before,
.sisun-side-toggle::after {
  content: ""; position: absolute; top: 50%; margin-top: -4px; width: 8px; height: 8px;
  border-left: 2.2px solid currentColor; border-bottom: 2.2px solid currentColor;
  transform: rotate(45deg); border-radius: 0 0 0 1px; pointer-events: none;
}
.sisun-side-toggle::before { left: 10px; }
.sisun-side-toggle::after { left: 17px; }
/* 닫힌 상태: 둥근 햄버거 3줄 */
html.sisun-side-closed .sisun-side-toggle::before {
  top: 50%; left: 11px; right: 11px; width: auto; height: 2px; margin-top: -1px;
  border: none; border-radius: 999px; transform: none; background: currentColor;
  box-shadow: 0 -5px 0 currentColor, 0 5px 0 currentColor;
}
html.sisun-side-closed .sisun-side-toggle::after { display: none; }
/* Gradio 6 가 붙이는 .gradio-container .contain 선택자보다 특이도를 높여 접기 */
html.sisun-side-closed .gradio-container .contain #sisun-side,
html.sisun-side-closed .gradio-container .contain .sisun-side,
html.sisun-side-closed #sisun-side,
html.sisun-side-closed .sisun-side {
  flex: 0 0 0 !important; flex-basis: 0 !important; flex-grow: 0 !important; flex-shrink: 0 !important;
  width: 0 !important; min-width: 0 !important; max-width: 0 !important;
  padding: 0 !important; margin: 0 !important; border: 0 !important;
  overflow: hidden !important; opacity: 0 !important; visibility: hidden !important;
  pointer-events: none !important; transform: translateX(-8px);
}
#sisun-side, .sisun-side {
  transition: flex-basis .22s ease, max-width .22s ease, opacity .18s ease, margin .22s ease;
}
.sisun-h-right {
  flex-direction: column; align-items: flex-end; justify-content: center;
  gap: 4px; font-size: 13px; text-align: right; line-height: 1.4;
  padding-right: 8px;
  margin-right: 0;
  overflow: visible !important;
}
.sisun-h-right .sisun-hello,
.sisun-h-right .sisun-clock,
.sisun-h-right .sisun-notice {
  white-space: nowrap;
  padding-right: 2px;
}
.sisun-h-center { text-align: center; }
.sisun-h-title { font-size: 1.35rem; font-weight: 800; line-height: 1.15; color: var(--sisun-title); letter-spacing: .02em; }
.sisun-h-sub { font-size: 12px; font-weight: 600; color: var(--sisun-muted); margin-top: 2px; }
.sisun-brand { display: inline-flex; align-items: center; gap: 8px; font-weight: 800; font-size: 15px; color: var(--sisun-title); white-space: nowrap; }
.sisun-brand-mark {
  width: 10px; height: 10px; border-radius: 2px; background: var(--sisun-accent);
  display: inline-block; flex: 0 0 10px;
}
.sisun-weather {
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  min-width: 0; line-height: 1.3; color: var(--sisun-muted);
}
.sisun-weather-place { font-size: 12px; font-weight: 700; white-space: nowrap; color: var(--sisun-card-fg); }
.sisun-weather-data { font-size: 13px; font-weight: 600; white-space: nowrap; }
.sisun-hello { font-weight: 700; white-space: nowrap; }
.sisun-clock { font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums; }
.sisun-notice { color: var(--sisun-muted); white-space: nowrap; font-size: 12px; }
@media (max-width: 1100px) {
  .sisun-header { grid-template-columns: 1fr 1fr; }
  .sisun-h-center { grid-column: 1 / -1; order: -1; }
}
.sisun-dash-row,
.sisun-dash-row > .form,
.sisun-dash-row > .gap {
  display: flex !important; flex-direction: row !important;
  flex-wrap: nowrap !important; align-items: flex-start !important;
  width: 100% !important; min-width: 0 !important;
  gap: 0 !important;
}
/* Gradio 래퍼가 사이드 칸을 또 차지하지 않게 */
.sisun-dash-row > .gap > *:has(#sisun-side),
.sisun-dash-row > .form > *:has(#sisun-side),
.sisun-dash-row > *:has(#sisun-side) {
  flex: 0 0 0 !important;
  width: 0 !important; min-width: 0 !important; max-width: 0 !important;
  padding: 0 !important; margin: 0 !important; border: none !important;
  overflow: visible !important; background: transparent !important;
}
/* 사이드는 fixed라 flex 공간을 안 먹고, 본문만 왼쪽 여백으로 피함 */
html:not(.sisun-side-closed) .sisun-dash-row {
  padding-left: calc(var(--sisun-side-w) + var(--sisun-side-gap)) !important; /* 200 + 38 ≈ 1cm */
  box-sizing: border-box !important;
}
html.sisun-side-closed .sisun-dash-row { padding-left: 0 !important; }
.sisun-body {
  min-width: 0 !important; flex: 1 1 auto !important;
  width: 100% !important; max-width: 100% !important;
}
.sisun-body .tab-nav, .sisun-tabs .tab-nav, .sisun-body [role="tablist"] {
  display: none !important; height: 0 !important; overflow: hidden !important;
  padding: 0 !important; margin: 0 !important; border: none !important;
}
#sisun-side, .sisun-side {
  /* 본문 스크롤과 분리 — 화면 왼쪽 고정. flex 칸은 0으로 두어 이중 여백 방지 */
  position: fixed !important;
  top: 72px !important;
  left: 18px !important;
  z-index: 40 !important;
  width: var(--sisun-side-w) !important;
  flex: 0 0 0 !important;
  min-width: 0 !important;
  max-width: none !important;
  background: var(--sisun-side-bg) !important; border: 1px solid var(--sisun-line) !important;
  border-radius: 10px !important; padding: 10px 8px 8px 8px !important; margin: 0 !important;
  height: calc(100vh - 84px) !important;
  max-height: calc(100vh - 84px) !important;
  min-height: 0 !important;
  overflow: hidden !important;
  display: flex !important; flex-direction: column !important;
  box-sizing: border-box !important;
}
#sisun-side > .gap,
#sisun-side .gap {
  gap: 4px !important; display: flex !important; flex-direction: column !important;
  flex: 1 1 auto !important; min-height: 0 !important; overflow: hidden !important;
}
.sisun-side-brand {
  display: flex; align-items: center; gap: 8px; flex: 0 0 auto !important;
  font-weight: 800; font-size: 14px; color: var(--sisun-title);
  padding: 4px 8px 10px 8px; border-bottom: 1px solid var(--sisun-line); margin-bottom: 6px;
}
.sisun-side-nav {
  flex: 1 1 auto !important; min-height: 0 !important;
  overflow-x: hidden !important; overflow-y: auto !important;
  -webkit-overflow-scrolling: touch;
}
.sisun-side-nav .gap { gap: 2px !important; overflow: visible !important; min-height: 0 !important; }
.sisun-theme, #sisun-side button.sisun-logout-btn, #sisun-side .sisun-logout-btn {
  flex: 0 0 auto !important;
}
/* Gradio 6: elem_classes 가 button 자체에 붙음 — 래퍼만 리셋, 버튼은 다크 칩 */
#sisun-side .sisun-side-btn:not(button) {
  margin: 0 0 4px 0 !important; padding: 0 !important; border: none !important;
  background: transparent !important; box-shadow: none !important;
}
#sisun-side button.sisun-side-btn,
#sisun-side .sisun-side-nav button.sisun-side-btn {
  position: relative !important;
  width: 100% !important; min-height: 40px !important; border-radius: 10px !important;
  font-size: 13px !important; font-weight: 700 !important;
  text-align: left !important; justify-content: flex-start !important;
  white-space: pre-line !important; line-height: 1.4 !important;
  background: #1a2230 !important;
  background-image: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,0) 55%) !important;
  color: #e8eef8 !important;
  border: 1px solid rgba(186, 198, 220, .28) !important;
  padding: 8px 28px 8px 12px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 2px 6px rgba(0,0,0,.22) !important;
}
/* 사이드바 확인 필요 표시 (위험 구역) */
.sisun-side-need {
  position: absolute; top: 50%; right: 8px; transform: translateY(-50%);
  width: 18px; height: 18px; border-radius: 999px;
  background: #ef4444; color: #fff !important;
  font-size: 10px; font-weight: 900; line-height: 1;
  display: none; align-items: center; justify-content: center;
  pointer-events: none; z-index: 2;
  box-shadow: 0 0 0 2px rgba(15, 23, 42, .35);
}
.sisun-side-need.is-on { display: inline-flex; }
html.sisun-light .sisun-side-need {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, .9);
}
#sisun-side button.sisun-side-btn:hover {
  border-color: rgba(186, 198, 220, .5) !important;
  background: #222b3c !important;
  background-image: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,0) 55%) !important;
}
#sisun-side button.sisun-side-btn.primary {
  background: #2563eb !important;
  background-image: linear-gradient(180deg, rgba(255,255,255,.14), rgba(255,255,255,0) 50%) !important;
  color: #ffffff !important;
  border-color: rgba(147, 197, 253, .55) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.2), 0 4px 14px rgba(37,99,235,.4) !important;
}
html.sisun-light #sisun-side button.sisun-side-btn {
  background: #ffffff !important; background-image: none !important;
  color: #0f172a !important; border: 1px solid #cbd5e1 !important;
  box-shadow: 0 1px 2px rgba(15,23,42,.06) !important;
}
html.sisun-light #sisun-side button.sisun-side-btn.primary {
  background: #2563eb !important; color: #ffffff !important;
  border-color: rgba(37,99,235,.55) !important;
}
.sisun-theme {
  display: flex; align-items: center; gap: 8px; cursor: pointer;
  padding: 10px 8px; margin-top: 8px; border-top: 1px solid var(--sisun-line);
  color: var(--sisun-card-fg); font-size: 12px; font-weight: 700; user-select: none;
}
.sisun-theme-ico { width: 18px; text-align: center; font-size: 14px; }
.sisun-theme-label { flex: 1; }
/* 테마 토글 스위치 — 손잡이 좌우 슬라이드 */
.sisun-theme-sw {
  width: 40px; height: 22px; border-radius: 999px; background: #475569 !important;
  border: 1px solid var(--sisun-line) !important; position: relative !important;
  flex: 0 0 40px; box-sizing: border-box !important;
  transition: background .2s ease;
}
.sisun-theme-knob {
  position: absolute !important; top: 2px !important; left: 2px !important;
  width: 16px !important; height: 16px !important; border-radius: 50% !important;
  background: #ffffff !important; box-shadow: 0 1px 2px rgba(0,0,0,.35);
  transform: translateX(0); transition: transform .22s ease;
  pointer-events: none;
}
/* Dark Mode(기본) = 손잡이 오른쪽(ON), Light Mode = 왼쪽 */
.sisun-theme-sw.sisun-sw-on { background: #2563eb !important; }
.sisun-theme-sw.sisun-sw-on .sisun-theme-knob { transform: translateX(18px); }
html.sisun-light .sisun-theme-sw { background: #94a3b8 !important; }
html.sisun-light .sisun-theme-sw.sisun-sw-on { background: #2563eb !important; }
button.sisun-logout-btn,
.sisun-logout-btn button {
  margin-top: 6px !important;
  width: 100% !important; min-height: 40px !important; border-radius: 10px !important;
  background: #151c2a !important; color: #e2e8f0 !important;
  border: 1px solid rgba(186, 198, 220, .22) !important; font-weight: 800 !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.04) !important;
}
html.sisun-light button.sisun-logout-btn,
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
/* Light Mode 글자색 — Gradio Soft 다크 토큰(#e2e8f0)이 남는 문제 보정 */
html.sisun-light,
html.sisun-light body,
html.sisun-light .gradio-container {
  --body-text-color: #0f172a !important;
  --block-label-text-color: #334155 !important;
  --block-title-text-color: #0f172a !important;
  --block-info-text-color: #475569 !important;
  --input-text-color: #0f172a !important;
  color: #0f172a !important;
}
html.sisun-light .sisun-header,
html.sisun-light .sisun-header .prose,
html.sisun-light .sisun-header .html-container {
  color: #0f172a !important;
}
html.sisun-light .sisun-h-title,
html.sisun-light .sisun-brand,
html.sisun-light .sisun-hello,
html.sisun-light .sisun-clock,
html.sisun-light .sisun-weather-place {
  color: #0f172a !important;
}
html.sisun-light .sisun-h-sub,
html.sisun-light .sisun-notice,
html.sisun-light .sisun-weather-data,
html.sisun-light .sisun-weather {
  color: #334155 !important;
}
html.sisun-light .sisun-theme,
html.sisun-light .sisun-theme-label,
html.sisun-light .sisun-theme-ico,
html.sisun-light .sisun-side-brand {
  color: #0f172a !important;
}
html.sisun-light .t2-kpi,
html.sisun-light .t2-card {
  color: #0f172a !important;
}
html.sisun-light .t2-kpi .t2-muted,
html.sisun-light .t2-muted {
  color: #475569 !important;
}
html.sisun-light .t2-kpi-ink {
  color: #0f172a !important;
}
html.sisun-light .t2-kpi-cam {
  color: #0369a1 !important;
}
html.sisun-light .t2-page-title,
html.sisun-light .t2-pick-label,
html.sisun-light .sisun-title,
html.sisun-light .sisun-sub,
html.sisun-light .sisun-meta {
  color: #0f172a !important;
}
.sisun-wall-row,
.sisun-wall-row > .gap {
  display: flex !important; flex-wrap: nowrap !important;
  align-items: stretch !important; min-width: 0 !important;
}
.sisun-cam { min-width: 0 !important; flex: 1 1 0 !important; }
.sisun-wall { position: relative !important; margin-top: 10px; }
.sisun-cam-slot {
  min-width: 0 !important; flex: 1 1 0 !important;
  display: flex !important; flex-direction: column !important; gap: 6px !important;
}
.sisun-cam-cap {
  font-size: 12px; font-weight: 800; letter-spacing: .02em;
  color: var(--sisun-card-fg); line-height: 1.2; padding: 0 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
html.sisun-light .sisun-cam-cap { color: #0f172a !important; }
.sisun-cam {
  position: relative !important; aspect-ratio: 16 / 9;
  min-height: 160px !important;
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
  display: block !important;
}
.sisun-cam .block, .sisun-cam .video-container, .sisun-cam .wrap,
.sisun-cam .container, .sisun-cam .sisun-cam-vid {
  height: 100% !important; min-height: 100% !important;
  border: none !important; background: transparent !important;
}
/* 소제목만 있는 메인 칸도 비디오 박스가 꽉 차게 */
.sisun-cam-slot .sisun-cam > .block:not(:has(.sisun-cam-tag)):not(:has(.sisun-cam-alert-inner)) {
  height: 100% !important; min-height: 100% !important;
  padding: 0 !important; margin: 0 !important;
  border: none !important; background: transparent !important;
}
/* 메인 영상 하단 위험 알림.
   Gradio .block/.html-container 가 height:0 으로 접히면 문구가 카메라 밖으로
   밀려 .sisun-cam{overflow:hidden} 에 잘림 → ON일 때 fit-content 로 위로 확장. */
.sisun-cam > .block:has(.sisun-cam-alert-inner),
.sisun-cam-alert {
  position: absolute !important;
  left: 0 !important; right: 0 !important; bottom: 0 !important;
  top: auto !important;
  width: 100% !important;
  height: fit-content !important;
  z-index: 6 !important;
  padding: 0 !important; margin: 0 !important;
  border: none !important; background: transparent !important;
  box-shadow: none !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  pointer-events: none !important;
}
/* 위험 박스만 클릭 가능 → 해당 구역 탭으로 이동 (영상 클릭 시어터는 유지) */
.sisun-cam > .block:has(.sisun-cam-alert-on),
.sisun-cam-alert:has(.sisun-cam-alert-on) {
  pointer-events: auto !important;
  cursor: pointer !important;
  /* .sisun-cam .block { height:100% } 보다 우선 */
  height: fit-content !important;
  min-height: 64px !important;
  max-height: 46% !important;
  overflow: hidden !important;
}
/* 꺼진 위험 박스는 컨테이너까지 숨겨 옆 목록 영상을 가리지 않음 */
.sisun-cam > .block:has(.sisun-cam-alert-off),
.sisun-cam-alert:has(.sisun-cam-alert-off) {
  display: none !important;
  height: 0 !important; min-height: 0 !important; max-height: 0 !important;
}
.sisun-cam-alert:has(.sisun-cam-alert-on) .html-container,
.sisun-cam-alert:has(.sisun-cam-alert-on) .prose {
  height: fit-content !important;
  min-height: 64px !important;
  max-height: none !important;
  padding: 0 !important; margin: 0 !important;
  background: transparent !important;
  overflow: visible !important;
  display: block !important;
  width: 100% !important;
}
.sisun-cam-alert .prose > :first-child { margin: 0 !important; }
.sisun-cam-alert-inner {
  width: 100% !important;
  max-width: 100% !important;
  height: auto !important;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-end;
  text-align: center;
  gap: 3px;
  box-sizing: border-box;
  padding: 0;
  overflow: visible;
}
.sisun-cam-alert-off { display: none !important; }
.sisun-cam-alert-on {
  background: rgba(185, 28, 28, .86);
  border-top: 2px solid rgba(254, 202, 202, .55);
  color: #fff;
  animation: sisunPulse .9s ease-in-out infinite;
  cursor: pointer !important;
  pointer-events: auto !important;
  box-sizing: border-box;
  padding: 8px 10px 7px;
  min-height: 64px;
  width: 100% !important;
  overflow: visible;
}
.sisun-cam-alert-on:hover {
  background: rgba(185, 28, 28, .94);
}
.sisun-cam-alert-kicker,
.sisun-cam-alert-msg,
.sisun-cam-alert-extra {
  flex: 0 0 auto !important;
  flex-shrink: 0 !important;
  min-height: 1.2em;
  max-width: 100%;
  box-sizing: border-box;
}
.sisun-cam-alert-kicker {
  display: block !important;
  font-size: 13px; font-weight: 900; letter-spacing: .01em;
  line-height: 1.3;
  white-space: normal;
  overflow: visible;
  word-break: keep-all;
  overflow-wrap: anywhere;
}
.sisun-cam-alert-msg {
  display: block !important;
  font-size: 12px; font-weight: 800; opacity: .95;
  letter-spacing: .02em;
  line-height: 1.25;
}
.sisun-cam-alert-extra {
  display: block !important;
  font-size: 11px; font-weight: 700; opacity: .9;
  line-height: 1.2;
}
.sisun-cam-alert-place {
  font-size: 11px; font-weight: 700; opacity: .88;
  margin-top: 2px; max-width: 100%;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sisun-theater-rail-list .sisun-cam-alert-on {
  min-height: 0;
  height: auto;
  padding: 5px 6px 4px;
  overflow: visible;
}
.sisun-theater-rail-list .sisun-cam-alert-kicker { font-size: 10px; line-height: 1.25; }
.sisun-theater-rail-list .sisun-cam-alert-msg { font-size: 9px; line-height: 1.25; }
.sisun-theater-rail-list .sisun-cam-alert-extra { font-size: 8px; line-height: 1.2; }
.sisun-theater-rail-list .sisun-cam-alert-place { font-size: 9px; }

/* 카메라 상세 상단: 위치·이유·근거 요약 */
.sisun-detail-summary {
  border-radius: 10px;
  padding: 14px 16px 12px;
  margin: 0 0 12px;
  color: #fff;
  box-sizing: border-box;
}
.sisun-detail-hot {
  background: linear-gradient(135deg, rgba(185, 28, 28, .92), rgba(127, 29, 29, .88));
  border: 1px solid rgba(254, 202, 202, .35);
}
.sisun-detail-warn {
  background: linear-gradient(135deg, rgba(180, 83, 9, .92), rgba(146, 64, 14, .88));
  border: 1px solid rgba(253, 230, 138, .35);
}
.sisun-detail-headline {
  font-size: 20px; font-weight: 900; letter-spacing: .01em; line-height: 1.3;
}
.sisun-detail-meta {
  margin-top: 6px; font-size: 13px; font-weight: 700; opacity: .92;
}
.sisun-detail-line {
  margin-top: 8px; font-size: 13px; font-weight: 600; line-height: 1.4;
  opacity: .95;
}
.sisun-detail-line span {
  display: inline-block; min-width: 4.5em; font-weight: 800; opacity: .8;
  margin-right: 6px;
}
.sisun-detail-extra {
  margin-top: 8px; font-size: 12px; font-weight: 700; opacity: .85;
}

/* 카메라 상세: 판정 기준·관측 근거 (접힘 Accordion) */
.sisun-judgment-acc {
  margin: 0 0 10px !important;
  border: 1px solid var(--sisun-line) !important;
  border-radius: 10px !important;
  background: rgba(15, 23, 42, .55) !important;
  overflow: visible !important;
  height: auto !important;
  min-height: 0 !important;
}
.sisun-judgment-acc > .label-wrap,
.sisun-judgment-acc .label-wrap {
  padding: 8px 12px !important;
  font-size: 13px !important;
  font-weight: 800 !important;
  color: var(--sisun-title) !important;
}
/* Gradio hide-container 가 펼친 본문 높이를 0으로 접지 않게 */
.sisun-judgment-acc [data-testid="accordion-content"],
.sisun-judgment-acc .label-wrap.open + div,
.sisun-judgment-acc .column,
.sisun-judgment-acc .block,
.sisun-judgment-acc .html-container,
.sisun-judgment-acc .prose {
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  display: block !important;
}
.sisun-judgment-acc .html-container,
.sisun-judgment-acc .prose {
  padding: 0 12px 10px !important;
  margin: 0 !important;
  background: transparent !important;
}
.sisun-judgment {
  font-size: 12.5px; line-height: 1.45;
  color: var(--sisun-card-fg, #e2e8f0);
}
.sisun-judgment-row { margin: 0 0 8px; }
.sisun-judgment-row > span {
  display: block; font-size: 11px; font-weight: 800;
  letter-spacing: .04em; opacity: .72; margin-bottom: 3px;
}
.sisun-judgment-row b { font-weight: 800; }
.sisun-judgment-row ul {
  margin: 0; padding-left: 1.15em;
}
.sisun-judgment-row li { margin: 1px 0; }
.sisun-judgment-row p { margin: 0; }
.sisun-judgment-note {
  font-size: 11px; font-weight: 700; opacity: .75; margin-bottom: 2px;
}
html.sisun-light .sisun-judgment-acc {
  background: #f8fafc !important;
  border-color: #cbd5e1 !important;
}
html.sisun-light .sisun-judgment { color: #0f172a; }
/* #1 메인 시어터: 큰 화면 + 옆 목록 */
.sisun-theater-chrome {
  display: none; width: 100%; min-height: 68vh;
  flex-direction: row; align-items: stretch; gap: 12px;
}
.sisun-wall-main.sisun-theater > .gap { display: none !important; }
.sisun-wall-main.sisun-theater .sisun-theater-chrome {
  display: flex !important;
}
.sisun-theater-stage {
  flex: 1 1 auto; min-width: 0;
  display: flex; flex-direction: column;
}
.sisun-theater-stage .sisun-cam-slot {
  flex: 1 1 auto !important; width: 100% !important;
}
.sisun-theater-stage .sisun-cam {
  width: 100% !important; min-height: 62vh !important;
  aspect-ratio: 16 / 9; cursor: pointer !important;
}
.sisun-theater-rail {
  flex: 0 0 260px; width: 260px; max-width: 30vw;
  background: rgba(2, 6, 23, .72); border: 1px solid var(--sisun-line);
  border-radius: 12px; display: flex; flex-direction: column;
  min-height: 0; max-height: 72vh; overflow: hidden;
}
.sisun-theater-rail-head {
  flex: 0 0 auto; padding: 10px 12px; font-size: 13px; font-weight: 800;
  color: var(--sisun-title); border-bottom: 1px solid var(--sisun-line);
}
.sisun-theater-rail-list {
  flex: 1 1 auto; min-height: 0; overflow-x: hidden; overflow-y: auto;
  padding: 8px; display: flex; flex-direction: column; gap: 10px;
  -webkit-overflow-scrolling: touch;
}
.sisun-theater-rail-list .sisun-cam-slot {
  flex: 0 0 auto !important; width: 100% !important;
  display: flex !important; flex-direction: column !important; gap: 4px !important;
}
.sisun-theater-rail-list .sisun-cam-cap {
  font-size: 11px; font-weight: 800; line-height: 1.2;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
/* 옆 목록: 글 + 작은 영상 썸네일 (위험 박스가 영상을 통째로 덮지 않게) */
.sisun-theater-rail-list .sisun-cam {
  width: 100% !important; min-height: 110px !important; height: auto !important;
  aspect-ratio: 16 / 9 !important;
  cursor: pointer !important;
  border-color: rgba(186, 198, 220, .35) !important;
  pointer-events: auto !important;
  position: relative !important;
  overflow: hidden !important;
}
.sisun-theater-rail-list .sisun-cam:hover {
  border-color: rgba(147, 197, 253, .75) !important;
}
.sisun-theater-rail-list .sisun-cam .block:not(:has(.sisun-cam-alert-inner)),
.sisun-theater-rail-list .sisun-cam .video-container,
.sisun-theater-rail-list .sisun-cam .wrap,
.sisun-theater-rail-list .sisun-cam .container,
.sisun-theater-rail-list .sisun-cam .sisun-cam-vid {
  height: 100% !important; min-height: 110px !important;
  width: 100% !important; display: block !important;
  padding: 0 !important; margin: 0 !important;
  border: none !important; background: #000 !important;
}
.sisun-theater-rail-list .sisun-cam > .block:has(.sisun-cam-alert-inner),
.sisun-theater-rail-list .sisun-cam-alert {
  position: absolute !important;
  left: 0 !important; right: 0 !important; bottom: 0 !important;
  top: auto !important;
  width: 100% !important;
  height: fit-content !important;
  min-height: 0 !important;
  max-height: none !important;
  z-index: 6 !important;
  background: transparent !important;
  overflow: visible !important;
  pointer-events: none !important;
}
/* Gradio가 .prose에도 sisun-cam-alert 를 붙여 absolute+bottom:0 으로 씀.
   예전 min-height:48px + overflow:hidden 이 3줄(~52px)을 잘랐음 → 내용만큼 확장 */
.sisun-theater-rail-list .sisun-cam > .block:has(.sisun-cam-alert-on),
.sisun-theater-rail-list .sisun-cam-alert:has(.sisun-cam-alert-on),
.sisun-theater-rail-list .prose.sisun-cam-alert:has(.sisun-cam-alert-on) {
  height: fit-content !important;
  min-height: 0 !important;
  max-height: 70% !important;
  overflow: visible !important;
  bottom: 0 !important;
  top: auto !important;
}
.sisun-theater-rail-list .sisun-cam-alert:has(.sisun-cam-alert-on) .html-container,
.sisun-theater-rail-list .block.sisun-cam-alert:has(.sisun-cam-alert-on) .html-container,
.sisun-theater-rail-list .sisun-cam-alert:has(.sisun-cam-alert-on) .prose {
  height: fit-content !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
  width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  display: block !important;
  background: transparent !important;
}
.sisun-theater-rail-list .sisun-cam > .block:has(.sisun-cam-alert-off),
.sisun-theater-rail-list .sisun-cam-alert:has(.sisun-cam-alert-off) {
  display: none !important;
}
.sisun-theater-rail-list .sisun-cam video {
  width: 100% !important; height: 100% !important; min-height: 110px !important;
  object-fit: cover !important; display: block !important;
  opacity: 1 !important; visibility: visible !important;
  position: relative !important; z-index: 1 !important;
}
html.sisun-light .sisun-theater-rail {
  background: rgba(255,255,255,.92); border-color: #cbd5e1;
}
/* #2~#7 단일 카메라: 클릭 확대 없이 처음부터 크게 */
.sisun-wall-solo .sisun-cam {
  width: 100% !important; max-width: 100% !important;
  aspect-ratio: 16 / 9; min-height: 62vh !important;
  cursor: default !important;
}
.sisun-wall-solo .sisun-cam-slot { flex: 1 1 100% !important; width: 100% !important; }
.sisun-wall-solo .sisun-wall-row { width: 100% !important; }

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
  if (typeof window.__sisunSound !== "boolean") window.__sisunSound = true;
  var seenOn = new WeakMap();
  var soundOff = function() {
    return !!window.__sisunBellMuted || window.__sisunSound === false;
  };
  var killBeepEl = function(a) {
    if (!a) return;
    try {
      a.autoplay = false;
      a.removeAttribute("autoplay");
      a.muted = true;
      a.defaultMuted = true;
      a.volume = 0;
      try { a.pause(); } catch (e1) {}
      try { a.removeAttribute("src"); a.src = ""; a.load(); } catch (e2) {}
      try { a.remove(); } catch (e3) {}
    } catch (e0) {}
  };
  var silenceBeeps = function() {
    // Gradio Soft 섀도우 DOM 안 audio까지 포함
    allOf("audio.sisun-beep").forEach(killBeepEl);
    allOf(".sisun-alert-bundle audio").forEach(killBeepEl);
  };
  // autoplay/play()가 폴링보다 먼저 울리는 경우 차단
  if (!window.__sisunBeepPlayPatch) {
    window.__sisunBeepPlayPatch = true;
    var _origPlay = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function() {
      try {
        if (this && this.classList && this.classList.contains("sisun-beep") && soundOff()) {
          killBeepEl(this);
          return Promise.resolve();
        }
      } catch (ePlay) {}
      return _origPlay.apply(this, arguments);
    };
  }
  if (!window.__sisunBeepObs) {
    window.__sisunBeepObs = true;
    var watchBeepNode = function(node) {
      if (!soundOff() || !node || node.nodeType !== 1) return;
      if (node.matches && (node.matches("audio.sisun-beep") || node.matches(".sisun-alert-bundle audio"))) {
        killBeepEl(node);
      }
      if (node.querySelectorAll) {
        node.querySelectorAll("audio.sisun-beep, .sisun-alert-bundle audio").forEach(killBeepEl);
      }
      if (node.shadowRoot) watchBeepNode(node.shadowRoot);
    };
    new MutationObserver(function(muts) {
      if (!soundOff()) return;
      muts.forEach(function(m) {
        m.addedNodes.forEach(watchBeepNode);
      });
      silenceBeeps();
    }).observe(document.documentElement, { childList: true, subtree: true });
  }
  var gateOn = function() {
    var g = document.getElementById("sisun-gate");
    if (!g) return false;
    if (g.classList.contains("sisun-login-off") || g.classList.contains("hide")) return false;
    if (g.classList.contains("sisun-login-on")) return true;
    var st = window.getComputedStyle(g);
    return st.display !== "none" && st.visibility !== "hidden";
  };
  var syncCctv = function() {
    // 로그인 화면에서는 video load/play 금지 — 메인 스레드 정지 방지
    if (gateOn()) return;
    allOf("video").forEach(function(v) {
      v.muted = true;
      v.defaultMuted = true;
      v.volume = 0;
      v.preload = "auto";
      v.setAttribute("playsinline", "true");
      if (v.closest(".sisun-preload")) {
        v.pause();
        return;
      }
      var box = v.getBoundingClientRect();
      var on = box.width > 8 && box.height > 8;
      var was = seenOn.get(v) === true;
      if (on && !was) {
        try { v.currentTime = 0; } catch (e) {}
        v.play().catch(function(){});
      } else if (!on && was) {
        v.pause();
      }
      seenOn.set(v, on);
    });
  };
  var tick = function() {
    var el = document.getElementById("sisun-clock");
    if (!el) return;
    var d = new Date();
    var pad = function(n) { return String(n).padStart(2, "0"); };
    // 년. 월. 일. HH:MM (24시간)
    el.textContent =
      d.getFullYear() + ". " +
      pad(d.getMonth() + 1) + ". " +
      pad(d.getDate()) + ". " +
      pad(d.getHours()) + ":" +
      pad(d.getMinutes());
  };
  tick();
  setInterval(tick, 1000);
  var lastWx = "--";
  var wxKo = {0:"맑음",1:"맑음",2:"구름조금",3:"흐림",45:"안개",48:"안개",51:"이슬비",53:"이슬비",55:"이슬비",61:"비",63:"비",65:"비",71:"눈",73:"눈",75:"눈",80:"소나기",81:"소나기",95:"뇌우",96:"뇌우"};
  var wxIco = {0:"☀",1:"☀",2:"⛅",3:"☁",45:"🌫",48:"🌫",51:"🌦",53:"🌦",61:"🌧",63:"🌧",65:"🌧",71:"❄",73:"❄",80:"🌦",95:"⛈"};
  var paintWx = function() {
    var el = document.getElementById("sisun-weather-data");
    if (el) el.textContent = lastWx;
  };
  // 포항시 남구 고정. 위치 탐색·좌표 표시 없음. 실패 시 lastWx 유지.
  var loadWx = function() {
    fetch("https://api.open-meteo.com/v1/forecast?latitude=36.0190&longitude=129.3435&current=temperature_2m,weather_code&timezone=Asia/Seoul")
      .then(function(r) {
        if (!r.ok) return null;
        return r.json();
      })
      .then(function(d) {
        if (!d) return;
        var cur = d.current;
        if (!cur || cur.temperature_2m == null) return;
        var code = String(cur.weather_code);
        var ico = wxIco[code] || "·";
        var name = wxKo[code] || "날씨";
        lastWx = ico + " " + Number(cur.temperature_2m).toFixed(1) + "° " + name;
        paintWx();
      })
      .catch(function() {});
  };
  paintWx();
  loadWx();
  setInterval(loadWx, 10 * 60 * 1000);
  var themeVars = {
    dark: {
      "--sisun-page": "#0f172a", "--sisun-header-bg": "#020617", "--sisun-side-bg": "#0b1220",
      "--sisun-title": "#f8fafc", "--sisun-card-bg": "#1e293b", "--sisun-card-fg": "#f8fafc",
      "--sisun-table-fg": "#f8fafc", "--sisun-table-bg": "#1e293b", "--sisun-th-bg": "#334155",
      "--sisun-muted": "#cbd5e1", "--sisun-line": "#334155", "--sisun-accent": "#2563eb",
      "--body-text-color": "#e2e8f0", "--block-label-text-color": "#cbd5e1",
      "--block-title-text-color": "#e2e8f0", "--block-info-text-color": "#94a3b8",
      "--input-text-color": "#f8fafc"
    },
    light: {
      "--sisun-page": "#f1f5f9", "--sisun-header-bg": "#ffffff", "--sisun-side-bg": "#e8eef6",
      "--sisun-title": "#0f172a", "--sisun-card-bg": "#ffffff", "--sisun-card-fg": "#0f172a",
      "--sisun-table-fg": "#0f172a", "--sisun-table-bg": "#ffffff", "--sisun-th-bg": "#e2e8f0",
      "--sisun-muted": "#475569", "--sisun-line": "#cbd5e1", "--sisun-accent": "#2563eb",
      "--body-text-color": "#0f172a", "--block-label-text-color": "#334155",
      "--block-title-text-color": "#0f172a", "--block-info-text-color": "#475569",
      "--input-text-color": "#0f172a"
    }
  };
  var paintThemeVars = function(light) {
    var vars = light ? themeVars.light : themeVars.dark;
    var root = document.documentElement;
    Object.keys(vars).forEach(function(k) { root.style.setProperty(k, vars[k]); });
    // Gradio CSS 스코프에 안 잡히도록 head 에 보강 스타일
    var tag = document.getElementById("sisun-theme-force");
    if (!tag) {
      tag = document.createElement("style");
      tag.id = "sisun-theme-force";
      document.head.appendChild(tag);
    }
    if (light) {
      tag.textContent = [
        "html.sisun-light,.gradio-container{color:#0f172a!important}",
        "html.sisun-light .sisun-header,html.sisun-light .sisun-header *{color:#0f172a!important}",
        "html.sisun-light .sisun-h-sub,html.sisun-light .sisun-notice,html.sisun-light .sisun-weather-data{color:#334155!important}",
        "html.sisun-light .sisun-theme,html.sisun-light .sisun-theme-label,html.sisun-light .sisun-theme-ico,html.sisun-light .sisun-side-brand{color:#0f172a!important}",
        "html.sisun-light .t2-kpi,html.sisun-light .t2-card,html.sisun-light .t2-page-title{color:#0f172a!important}",
        "html.sisun-light .t2-muted,html.sisun-light .t2-kpi .t2-muted{color:#475569!important}",
        "html.sisun-light .t2-kpi-ink{color:#0f172a!important}",
        "html.sisun-light .t2-kpi-cam{color:#0369a1!important}",
        "html.sisun-light #sisun-side button.sisun-side-btn{background:#ffffff!important;background-image:none!important;color:#0f172a!important;border:1px solid #cbd5e1!important;box-shadow:0 1px 2px rgba(15,23,42,.06)!important}",
        "html.sisun-light #sisun-side button.sisun-side-btn.primary{background:#2563eb!important;color:#ffffff!important;border-color:rgba(37,99,235,.55)!important}",
        "html.sisun-light button.sisun-logout-btn{background:#ffffff!important;color:#0f172a!important;border:1px solid #cbd5e1!important}",
        "html.sisun-light .sisun-cam-cap{color:#0f172a!important}"
      ].join("");
    } else {
      tag.textContent = "";
    }
  };
  var applyTheme = function(mode) {
    var light = mode === "light";
    document.documentElement.classList.toggle("sisun-light", light);
    paintThemeVars(light);
    try { sessionStorage.setItem("sisun-theme", light ? "light" : "dark"); } catch (e) {}
    var row = document.getElementById("sisun-theme-row");
    if (row) {
      var lab = row.querySelector(".sisun-theme-label");
      var ico = row.querySelector(".sisun-theme-ico");
      var sw = row.querySelector(".sisun-theme-sw");
      if (lab) lab.textContent = light ? "Light Mode" : "Dark Mode";
      if (ico) ico.textContent = light ? "☀" : "☽";
      // Dark = ON(오른쪽), Light = OFF(왼쪽) — 손잡이 슬라이드
      if (sw) sw.classList.toggle("sisun-sw-on", !light);
    }
  };
  try { applyTheme(sessionStorage.getItem("sisun-theme") || "dark"); } catch (e) { applyTheme("dark"); }
  var bindTheme = function() {
    var row = document.getElementById("sisun-theme-row");
    if (!row || row.__sisunBound) return;
    row.__sisunBound = true;
    row.addEventListener("click", function(e) {
      e.preventDefault();
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
  // #1 메인: 유튜브형 시어터 (큰 화면 + 옆 목록, 순서 1~6 유지)
  var theaterParents = new WeakMap();
  var indexSlots = function(wall) {
    var slots = Array.prototype.slice.call(wall.querySelectorAll(".sisun-cam-slot"));
    slots.forEach(function(s, i) {
      if (s.dataset.camIdx === undefined) s.dataset.camIdx = String(i);
    });
    return slots.sort(function(a, b) {
      return Number(a.dataset.camIdx) - Number(b.dataset.camIdx);
    });
  };
  var ensureTheaterChrome = function(wall) {
    var chrome = wall.querySelector(".sisun-theater-chrome");
    if (chrome) return chrome;
    chrome = document.createElement("div");
    chrome.className = "sisun-theater-chrome";
    chrome.innerHTML =
      '<div class="sisun-theater-stage"></div>' +
      '<div class="sisun-theater-rail">' +
      '<div class="sisun-theater-rail-head">카메라 목록</div>' +
      '<div class="sisun-theater-rail-list"></div></div>';
    wall.appendChild(chrome);
    return chrome;
  };
  var wakeTheaterVideos = function(root) {
    if (!root) return;
    root.querySelectorAll("video").forEach(function(v) {
      try {
        v.style.setProperty("display", "block", "important");
        v.style.setProperty("visibility", "visible", "important");
        v.muted = true;
        v.playsInline = true;
        if (v.readyState < 2) v.load();
        var p = v.play();
        if (p && p.catch) p.catch(function() {});
      } catch (err) {}
    });
  };
  var placeTheaterSlots = function(wall, activeSlot) {
    var chrome = ensureTheaterChrome(wall);
    var stage = chrome.querySelector(".sisun-theater-stage");
    var list = chrome.querySelector(".sisun-theater-rail-list");
    indexSlots(wall);
    // chrome 안·밖 어디 있든 전부 모아 정렬
    var all = Array.prototype.slice.call(wall.querySelectorAll(".sisun-cam-slot"));
    all.sort(function(a, b) {
      return Number(a.dataset.camIdx) - Number(b.dataset.camIdx);
    });
    all.forEach(function(slot) {
      if (!theaterParents.has(slot)) {
        theaterParents.set(slot, { parent: slot.parentNode, next: slot.nextSibling });
      }
      if (slot === activeSlot) stage.appendChild(slot);
      else list.appendChild(slot);
    });
    // 옆 목록·큰 화면 영상 다시 보이게
    setTimeout(function() {
      wakeTheaterVideos(chrome);
      syncCctv();
    }, 50);
  };
  var exitTheater = function(wall) {
    if (!wall || !wall.classList.contains("sisun-theater")) return;
    wall.classList.remove("sisun-theater");
    wall.querySelectorAll(".sisun-cam-on").forEach(function(el) {
      el.classList.remove("sisun-cam-on");
    });
    var slots = Array.prototype.slice.call(wall.querySelectorAll(".sisun-cam-slot"));
    slots.sort(function(a, b) {
      return Number(a.dataset.camIdx || 0) - Number(b.dataset.camIdx || 0);
    });
    slots.forEach(function(slot) {
      var info = theaterParents.get(slot);
      if (!info || !info.parent) return;
      if (info.next && info.next.parentNode === info.parent) {
        info.parent.insertBefore(slot, info.next);
      } else {
        info.parent.appendChild(slot);
      }
    });
    var chrome = wall.querySelector(".sisun-theater-chrome");
    if (chrome) chrome.remove();
    syncCctv();
  };
  var enterTheater = function(wall, hitCam) {
    var activeSlot = hitCam.closest(".sisun-cam-slot");
    if (!activeSlot) return;
    indexSlots(wall);
    wall.classList.add("sisun-theater");
    wall.querySelectorAll(".sisun-cam-on").forEach(function(el) {
      el.classList.remove("sisun-cam-on");
    });
    hitCam.classList.add("sisun-cam-on");
    placeTheaterSlots(wall, activeSlot);
    syncCctv();
  };
  var switchTheater = function(wall, hitCam) {
    var activeSlot = hitCam.closest(".sisun-cam-slot");
    if (!activeSlot) return;
    wall.querySelectorAll(".sisun-cam-on").forEach(function(el) {
      el.classList.remove("sisun-cam-on");
    });
    hitCam.classList.add("sisun-cam-on");
    placeTheaterSlots(wall, activeSlot);
    syncCctv();
  };
  var camIdFromAlert = function(node) {
    var on = node && node.closest ? node.closest(".sisun-cam-alert-on") : null;
    if (!on) return "";
    var id = on.getAttribute("data-cam-id") || "";
    if (id) return id;
    var slot = on.closest(".sisun-cam-slot");
    var host = slot && slot.querySelector("[id^='sisun-video-sisun-wall-']");
    if (host && host.id) {
      var m = host.id.match(/^sisun-video-sisun-wall-(.+)$/);
      if (m) return m[1];
    }
    return "";
  };
  var goCameraTab = function(camId) {
    if (!camId) return false;
    var btn = document.getElementById("sisun-side-" + camId);
    if (!btn) {
      // Gradio가 id를 감싸는 경우
      btn = document.querySelector("#sisun-side-" + camId + " button, button#sisun-side-" + camId);
    }
    if (!btn) return false;
    try { btn.click(); } catch (err) { return false; }
    return true;
  };
  // 사이드바 확인 필요(N): 위험 나면 표시. 사이드바로 그 구역을 보기 전에는 절대 안 지움.
  // 확인 후에야 사라지고, 이후 새 위험/새로고침이면 다시 뜸.
  var __sisunSideNeed = window.__sisunSideNeed || (window.__sisunSideNeed = {});
  var sideBtnForCam = function(camId) {
    if (!camId || camId === "main" || camId === "alerts" || camId === "history" || camId === "data") {
      return null;
    }
    var btn = document.querySelector("button#sisun-side-" + camId);
    if (btn) return btn;
    var host = document.getElementById("sisun-side-" + camId);
    return host ? (host.querySelector("button") || host) : null;
  };
  var ensureSideNeedBadge = function(btn) {
    if (!btn || !btn.querySelector) return null;
    var mark = btn.querySelector(".sisun-side-need");
    if (!mark) {
      mark = document.createElement("span");
      mark.className = "sisun-side-need";
      mark.textContent = "N";
      mark.title = "사이드 미방문(위험) · 운영자 확인함과 별개";
      mark.setAttribute("aria-label", "사이드 미방문");
      btn.appendChild(mark);
    }
    return mark;
  };
  var paintSideNeed = function(camId) {
    var btn = sideBtnForCam(camId);
    if (!btn) return;
    var mark = ensureSideNeedBadge(btn);
    if (!mark) return;
    mark.classList.toggle("is-on", !!__sisunSideNeed[camId]);
  };
  var markSideNeed = function(camId) {
    if (!camId) return;
    if (!sideBtnForCam(camId)) return;
    __sisunSideNeed[camId] = true;
    paintSideNeed(camId);
  };
  var clearSideNeed = function(camId) {
    if (!camId) return;
    __sisunSideNeed[camId] = false;
    paintSideNeed(camId);
  };
  var resetSideNeeds = function() {
    Object.keys(__sisunSideNeed).forEach(function(k) { delete __sisunSideNeed[k]; });
    document.querySelectorAll(".sisun-side-need").forEach(function(el) {
      el.classList.remove("is-on");
    });
  };
  var syncSideNeedsFromOverlays = function() {
    // 켜질 때만 표시. 오버레이가 꺼져도 N은 유지(사이드바 확인 전).
    document.querySelectorAll(".sisun-wall-main .sisun-cam-alert-on[data-cam-id]").forEach(function(el) {
      var id = el.getAttribute("data-cam-id") || "";
      if (id) markSideNeed(id);
    });
  };
  if (!window.__sisunSideNeedBound) {
    window.__sisunSideNeedBound = true;
    document.addEventListener("click", function(ev) {
      var t = ev.target && ev.target.closest
        ? ev.target.closest("#sisun-side button.sisun-side-btn, #sisun-side .sisun-side-btn button")
        : null;
      if (!t) return;
      var id = (t.id || "").replace(/^sisun-side-/, "");
      if (!id && t.closest) {
        var host = t.closest("[id^='sisun-side-']");
        if (host && host.id) id = host.id.replace(/^sisun-side-/, "");
      }
      // 해당 구역 사이드바를 눌렀을 때만 해제
      if (id) clearSideNeed(id);
    }, true);
  }
  var wallClick = function(e) {
    // 위험 알림 박스 클릭 → #2~ 해당 구역 탭 (시어터 동작과 분리)
    var alertOn = e.target && e.target.closest
      ? e.target.closest(".sisun-cam-alert-on")
      : null;
    if (alertOn) {
      var mainWall = alertOn.closest(".sisun-wall-main");
      if (mainWall) {
        var camId = camIdFromAlert(alertOn);
        if (camId) {
          e.preventDefault();
          e.stopPropagation();
          if (mainWall.classList.contains("sisun-theater")) {
            try { exitTheater(mainWall); } catch (e0) {}
          }
          clearSideNeed(camId);
          goCameraTab(camId);
          return;
        }
      }
    }
    var path = e.composedPath ? e.composedPath() : [];
    var hitCam = null, wall = null;
    path.forEach(function(n) {
      if (!n || !n.classList) return;
      if (n.classList.contains("sisun-cam")) hitCam = n;
      if (n.classList.contains("sisun-wall")) wall = n;
    });
    if (!wall && e.target && e.target.closest) {
      hitCam = e.target.closest(".sisun-cam");
      wall = e.target.closest(".sisun-wall");
    }
    if (!wall || !hitCam) return;
    // #2~#7 단독 벽은 클릭 확대 없음
    if (wall.classList.contains("sisun-wall-solo")) return;
    // #1 메인 시어터 (영상 영역 클릭 — 기존 동작 유지)
    if (wall.classList.contains("sisun-wall-main")) {
      e.preventDefault();
      e.stopPropagation();
      if (!wall.classList.contains("sisun-theater")) {
        enterTheater(wall, hitCam);
        return;
      }
      // 큰 화면 클릭 → 6칸 복귀
      if (hitCam.classList.contains("sisun-cam-on") && hitCam.closest(".sisun-theater-stage")) {
        exitTheater(wall);
        return;
      }
      // 옆 목록 클릭 → 큰 화면과 교체
      if (hitCam.closest(".sisun-theater-rail-list")) {
        switchTheater(wall, hitCam);
      }
      return;
    }
  };
  document.addEventListener("click", wallClick, true);
  syncSide();
  var hideGate = function() {
    var g = document.getElementById("sisun-gate");
    if (!g) return;
    var off = g.classList.contains("hide") || g.classList.contains("sisun-login-off");
    if (!off) return;
    if (g.classList.contains("sisun-login-on")) g.classList.remove("sisun-login-on");
    g.style.setProperty("display", "none", "important");
    g.style.setProperty("visibility", "hidden", "important");
    g.style.setProperty("pointer-events", "none", "important");
    g.style.setProperty("z-index", "-1", "important");
    g.style.setProperty("opacity", "0", "important");
  };
  hideGate();
  bindTheme();
  paintWx();
  // 사이드바 열기/닫기 — 마우스 클릭만
  // Gradio 가 flex/min-width 인라인을 다시 써서, 접을 때는 display:none 이 확실함
  var applySideLayout = function() {
    var side = document.getElementById("sisun-side");
    if (!side) return;
    var closed = document.documentElement.classList.contains("sisun-side-closed");
    if (closed) {
      side.style.setProperty("display", "none", "important");
      side.style.setProperty("flex", "0 0 0", "important");
      side.style.setProperty("width", "0", "important");
      side.style.setProperty("min-width", "0", "important");
      side.style.setProperty("max-width", "0", "important");
      side.style.setProperty("margin", "0", "important");
      side.style.setProperty("padding", "0", "important");
    } else {
      side.style.removeProperty("display");
      side.style.setProperty("display", "flex", "important");
      side.style.setProperty("position", "fixed", "important");
      side.style.setProperty("z-index", "40", "important");
      // flex 흐름에서는 자리 안 차지하고, 보이는 폭만 200
      side.style.setProperty("flex", "0 0 0", "important");
      side.style.setProperty("width", "200px", "important");
      side.style.setProperty("min-width", "0", "important");
      side.style.setProperty("max-width", "none", "important");
      side.style.setProperty("margin", "0", "important");
      side.style.setProperty("overflow", "hidden", "important");
      // 헤더 아래·컨테이너 왼쪽 패딩에 맞춤
      var head = document.querySelector(".sisun-header");
      var box = document.querySelector(".gradio-container");
      var top = 72;
      if (head) {
        var hr = head.getBoundingClientRect();
        top = Math.max(12, Math.round(hr.bottom + 8));
      }
      var left = 12;
      if (box) left = Math.max(8, Math.round(box.getBoundingClientRect().left));
      side.style.setProperty("top", top + "px", "important");
      side.style.setProperty("left", left + "px", "important");
      side.style.setProperty("height", "calc(100vh - " + top + "px - 12px)", "important");
      side.style.setProperty("max-height", "calc(100vh - " + top + "px - 12px)", "important");
    }
  };
  if (!window.__sisunSideResizeBound) {
    window.__sisunSideResizeBound = true;
    window.addEventListener("resize", function() { applySideLayout(); });
  }
  var syncSideToggle = function() {
    var btn = document.getElementById("sisun-side-toggle");
    if (!btn) return;
    var closed = document.documentElement.classList.contains("sisun-side-closed");
    var label = closed ? "사이드바 열기" : "사이드바 닫기";
    btn.setAttribute("aria-label", label);
    btn.setAttribute("title", label);
    if (!btn.__sisunSideBound) {
      btn.__sisunSideBound = true;
      btn.addEventListener("click", function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        window.__sisunToggleSide();
      });
    }
    applySideLayout();
  };
  window.__sisunToggleSide = function() {
    var closed = document.documentElement.classList.contains("sisun-side-closed");
    document.documentElement.classList.toggle("sisun-side-closed", !closed);
    try { sessionStorage.setItem("sisun-side", closed ? "1" : "0"); } catch (e) {}
    syncSideToggle();
  };
  try {
    var wantOpen = sessionStorage.getItem("sisun-side") !== "0";
    document.documentElement.classList.toggle("sisun-side-closed", !wantOpen);
  } catch (e) {
    document.documentElement.classList.remove("sisun-side-closed");
  }
  syncSideToggle();
  var __sisunNotices = window.__sisunNotices || (window.__sisunNotices = []);
  var __sisunToastSeen = window.__sisunToastSeen || (window.__sisunToastSeen = {});
  var BELL_SVG_ON =
    '<svg class="sisun-bell-on" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>' +
    '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>';
  var BELL_SVG_OFF =
    '<svg class="sisun-bell-slash" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M8.7 3.7A6 6 0 0 1 18 8c0 2.2.4 4.1 1.1 5.6"/>' +
    '<path d="M17 17H3s3-2 3-9a4.7 4.7 0 0 1 .4-1.9"/>' +
    '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>' +
    '<path d="M2 2l20 20"/></svg>';
  // 기본은 알림·소리 켜짐. 음소거는 현재 페이지에서만 유지, 로그인/새로고침 시 다시 켜짐.
  if (!window.__sisunBellMuteInit) {
    window.__sisunBellMuteInit = true;
    window.__sisunBellMuted = false;
    window.__sisunSound = true;
    try { sessionStorage.removeItem("sisun-bell-muted"); } catch (eMute) {}
  }
  var isBellMuted = function() {
    return !!window.__sisunBellMuted;
  };
  var isRailOpen = function() {
    return !!window.__sisunRailOpen;
  };
  var syncMuteButton = function() {
    var rail = document.getElementById("sisun-alert-rail");
    var muteBtn = rail && rail.querySelector(".sisun-rail-mute-btn");
    if (!muteBtn) return;
    var muted = isBellMuted();
    muteBtn.textContent = muted ? "알림 켜기" : "알림 끄기";
    muteBtn.classList.toggle("is-muted", muted);
    muteBtn.setAttribute("aria-pressed", muted ? "true" : "false");
  };
  var setBellMuted = function(on) {
    window.__sisunBellMuted = !!on;
    // 알림 끄기 = 소리 끔, 알림 켜기 = 소리 다시 켬
    window.__sisunSound = !on;
    try { sessionStorage.removeItem("sisun-bell-muted"); } catch (e) {}
    var wrap = document.getElementById("sisun-bell-wrap");
    var btn = wrap && wrap.querySelector(".sisun-bell-btn");
    if (btn) {
      btn.classList.toggle("is-muted", !!on);
      btn.title = on ? "알림 목록 (꺼짐)" : "알림 목록";
      btn.setAttribute("aria-label", on ? "알림 목록 (꺼짐)" : "알림 목록");
    }
    syncMuteButton();
    if (on) {
      // 이미 재생 중·직후 주입되는 autoplay까지 연속 차단
      silenceBeeps();
      try { requestAnimationFrame(silenceBeeps); } catch (eRaf) {}
      setTimeout(silenceBeeps, 0);
      setTimeout(silenceBeeps, 40);
      setTimeout(silenceBeeps, 120);
    }
  };
  var setRailOpen = function(open) {
    window.__sisunRailOpen = !!open;
    var rail = document.getElementById("sisun-alert-rail");
    if (rail) rail.classList.toggle("is-open", !!open);
    var wrap = document.getElementById("sisun-bell-wrap");
    var btn = wrap && wrap.querySelector(".sisun-bell-btn");
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) placeAlertRail();
  };
  var escText = function(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  };
  var noticeSortKey = function(item) {
    // 확인 전 위험 > 확인 전 주의 > 확인함, 최근 갱신 우선
    var pending = item.ack === "done" ? 0 : 1;
    var hot = item.level === "hot" ? 1 : 0;
    var t = item._seq || 0;
    return pending * 1e9 + hot * 1e6 + t;
  };
  var noticeItemHtml = function(item) {
    var level = item.level === "hot" ? "hot" : "warn";
    var sev = escText(item.severity_label || (level === "hot" ? "위험" : "주의"));
    var title = escText(item.title || sev);
    var text = escText(item.text || "");
    var action = escText(item.action || "");
    var ackPending = item.ack !== "done";
    var ackLabel = ackPending ? "확인 전" : "확인함";
    var ackCls = ackPending ? "is-pending" : "is-done";
    var ep = escText(item.episode_id || "");
    var cam = escText(item.cam_id || "");
    var ackedCls = ackPending ? "" : " is-acked";
    var actions = "<div class='sisun-toast-actions'>";
    if (cam) {
      actions += "<button type='button' class='sisun-toast-goto' data-cam='" + cam + "'>해당 카메라 상세</button>";
    }
    if (ackPending && ep) {
      actions += "<button type='button' class='sisun-toast-ack-btn' data-episode='" + ep + "'>확인함</button>";
    }
    actions += "</div>";
    return "<div class='sisun-toast sisun-toast-" + level + ackedCls + "' data-episode='" + ep + "'>" +
      "<div class='sisun-toast-head'><span class='sisun-toast-ico'>!</span><span>" + title + "</span></div>" +
      "<div class='sisun-toast-text'>" + text + "</div>" +
      (action ? "<div class='sisun-toast-meta'>" + action + "</div>" : "") +
      "<span class='sisun-toast-ack " + ackCls + "'>" + ackLabel + "</span>" +
      actions +
      "</div>";
  };
  var renderBellList = function() {
    var wrap = document.getElementById("sisun-bell-wrap");
    var rail = document.getElementById("sisun-alert-rail");
    var badge = wrap && wrap.querySelector(".sisun-bell-badge");
    var list = rail && rail.querySelector(".sisun-rail-list");
    var html;
    if (!__sisunNotices.length) {
      html = "<div class='sisun-rail-empty'>확인 전 경보가 없습니다</div>";
    } else {
      html = __sisunNotices.slice().sort(function(a, b) {
        return noticeSortKey(b) - noticeSortKey(a);
      }).map(noticeItemHtml).join("");
    }
    if (list) {
      list.innerHTML = html;
    }
    if (badge) {
      var pending = __sisunNotices.filter(function(x) { return x.ack !== "done"; });
      var n = pending.length;
      badge.textContent = n >= 40 ? "40+" : String(n);
      badge.classList.toggle("has-items", n > 0);
      badge.classList.toggle("is-warn", n > 0 && !pending.some(function(x){ return x.level === "hot"; }));
    }
  };
  var placeAlertRail = function() {
    var rail = document.getElementById("sisun-alert-rail");
    if (!rail) return;
    var head = document.querySelector(".sisun-header");
    var top = 64;
    if (head) {
      var hr = head.getBoundingClientRect();
      top = Math.max(56, Math.round(hr.bottom + 8));
    }
    rail.style.top = top + "px";
    rail.classList.toggle("is-open", isRailOpen());
  };
  var ensureBell = function() {
    var wrap = document.getElementById("sisun-bell-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = "sisun-bell-wrap";
      wrap.innerHTML =
        "<button type='button' class='sisun-bell-btn' aria-label='알림 목록' title='알림 목록' aria-expanded='false'>" +
        BELL_SVG_ON + BELL_SVG_OFF +
        "<span class='sisun-bell-badge'>0</span></button>";
      document.body.appendChild(wrap);
    }
    var rail = document.getElementById("sisun-alert-rail");
    if (!rail) {
      rail = document.createElement("div");
      rail.id = "sisun-alert-rail";
      rail.innerHTML =
        "<div class='sisun-rail-head'><span>운영 경보</span>" +
        "<div class='sisun-rail-actions'>" +
        "<button type='button' class='sisun-rail-mute-btn'>알림 끄기</button>" +
        "<button type='button' class='sisun-rail-read-btn' title='운영자 확인 상태만 변경 · 위험 종료 아님'>모두 확인함</button>" +
        "</div></div>" +
        "<div class='sisun-rail-note'>확인함 ≠ 안전·종료 · 브라우저 세션 기준 · 관련 기록은 같은 경보 갱신</div>" +
        "<div class='sisun-rail-list'></div>";
      document.body.appendChild(rail);
    } else if (!rail.querySelector(".sisun-rail-actions")) {
      var head = rail.querySelector(".sisun-rail-head");
      if (head) {
        var actions = document.createElement("div");
        actions.className = "sisun-rail-actions";
        actions.innerHTML =
          "<button type='button' class='sisun-rail-mute-btn'>알림 끄기</button>" +
          "<button type='button' class='sisun-rail-read-btn'>모두 읽음</button>";
        head.appendChild(actions);
      }
    }
    var btn = wrap.querySelector(".sisun-bell-btn");
    if (btn && !btn.__sisunBound) {
      btn.__sisunBound = true;
      btn.addEventListener("click", function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        setRailOpen(!isRailOpen());
      });
    }
    // 버튼 위임: 탭 전환·DOM 갱신 후에도 끄기/켜기·모두 읽음이 죽지 않게
    if (!rail.__sisunDelegated) {
      rail.__sisunDelegated = true;
      rail.addEventListener("click", function(ev) {
        var t = ev.target && ev.target.closest
          ? ev.target.closest(
              ".sisun-rail-mute-btn, .sisun-rail-read-btn, .sisun-toast-ack-btn, .sisun-toast-goto"
            )
          : null;
        if (!t || !rail.contains(t)) return;
        ev.preventDefault();
        ev.stopPropagation();
        if (t.classList.contains("sisun-rail-mute-btn")) {
          if (window.__sisunMuteLock) return;
          window.__sisunMuteLock = true;
          setBellMuted(!isBellMuted());
          setTimeout(function() { window.__sisunMuteLock = false; }, 120);
          return;
        }
        if (t.classList.contains("sisun-rail-read-btn")) {
          // 운영자 확인함만 변경. 목록·원본·위험 판정은 유지.
          window.sisunAckAllNotices && window.sisunAckAllNotices();
          return;
        }
        if (t.classList.contains("sisun-toast-ack-btn")) {
          var ep = t.getAttribute("data-episode") || "";
          window.sisunAckNotice && window.sisunAckNotice(ep);
          return;
        }
        if (t.classList.contains("sisun-toast-goto")) {
          var cam = t.getAttribute("data-cam") || "";
          if (cam) {
            // 화면 이동만. 확인함으로 자동 처리하지 않음.
            goCameraTab(cam);
            setRailOpen(false);
          }
        }
      });
    }
    if (!window.__sisunRailOutsideBound) {
      window.__sisunRailOutsideBound = true;
      document.addEventListener("click", function(ev) {
        if (!isRailOpen()) return;
        var t = ev.target;
        var r = document.getElementById("sisun-alert-rail");
        var w = document.getElementById("sisun-bell-wrap");
        if ((r && r.contains(t)) || (w && w.contains(t))) return;
        setRailOpen(false);
      }, true);
    }
    // 아이콘/버튼 표시만 동기화 (상태 토글 금지 — 탭 폴링마다 깨지던 원인)
    syncMuteButton();
    var wrapBtn = wrap.querySelector(".sisun-bell-btn");
    if (wrapBtn) {
      wrapBtn.classList.toggle("is-muted", isBellMuted());
      wrapBtn.title = isBellMuted() ? "알림 목록 (꺼짐)" : "알림 목록";
    }
    if (isBellMuted()) silenceBeeps();
    setRailOpen(isRailOpen());
    renderBellList();
    placeAlertRail();
    return wrap;
  };
  window.__sisunNoticeSeq = window.__sisunNoticeSeq || 0;
  window.sisunPushToasts = function(items) {
    if (!items || !items.length) return;
    ensureBell();
    // 알림 꺼져도 목록·배지는 갱신. 소리만 막음.
    items.forEach(function(item) {
      if (!item) return;
      var ep = String(item.episode_id || item.event_id || ("tmp-" + (++window.__sisunNoticeSeq)));
      var op = String(item.op || "new");
      var found = null;
      for (var i = 0; i < __sisunNotices.length; i++) {
        if (__sisunNotices[i].episode_id === ep) { found = __sisunNotices[i]; break; }
      }
      var level = (item.level === "hot") ? "hot" : "warn";
      if (!found) {
        found = {
          episode_id: ep,
          level: level,
          severity_label: item.severity_label || (level === "hot" ? "위험" : "주의"),
          title: item.title || "",
          text: item.text || "",
          action: item.action || "",
          cam_id: item.cam_id || "",
          cam_code: item.cam_code || "",
          first_clock: item.first_clock || "",
          last_clock: item.last_clock || "",
          related_count: item.related_count || 1,
          ack: "pending",
          _seq: ++window.__sisunNoticeSeq
        };
        __sisunNotices.push(found);
      } else {
        found.level = level;
        found.severity_label = item.severity_label || found.severity_label;
        found.title = item.title || found.title;
        found.text = item.text || found.text;
        found.action = item.action || found.action;
        found.cam_id = item.cam_id || found.cam_id;
        found.cam_code = item.cam_code || found.cam_code;
        if (item.first_clock) found.first_clock = item.first_clock;
        found.last_clock = item.last_clock || found.last_clock;
        found.related_count = item.related_count || found.related_count;
        found._seq = ++window.__sisunNoticeSeq;
        // 중요도 상승 시 다시 확인 전
        if (item.ack_reset || op === "upgrade") {
          found.ack = "pending";
        }
      }
      // 위험 + 확인 전만 사이드바 N (화면 방문 표시, 확인함과 별개)
      if (found.level === "hot" && found.ack !== "done" && found.cam_id) {
        markSideNeed(String(found.cam_id));
      }
    });
    while (__sisunNotices.length > 40) __sisunNotices.shift();
    renderBellList();
    placeAlertRail();
  };
  window.sisunAckNotice = function(episodeId) {
    if (!episodeId) return;
    __sisunNotices.forEach(function(n) {
      if (n.episode_id === episodeId) n.ack = "done";
    });
    renderBellList();
  };
  window.sisunAckAllNotices = function() {
    // 운영자 확인함만. 경보 삭제·안전 전환·사이드 N 일괄 해제 아님.
    __sisunNotices.forEach(function(n) { n.ack = "done"; });
    renderBellList();
  };
  window.sisunClearToasts = function() {
    // 세션 리셋(새로고침)용: 목록 비움. 모두 확인함과 구분.
    __sisunNotices.length = 0;
    try {
      if (window.__sisunNotices && window.__sisunNotices !== __sisunNotices) {
        window.__sisunNotices.length = 0;
      }
    } catch (e0) {}
    document.querySelectorAll(".sisun-toast-payload").forEach(function(node) {
      var seq = node.getAttribute("data-seq") || "";
      if (seq) __sisunToastSeen[seq] = 1;
      try { node.remove(); } catch (e1) {}
    });
    renderBellList();
  };
  window.sisunRestartMainVideos = function() {
    var wall = document.getElementById("sisun-wall") || document.querySelector(".sisun-wall-main");
    var root = wall || document;
    root.querySelectorAll("video").forEach(function(v) {
      try {
        v.pause();
        if (v.fastSeek) {
          try { v.fastSeek(0); } catch (e0) { v.currentTime = 0; }
        } else {
          v.currentTime = 0;
        }
        // load()까지 하면 같은 src도 확실히 처음으로 감
        try { v.load(); } catch (e1) {}
        v.currentTime = 0;
        var p = v.play();
        if (p && p.catch) p.catch(function() {});
      } catch (e) {}
    });
    document.querySelectorAll(".sisun-restart-videos").forEach(function(m) {
      try { m.remove(); } catch (e2) {}
    });
    try { setBellMuted(false); } catch (e2b) {}
    try { window.sisunClearToasts && window.sisunClearToasts(); } catch (e3) {}
    try { resetSideNeeds(); } catch (e4) {}
  };
  var drainToastPayloads = function() {
    if (document.querySelector(".sisun-restart-videos")) {
      window.sisunRestartMainVideos();
    }
    ensureBell();
    var nodes = document.querySelectorAll(".sisun-toast-payload");
    if (nodes && nodes.length) {
      nodes.forEach(function(node) {
        var seq = node.getAttribute("data-seq") || "";
        if (seq && __sisunToastSeen[seq]) {
          node.remove();
          return;
        }
        if (seq) __sisunToastSeen[seq] = 1;
        var raw = node.getAttribute("data-items") || "[]";
        try {
          var items = JSON.parse(raw);
          window.sisunPushToasts(items);
        } catch (e) {}
        try { node.remove(); } catch (e2) {}
      });
    }
    // 알림 끄기 / 소리 끔이면 beep 즉시 제거
    if (soundOff()) {
      silenceBeeps();
      return;
    }
    allOf("audio.sisun-beep").forEach(function(a) {
      try { a.play && a.play().catch(function(){}); } catch (e4) {}
    });
  };
  ensureBell();
  if (!window.__sisunToastPoll) {
    window.__sisunToastPoll = true;
    setInterval(drainToastPayloads, 300);
    // 음소거 중엔 더 자주 훑어 autoplay 잔향 제거
    setInterval(function() {
      if (soundOff()) silenceBeeps();
    }, 80);
  }
  if (!window.__sisunUiPoll) {
    window.__sisunUiPoll = true;
    setInterval(function() {
      if (gateOn()) {
        paintWx();
        return;
      }
      hideGate();
      syncSide();
      bindTheme();
      paintWx();
      syncCctv();
      syncSideToggle();
      ensureBell();
      placeAlertRail();
      drainToastPayloads();
      syncSideNeedsFromOverlays();
    }, 2000);
  }
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
