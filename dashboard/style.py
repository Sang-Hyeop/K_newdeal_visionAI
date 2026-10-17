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

.sisun-header {
  display: grid; grid-template-columns: minmax(160px,1fr) auto minmax(160px,1fr);
  align-items: center; gap: 10px 16px;
  min-height: 56px; padding: 8px 16px; margin: 0 -18px 12px -18px;
  background: var(--sisun-header-bg) !important;
  border-bottom: 1px solid var(--sisun-line) !important; color: var(--sisun-card-fg);
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
  gap: 2px; font-size: 13px; text-align: right; line-height: 1.35;
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
}
/* 사이드 fixed 공간 확보 (본문이 밑으로 들어가지 않게) */
html:not(.sisun-side-closed) .sisun-dash-row {
  padding-left: 214px !important; /* 200 사이드 + 14 간격 */
  box-sizing: border-box !important;
}
html.sisun-side-closed .sisun-dash-row { padding-left: 0 !important; }
.sisun-body { min-width: 0 !important; flex: 1 1 auto !important; width: 100% !important; }
.sisun-body .tab-nav, .sisun-tabs .tab-nav, .sisun-body [role="tablist"] {
  display: none !important; height: 0 !important; overflow: hidden !important;
  padding: 0 !important; margin: 0 !important; border: none !important;
}
#sisun-side, .sisun-side {
  /* 본문 스크롤과 분리 — 화면 왼쪽 고정, 메뉴만 안쪽 스크롤 */
  position: fixed !important;
  top: 72px !important;
  left: 18px !important;
  z-index: 40 !important;
  width: 200px !important;
  flex: 0 0 200px !important; min-width: 200px !important; max-width: 200px !important;
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
  width: 100% !important; min-height: 40px !important; border-radius: 10px !important;
  font-size: 13px !important; font-weight: 700 !important;
  text-align: left !important; justify-content: flex-start !important;
  background: #1a2230 !important;
  background-image: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,0) 55%) !important;
  color: #e8eef8 !important;
  border: 1px solid rgba(186, 198, 220, .28) !important;
  padding: 8px 12px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 2px 6px rgba(0,0,0,.22) !important;
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
.sisun-cam-slot .sisun-cam > .block:not(:has(.sisun-cam-tag)) {
  height: 100% !important; min-height: 100% !important;
  padding: 0 !important; margin: 0 !important;
  border: none !important; background: transparent !important;
}
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
/* 옆 목록: 글 + 작은 영상 썸네일 */
.sisun-theater-rail-list .sisun-cam {
  width: 100% !important; min-height: 110px !important; height: auto !important;
  aspect-ratio: 16 / 9 !important;
  cursor: pointer !important;
  border-color: rgba(186, 198, 220, .35) !important;
  pointer-events: auto !important;
}
.sisun-theater-rail-list .sisun-cam:hover {
  border-color: rgba(147, 197, 253, .75) !important;
}
.sisun-theater-rail-list .sisun-cam .block,
.sisun-theater-rail-list .sisun-cam .video-container,
.sisun-theater-rail-list .sisun-cam .wrap,
.sisun-theater-rail-list .sisun-cam .container,
.sisun-theater-rail-list .sisun-cam .sisun-cam-vid {
  height: 100% !important; min-height: 110px !important;
  width: 100% !important; display: block !important;
  padding: 0 !important; margin: 0 !important;
  border: none !important; background: #000 !important;
}
.sisun-theater-rail-list .sisun-cam video {
  width: 100% !important; height: 100% !important; min-height: 110px !important;
  object-fit: cover !important; display: block !important;
  opacity: 1 !important; visibility: visible !important;
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
  window.__sisunSound = true;
  var seenOn = new WeakMap();
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
  var wallClick = function(e) {
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
    // #1 메인 시어터
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
      side.style.setProperty("width", "200px", "important");
      side.style.setProperty("min-width", "200px", "important");
      side.style.setProperty("max-width", "200px", "important");
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
      var left = 18;
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
  }, 2000);
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
