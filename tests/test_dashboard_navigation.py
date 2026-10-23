# 역할: 페이지 이동과 독립적인 경보 및 N·체크 표시 동작을 회귀 검증합니다.
"""페이지 이동과 독립적인 경보 및 N·체크 표시 동작을 회귀 검증합니다."""
import unittest
from unittest.mock import patch
import pandas as pd
from dashboard import app
from dashboard.config import CAMERAS

class AlertClockTests(unittest.TestCase):
    def test_one_clock_for_all_cameras_without_page_input(self):
        previous=dict(app._ALERT_BUS)
        try:
            with patch.object(app.time,'monotonic',return_value=100):
                app._alert_bus_reset()
                app._alert_bus_start()
            with patch.object(app.time,'monotonic',return_value=125), patch.object(app,'get_df',return_value=pd.DataFrame({'x':[1]})), patch.object(app,'live_positions',return_value='slice') as collect, patch.object(app,'notify',return_value=None):
                app._alert_bus_tick()
                self.assertEqual(collect.call_args.args[1], {c['id']:25.0 for c in CAMERAS})
            with patch.object(app.time,'monotonic',return_value=140):
                self.assertEqual(app._alert_bus_elapsed(),40)
        finally:
            app._ALERT_BUS.clear();app._ALERT_BUS.update(previous)


