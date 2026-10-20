"""Alert clock is independent of the selected camera/page."""
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
    def test_first_playhead_after_initial_window_does_not_freeze_kpi(self):
        from dashboard.config import clock_start
        previous = dict(app._ALERT_BUS)
        frame = pd.DataFrame([{'area': 'A1', 'timestamp': clock_start() + pd.Timedelta(seconds=4)}])
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
