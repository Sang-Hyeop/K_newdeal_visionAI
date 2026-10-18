"""Fire status history must remain visible without becoming camera alarm rows."""
import unittest
import pandas as pd
from dashboard.events import event_to_row
from dashboard.ui import table_html


class FireDisplayTests(unittest.TestCase):
    def event(self, reason, alert=False, timestamp=4.0):
        return {'event_type':'fire','video':'6_parking_lot_fire.mp4',
                'event_id':reason,'timestamp_seconds':timestamp,
                'severity':'CRITICAL' if alert else None,
                'observation_status':'confirmed' if alert else 'unconfirmed',
                'alert_eligible':alert,'track_ids':['FIRE2:1'],
                'evidence':{'reason':reason}}

    def test_camera_hides_pending_but_history_keeps_it(self):
        rows=[event_to_row(self.event('pending_temporal_confirmation')),
              event_to_row(self.event('repeated_fire_observations',True,4.6))]
        frame=pd.DataFrame(rows)
        self.assertEqual(rows[0]['status'],'확인 중')
        self.assertTrue(rows[0]['timestamp'].endswith('04.0'))
        self.assertTrue(rows[1]['timestamp'].endswith('04.6'))
        camera=table_html(frame)
        history=table_html(frame,include_fire_status=True)
        self.assertNotIn('반복 관측 확인 중',camera)
        self.assertIn('반복 관측에 따른 화재 의심',camera)
        self.assertIn('반복 관측 확인 중',history)
        self.assertEqual(len(frame),2)

    def test_lost_observation_is_distinct_and_never_safe(self):
        row=event_to_row(self.event('fire_not_observed'))
        self.assertEqual(row['status'],'관측 소실')
        self.assertIn('진화 여부 확인 필요',row['message'])
        frame=pd.DataFrame([row])
        self.assertNotIn(row['message'],table_html(frame))
        self.assertIn(row['message'],table_html(frame,include_fire_status=True))

    def test_nonfire_unknown_is_not_filtered(self):
        row=event_to_row(self.event('pending_temporal_confirmation'))
        row.update(scenario='ppe',status='미확인',message='기존 PPE 상태 유지')
        self.assertIn('기존 PPE 상태 유지',table_html(pd.DataFrame([row])))