class BrowserLogicTests(unittest.TestCase):
    """Run the shipped browser logic with small DOM/media fakes, not a rewrite."""
    def run_js(self, source):
        import shutil, subprocess
        from pathlib import Path
        node=shutil.which('node') or str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
        if not Path(node).is_file():
            self.skipTest('Node is required for browser logic regression tests')
        result=subprocess.run([node,'-e',source],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_camera_review_does_not_clear_other_camera_or_rearm_on_update(self):
        from dashboard.style import BOOT_JS
        start=BOOT_JS.index('  var __sisunSideNeed =')
        end=BOOT_JS.index('  var wallClick =',start)
        self.run_js('''
const assert=require('node:assert/strict'); const elements={};
function el(){return {children:[],classList:{toggle(){}},setAttribute(){},appendChild(c){this.children.push(c)},querySelector(s){return s==='button'?null:(this.children[0]||null)}}}
for(const id of ['A1','A2','P1']) elements['sisun-side-'+id]=el();
const window={}; const document={getElementById(id){return elements[id]||null},createElement:el,addEventListener(){}};
''' + BOOT_JS[start:end] + '''
markSideNeed('A1');markSideNeed('A2');markSideNeed('P1');clearSideNeed('A1');
assert.equal(__sisunSideNeed.A1,false);assert.equal(__sisunSideNeed.A2,true);assert.equal(__sisunSideNeed.P1,true);
assert.equal(elements['sisun-side-A1'].children[0].textContent,'✓');
markSideNeed('A1');assert.equal(__sisunSideNeed.A1,true);
''')

    def test_main_video_keeps_playing_when_hidden_and_does_not_rewind(self):
        from dashboard.style import BOOT_JS
        start = BOOT_JS.index('  var syncCctv =')
        end = BOOT_JS.index('  var tick =', start)
        self.run_js('''
const assert=require('node:assert/strict');let shown=true,pauses=0,plays=0;
const seenOn=new WeakMap();const gateOn=()=>false;
const video={currentTime:12,paused:false,setAttribute(){},
closest(s){return s==='.sisun-wall-main'?{}:null},
getBoundingClientRect(){return {width:shown?640:0,height:shown?360:0}},
pause(){pauses++;this.paused=true},play(){plays++;this.paused=false;return Promise.resolve()}};
const allOf=()=>[video];
''' + BOOT_JS[start:end] + '''
syncCctv();shown=false;syncCctv();shown=true;syncCctv();
assert.equal(pauses,0);assert.equal(video.currentTime,12);
video.paused=true;shown=false;syncCctv();assert.equal(plays,1);
''')

    def test_mute_label_only_controls_sound(self):
        from dashboard.style import BOOT_JS
        self.assertNotIn('알림 끄기</button>', BOOT_JS)
        self.assertIn('소리 끄기</button>', BOOT_JS)
        start = BOOT_JS.index('  var syncMuteButton =')
        end = BOOT_JS.index('  var setBellMuted =', start)
        self.run_js('''
const assert=require('node:assert/strict');let muted=false;
const button={classList:{toggle(){}},setAttribute(){}};
const document={getElementById(){return {querySelector(){return button}}}};
const isBellMuted=()=>muted;
''' + BOOT_JS[start:end] + '''
syncMuteButton();assert.equal(button.textContent,'소리 끄기');
muted=true;syncMuteButton();assert.equal(button.textContent,'소리 켜기');
''')

    def test_detached_audio_finishes_and_old_callback_cannot_stop_new_audio(self):
        from dashboard.style import BOOT_JS
        start=BOOT_JS.index('  var __sisunSoundPlayed =')
        end=BOOT_JS.index('  // 음소거 중 play() 차단',start)
        self.run_js('''
const assert=require('node:assert/strict');const window={};const allOf=()=>[];
class Audio {constructor(src){this.src=src} play(){return Promise.resolve()}pause(){} removeAttribute(){}load(){}}
function tag(id){return {getAttribute(k){return k==='data-sound-id'?id:'test.wav'},removeAttribute(){},pause(){},load(){},remove(){this.removed=true}}}
''' + BOOT_JS[start:end] + '''
let a=tag('1');armBeepOnce(a);const first=window.__sisunActiveBeep;const oldDone=first.onended;
assert.ok(a.removed);armBeepOnce(tag('2'));assert.equal(window.__sisunActiveBeep,first);
first.onended();assert.equal(window.__sisunActiveBeep,null);
armBeepOnce(tag('3'));const second=window.__sisunActiveBeep;assert.ok(second);oldDone();assert.equal(window.__sisunActiveBeep,second);
silenceBeeps();assert.equal(window.__sisunActiveBeep,null);armBeepOnce(tag('3'));assert.equal(window.__sisunActiveBeep,null);
window.__sisunBellMuted=true;armBeepOnce(tag('4'));window.__sisunBellMuted=false;armBeepOnce(tag('4'));assert.equal(window.__sisunActiveBeep,null);
''')

    def test_filters_rebuild_after_gradio_recreates_empty_container(self):
        from dashboard.style import BOOT_JS
        start=BOOT_JS.index('  var bindCasesScope =')
        end=BOOT_JS.index('  var casesQuery =',start)
        self.run_js('''
const assert=require('node:assert/strict');const __cases={filtersReady:true,filterValues:{'cf-cam':'A2'}};
const box={innerHTML:'',querySelector(){return this.innerHTML.includes("id='cf-st'")?{}:null}};
const els={};const document={getElementById(id){if(id==='sisun-cases-filters')return box;return els[id]||(els[id]={value:'all'})}};
const window={sisunCasesRefresh(){}};
''' + BOOT_JS[start:end] + '''
ensureCasesFilters();assert.ok(box.innerHTML.includes("id='cf-st'"));assert.equal(els['cf-cam'].value,'A2');
box.innerHTML='';ensureCasesFilters();assert.ok(box.innerHTML.includes("id='cf-st'"));
assert.equal(typeof els['cases-all'].onclick,'function');els['cases-all'].onclick();assert.equal(els['cf-st'].value,'__all_incl_done');
''')

class DelayedMainStartTests(unittest.TestCase):
    def test_login_and_refresh_preserve_app_start_timestamp(self):
        from dashboard import config
        previous = dict(app._ALERT_BUS)
        base = config.clock_start()
        try:
            with patch.object(app, '_ensure_clip', return_value=None), patch.object(app, '_existing', return_value=None), patch.object(app, 'reset_notify_state'), patch.object(app, 'load_df', return_value=None):
                demo = app.make_main(CAMERAS)
                demo._kpi_new_session()
                demo._live_begin()
                refresh = next(fn.fn for fn in demo.fns.values() if getattr(fn.fn, '__name__', '') == 'refresh')
                refresh()
                self.assertEqual(config.clock_start(), base)
        finally:
            app._ALERT_BUS.clear()
            app._ALERT_BUS.update(previous)

    def test_global_monitor_counts_without_main_page_timer(self):
        previous = dict(app._ALERT_BUS)
        frame = pd.DataFrame([{'area': 'A1', '_video_seconds': 4}, {'area': 'A1', '_video_seconds': 20}])
        try:
            app._ALERT_BUS['on'] = True
            with patch.object(app, '_alert_bus_tick', return_value='notifications'), patch.object(app, 'get_df', return_value=frame), patch.object(app, 'kpi_html', side_effect=len):
                with patch.object(app, '_alert_bus_elapsed', return_value=8):
                    self.assertEqual(app._global_monitor_tick(), ('notifications', 1))
                with patch.object(app, '_alert_bus_elapsed', return_value=25):
                    self.assertEqual(app._global_monitor_tick(), ('notifications', 2))
        finally:
            app._ALERT_BUS.clear()
            app._ALERT_BUS.update(previous)

    def test_main_counts_while_other_page_has_no_video_playheads(self):
        previous = dict(app._ALERT_BUS)
        frame = pd.DataFrame([
            {'area': 'A1', '_video_seconds': 4},
            {'area': 'A1', '_video_seconds': 20},
        ])
        try:
            with patch.object(app, '_ensure_clip', return_value=None), patch.object(app, '_existing', return_value=None), patch.object(app, 'reset_notify_state'), patch.object(app, 'kpi_html', side_effect=lambda d: 0 if d is None else len(d)), patch.object(app, 'get_df', return_value=frame), patch.object(app, 'danger_overlay_updates', return_value=()):
                demo = app.make_main(CAMERAS)
                demo._live_begin()
                app._alert_bus_start()
                stopped = demo._live_stop()
                self.assertTrue(stopped[len(CAMERAS)])
                self.assertTrue(stopped[-1]['active'])
                tick = next(fn.fn for fn in demo.fns.values() if getattr(fn.fn, '__name__', '') == 'tick')
                with patch.object(app, '_alert_bus_elapsed', return_value=8):
                    self.assertEqual(tick(True, {}, True)[0], 1)
                with patch.object(app, '_alert_bus_elapsed', return_value=25):
                    self.assertEqual(tick(True, {}, True)[0], 2)
                with patch.object(app, '_alert_bus_elapsed', return_value=30):
                    self.assertEqual(tick(True, {'A1': 0}, True)[0], 2)
        finally:
            app._ALERT_BUS.clear()
            app._ALERT_BUS.update(previous)

    def test_first_playhead_after_initial_window_does_not_freeze_kpi(self):
        from dashboard.config import clock_start
        previous = dict(app._ALERT_BUS)
        frame = pd.DataFrame([{'area': 'A1', 'timestamp': clock_start() + pd.Timedelta(seconds=4), '_video_seconds': 4}])
        try:
            with patch.object(app, '_ensure_clip', return_value=None), patch.object(app, '_existing', return_value=None), patch.object(app, 'reset_notify_state'), patch.object(app, 'kpi_html', side_effect=lambda d: 0 if d is None else len(d)), patch.object(app, 'get_df', return_value=frame), patch.object(app, 'danger_overlay_updates', return_value=()):
                demo = app.make_main(CAMERAS)
                demo._live_begin()
                tick = next(fn.fn for fn in demo.fns.values() if getattr(fn.fn, '__name__', '') == 'tick')
                self.assertEqual(tick(True, {}, True)[0], 0)
                self.assertEqual(tick(True, {'A1': 8.0}, True)[0], 1)
        finally:
            app._ALERT_BUS.clear()
            app._ALERT_BUS.update(previous)

class MainReturnResetTests(unittest.TestCase):
    run_js = BrowserLogicTests.run_js
    def test_remounted_main_restores_elapsed_position_without_resetting_notices(self):
        from dashboard.style import BOOT_JS
        start = BOOT_JS.index('    // Gradio가 숨긴 페이지')
        end = BOOT_JS.index('    // Gradio re-creates', start)
        self.run_js('''
const assert=require('node:assert/strict');const window={};let played=0,removed=0;
const video={duration:21,readyState:2,currentTime:0,play(){played++;return Promise.resolve()}};
const marker={getAttribute(k){return k==='data-token'?'resume-1':'30'},remove(){removed++}};
const document={querySelectorAll(){return [marker]},getElementById(){return {querySelectorAll(){return [video]}}}};
''' + BOOT_JS[start:end] + '''
assert.ok(video.currentTime>=9 && video.currentTime<10);assert.equal(played,1);assert.equal(removed,1);
''')

    def test_remounted_restart_marker_does_not_clear_unreviewed_cameras(self):
        from dashboard.style import BOOT_JS
        start = BOOT_JS.index('    // Gradio re-creates the stored HTML')
        end = BOOT_JS.index('    ensureBell();', start)
        self.run_js('''
const assert=require('node:assert/strict');
let markers=[]; let resets=0; let notices=[]; let need={};
const document={querySelectorAll(){return markers}};
const window={sisunRestartMainVideos(){resets++;notices=[];need={}}};
function marker(token){return {getAttribute(){return token},remove(){}}}
function drain(){
''' + BOOT_JS[start:end] + '''
}
markers=[marker('login-1')];drain();assert.equal(resets,1);
need={A1:false,A2:true,B1:true,P1:true};notices=['A2','B1','P1'];
markers=[marker('login-1')];drain();
assert.equal(resets,1);assert.deepEqual(notices,['A2','B1','P1']);
assert.equal(need.A2,true);assert.equal(need.B1,true);assert.equal(need.P1,true);
markers=[marker('refresh-2')];drain();assert.equal(resets,2);
''')


class MainCheckDismissTests(unittest.TestCase):
    run_js = BrowserLogicTests.run_js

    def test_main_click_dismisses_checks_but_keeps_unread_and_notices(self):
        from dashboard.style import BOOT_JS
        start = BOOT_JS.index('  if (!window.__sisunSideNeedBound)')
        end = BOOT_JS.index('  var syncReviewedCamera', start)
        self.run_js('''
const assert=require('node:assert/strict');let listener;let __sisunViewingCam='A1';
const __sisunSideNeed={A1:false,A2:true,B1:true,P1:true};
const __sisunSideReviewed={A1:true};const notices=['A2','B1','P1'];const painted=[];
const window={};const document={addEventListener(type,fn){listener=fn}};
const isCameraSideId=id=>/^(A[1-4]|B1|P1)$/.test(id);
const paintSideNeed=id=>painted.push(id);
''' + BOOT_JS[start:end] + '''
listener({target:{closest(){return {id:'sisun-side-main'}}}});
assert.equal(__sisunViewingCam,'');assert.deepEqual(__sisunSideReviewed,{});
assert.equal(__sisunSideNeed.A1,false);assert.equal(__sisunSideNeed.A2,true);
assert.equal(__sisunSideNeed.B1,true);assert.equal(__sisunSideNeed.P1,true);
assert.deepEqual(notices,['A2','B1','P1']);assert.deepEqual(painted,['A1']);
''')
