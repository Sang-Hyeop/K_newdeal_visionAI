"""Add video6 to the current dashboard without changing warehouse camera behavior."""
def register(namespace):
    if not (namespace['VIDEO_DIR'] / '6_parking_lot_fire.mp4').exists():
        return
    if 'parking' in namespace['SITE_BY_ID']:
        return
    video = '6_parking_lot_fire.mp4'
    site = {'id':'parking','name':'주차장','color':'#dc2626'}
    camera = {'id':'P1','site':'parking','name':'주차장','cam':'CAM06','color':'#dc2626','video_num':6,'scenario':'fire','src':video,'origin':'origin_P1.mp4','detect':'detect_P1.mp4'}
    scenario = {'id':'fire','name':'화재 의심','color':'#dc2626','cam':'CAM06'}
    namespace['TABS'].append({'id':'parking','name':'#7 주차장'})
    namespace['SITES'].append(site)
    namespace['SITE_BY_ID'][site['id']] = site
    namespace['CAMERAS'].append(camera)
    namespace['CAM_BY_ID'][camera['id']] = camera
    namespace['SCENARIOS'].append(scenario)
    namespace['SC_BY_ID']['fire'] = scenario
    namespace['SID_TO_VIDEO']['fire'] = 6
    namespace['SID_TO_EVENT_TYPE']['fire'] = 'fire'
    namespace['VIDEO_FILES']['fire'] = video
    namespace['TYPE_TO_SCENARIO']['fire'] = 'fire'
    namespace['NEEDED_VIDEOS'] = tuple(namespace['NEEDED_VIDEOS']) + (6,)
