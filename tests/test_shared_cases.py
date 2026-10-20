# 역할: 임시 공용 DB의 상태 공유·동시 조치·연결 실패 동작을 회귀 검증합니다.
"""임시 공용 DB의 상태 공유·동시 조치·연결 실패 동작을 회귀 검증합니다."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from dashboard import alert_response as ar
from dashboard.case_server import CaseService

META = dict(link_key='A1|collision|person:2|e0:E1', cam_id='A1', scenario='collision',
            subject='person:2', anchor_event_id='E1', event_ids=['E1'], grade='위험', level='hot')


def action(prev, nxt, req, who='작업자 A'):
    return dict(META, request_id=req, prev_status=prev, next_status=nxt,
                operator=who, note='현장 확인 및 조치' if nxt in ('acting', 'done') else '')


class SharedStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'shared.sqlite3'
        self.store = CaseService(self.db)
        self.env = patch.dict(os.environ, {'SISUN_CASE_SERVER': ''})
        self.env.start()

    def tearDown(self):
        self.env.stop(); self.tmp.cleanup(); ar.reset_response_memory()

    def state(self):
        rows = self.store.execute('snapshot', [])['rows']
        ar.reset_response_memory()
        for row in rows:
            ar._apply_row_to_memory(row)
        return dict(ar._CURRENT[META['link_key']])

    def test_same_case_assignment_and_daily_count_shared_after_restart(self):
        self.store.execute('observations', [[['new', META]]])
        first = self.state()
        self.store = CaseService(self.db)
        self.store.execute('observations', [[['new', META]]])
        second = self.state()
        self.assertEqual(first['assigned_to'], second['assigned_to'])
        rows = self.store.execute('snapshot', [])['rows']
        self.assertEqual(sum(r['kind'] == 'case_open' for r in rows), 1)
        self.assertEqual(sum(r['kind'] == 'observation_day' for r in rows), 1)

    def test_two_writers_cannot_skip_or_overwrite_operator(self):
        self.store.execute('observations', [[['new', META]]])
        self.store.execute('apply_transition', [action('new', 'acked', 'a')])
        results = []
        def work(who):
            try:
                self.store.execute('apply_transition', [action('acked', 'acting', who, who)])
                results.append(True)
            except ValueError:
                results.append(False)
        threads = [threading.Thread(target=work,args=(who,)) for who in ['A','B']]
        for t in threads:t.start()
        for t in threads:t.join()
        rows = self.store.execute('snapshot', [])['rows']
        self.assertEqual(sum(r.get('next_status') == 'acting' for r in rows), 1)
        self.assertIn(self.state()['last_operator'], ['A','B'])
        with self.assertRaises(ValueError):
            self.store.execute('apply_transition', [action('new','done','bad')])

    def test_detection_replay_does_not_reopen_completed_shared_case(self):
        self.store.execute('observations', [[['new',META]]])
        for prev,nxt in [('new','acked'),('acked','acting'),('acting','done')]:
            self.store.execute('apply_transition',[action(prev,nxt,nxt)])
        self.store.execute('observations', [[['upgrade',META]]])
        self.assertEqual(self.state()['status'],'done')
        duplicate = self.store.execute('apply_transition',[action('acting','done','done')])
        self.assertEqual(duplicate['state']['status'], 'done')
        rows=self.store.execute('snapshot',[])['rows']
        self.assertEqual(sum(r.get('next_status')=='done' for r in rows),1)

    def test_failed_transaction_leaves_database_unchanged(self):
        before=self.store.execute('snapshot',[])['rows']
        with self.assertRaises(ValueError):
            self.store.execute('apply_transition',[action('new','done','invalid')])
        self.assertEqual(self.store.execute('snapshot',[])['rows'],before)

    def test_explicit_import_preserves_old_records_and_rejects_second_import(self):
        p=Path(self.tmp.name)/'source.jsonl'
        row=dict(META,kind='case_open',assigned_to='담당자 A',operator_at='2026-10-19 09:00:00')
        p.write_text(json.dumps(row),encoding='utf-8')
        self.assertEqual(self.store.import_log(p),1)
        self.assertEqual(self.state()['opened_at'],'2026-10-19 09:00:00')
        with self.assertRaises(ValueError):self.store.import_log(p)
        self.assertEqual(json.loads(p.read_text()),row)


class SharedHTTPTests(unittest.TestCase):
    def test_two_independent_clients_authentication_and_offline_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,SISUN_CASE_TOKEN='integration-test-only',SISUN_CASE_SERVER='')
            server=subprocess.Popen([sys.executable,'-u','-m','dashboard.case_server','--port','0','--db',str(Path(tmp)/'shared.db')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                line=server.stdout.readline().strip()
                self.assertTrue(line.startswith('Case server:'),line)
                url=line.split('Case server: ',1)[1]
                env.update(SISUN_CASE_SERVER=url)
                def client(code):
                    result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=15)
                    self.assertEqual(result.returncode,0,result.stderr)
                    return json.loads(result.stdout)
                prefix='from dashboard import alert_response as a; import json; '
                created=client(prefix+f'print(json.dumps(a.ensure_case({META!r})))')
                client(prefix+f'print(json.dumps(a.apply_transition({action("new","acked","rpc-a")!r})))')
                seen=client(prefix+f'print(json.dumps(a.get_state_by_link({META["link_key"]!r})))')
                self.assertEqual(seen['state']['status'],'acked')
                self.assertEqual(seen['state']['last_operator'],'작업자 A')
                self.assertEqual(seen['state']['assigned_to'],created['state']['assigned_to'])
                client(prefix+f'print(json.dumps(a.apply_transition({action("acked","acting","rpc-b","작업자 B")!r})))')
                detail=client(prefix+f'print(json.dumps(a.case_detail({META["link_key"]!r})))')
                self.assertEqual(detail['state']['status'],'acting')
                self.assertEqual(detail['state']['last_operator'],'작업자 B')
                self.assertEqual(len(detail['history']),3)
                request=urllib.request.Request(url+'/rpc',data=b'{}',method='POST')
                with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(request)
                self.assertEqual(err.exception.code,401)
                server.terminate();server.wait(timeout=10)
                failed=subprocess.run([sys.executable,'-c',prefix+f'a.apply_transition({action("acting","done","offline")!r})'],env=env,capture_output=True,text=True,timeout=10)
                self.assertNotEqual(failed.returncode,0)
                self.assertIn('저장되지 않았습니다',failed.stderr)
            finally:
                if server.poll() is None:server.terminate();server.wait(timeout=10)
                server.stdout.close();server.stderr.close()
