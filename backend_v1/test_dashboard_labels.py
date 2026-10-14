import unittest

from dashboard_labels import (
    EMPTY_EVENTS_MESSAGE,
    EMPTY_OBSERVATIONS_MESSAGE,
    PRESENTATION_VIDEOS,
    display_state_label,
    empty_events_message,
    empty_observations_message,
    event_type_label,
    field_label,
    format_distance_meters,
    format_dwell_seconds,
    format_timestamp_seconds,
    global_safety_label,
    observation_status_label,
    ppe_state_label,
    presentation_video,
    region_label,
    severity_label,
)


class DashboardLabelTests(unittest.TestCase):
    def test_known_event_types(self):
        self.assertEqual(event_type_label('proximity'), '지게차·작업자 근접 위험')
        self.assertEqual(event_type_label('zone_access'), '구역 접근·진입')
        self.assertEqual(event_type_label('zone_dwell'), '구역 체류')
        self.assertEqual(event_type_label('ppe'), '안전모 착용 상태')
        self.assertEqual(event_type_label('status'), '상태 정보')

    def test_severity_and_unconfirmed_null(self):
        self.assertEqual(severity_label('SAFE'), '안전')
        self.assertEqual(severity_label('WARNING'), '주의')
        self.assertEqual(severity_label('CRITICAL'), '위험')
        self.assertEqual(severity_label(None, 'unconfirmed'), '미확인')
        self.assertEqual(severity_label(None), '미확인')
        self.assertNotEqual(severity_label(None), '안전')

    def test_observation_and_display_and_global(self):
        self.assertEqual(observation_status_label('confirmed'), '확인됨')
        self.assertEqual(observation_status_label('unconfirmed'), '미확인')
        self.assertEqual(display_state_label('UNKNOWN'), '미확인')
        self.assertEqual(global_safety_label('not_evaluated'), '평가하지 않음')

    def test_region_and_ppe(self):
        self.assertEqual(region_label('outside'), '구역 밖')
        self.assertEqual(region_label('approach'), '구역 접근')
        self.assertEqual(region_label('inside'), '구역 내부')
        self.assertEqual(region_label('unknown'), '미확인')
        self.assertEqual(ppe_state_label('no_helmet_candidate'), '미착용 후보')

    def test_unknown_enum_does_not_raise(self):
        self.assertEqual(event_type_label('not_a_real_type'), '알 수 없음 (not_a_real_type)')
        self.assertEqual(severity_label('BAD'), '알 수 없음 (BAD)')
        self.assertIn('mystery', region_label('mystery'))

    def test_empty_results(self):
        self.assertEqual(empty_events_message(), EMPTY_EVENTS_MESSAGE)
        self.assertEqual(empty_observations_message(), EMPTY_OBSERVATIONS_MESSAGE)
        self.assertEqual(empty_events_message(), '조회 결과 없음')
        self.assertEqual(empty_observations_message(), '관측 없음')

    def test_time_zero_and_fractional(self):
        self.assertEqual(format_timestamp_seconds(0), '0초')
        self.assertEqual(format_timestamp_seconds(0.0), '0초')
        self.assertEqual(format_timestamp_seconds(12.5), '12.5초')
        self.assertEqual(format_dwell_seconds(3.14159), '3.142초')
        self.assertNotIn('2026', format_timestamp_seconds(10))

    def test_distance_meters_never_invented(self):
        self.assertEqual(format_distance_meters(None), '미제공')
        self.assertIn('금지', format_distance_meters(1.2))

    def test_presentation_videos_match_api_contract(self):
        self.assertEqual(PRESENTATION_VIDEOS[1], '1_forklift_worker_collision_risk.mp4')
        self.assertEqual(PRESENTATION_VIDEOS[5], '5_Logistics Warehouse.mp4')
        for number in range(1, 6):
            self.assertEqual(presentation_video(number), PRESENTATION_VIDEOS[number])

    def test_field_labels_and_video_separation_keys(self):
        self.assertEqual(field_label('timestamp_seconds'), '영상 시간')
        self.assertEqual(field_label('observed_dwell_seconds'), '관측 체류시간')
        self.assertEqual(field_label('roi_id'), '구역 ID')
        # Filter/sort must keep raw English codes available beside labels.
        self.assertEqual(event_type_label('proximity'), '지게차·작업자 근접 위험')
        self.assertNotEqual('proximity', event_type_label('proximity'))


if __name__ == '__main__':
    unittest.main()
