"""PPE on boxes that mostly sit inside a forklift cannot prove helmet status."""
import math

def _overlap_ratio(person,vehicle):
    inter=max(0,min(person[2],vehicle[2])-max(person[0],vehicle[0]))*max(0,min(person[3],vehicle[3])-max(person[1],vehicle[1]))
    area=max(0,person[2]-person[0])*max(0,person[3]-person[1])
    return inter/area if area else 0

def apply_ppe_vehicle_guard(events,vehicle_boxes,minimum_overlap=.8):
    if not math.isfinite(minimum_overlap) or not 0<minimum_overlap<=1:
        raise ValueError('Invalid PPE vehicle overlap threshold')
    result=[]
    for original in events:
        event=dict(original);box=event.get('person_bbox_xyxy')
        if box and any(_overlap_ratio(box,vehicle)>=minimum_overlap for vehicle in vehicle_boxes):
            if event.get('severity') in ('SAFE','WARNING'):
                event.update(severity=None,observation_status='unconfirmed',classification_status='unconfirmed',ppe_state='unknown',reason='possible_operator_or_equipment_person_box')
            else:
                event.setdefault('reason',event.get('reason') or 'possible_operator_or_equipment_person_box')
                event.update(observation_status='unconfirmed',classification_status='unconfirmed')
        result.append(event)
    return result
