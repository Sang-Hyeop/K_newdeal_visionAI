"""Person-guided PPE inference. Per-frame observations, never safety decisions."""
import math


def head_matches_person(head, person, image_height=None):
    """Reject body-sized boxes and heads outside this person's upper region."""
    x1, y1, x2, y2 = person
    a, b, c, d = head
    pw, ph = x2 - x1, y2 - y1
    if pw <= 0 or ph <= 0 or c <= a or d <= b:
        return False
    clipped = image_height is not None and y1 > 3 and image_height - max(2, .01 * image_height) <= y2 <= image_height + 1
    # Visible head size cannot use full-body proportions when legs are off-frame.
    # Continue rejecting body-sized proposals; do not change risk foot anchors.
    head_width, head_height = c-a, d-b
    height_limit = min(.85 * ph, .95 * pw, 1.6 * head_width) if clipped else .4 * ph
    width_limit = .9 * pw if clipped else 1.1 * pw
    upper_fraction = .65 if clipped else .35
    return (x1 - .15 * pw <= (a + c) / 2 <= x2 + .15 * pw
            and y1 - .1 * ph <= (b + d) / 2 <= y1 + upper_fraction * ph
            and head_height <= height_limit and head_width <= width_limit)


def head_owner(head, people, image_height=None):
    """Select nearest compatible upper-head anchor; ties stay unassigned."""
    a,b,c,d=head;cx,cy=(a+c)/2,(b+d)/2
    scores=[]
    for index,person in enumerate(people):
        if head_matches_person(head,person,image_height):
            x1,y1,x2,y2=person
            scores.append(((cx-(x1+x2)/2)**2+(cy-(y1+.1*(y2-y1)))**2,index))
    scores.sort()
    if not scores or (len(scores)>1 and abs(scores[0][0]-scores[1][0])<1):
        return None
    return scores[0][1]


def infer_person_ppe(frame, people, model, conf=.25, imgsz=640, full_frame_heads=None, crop_height_fraction=.55):
    if model.names != {0: 'helmeted_head', 1: 'no_helmet_head'}:
        raise ValueError('Unexpected PPE classes')
    if not math.isfinite(crop_height_fraction) or not .35 <= crop_height_fraction <= 1:
        raise ValueError('crop_height_fraction must be in [.35, 1]')
    if not 0 < conf <= 1:
        raise ValueError('conf must be in (0, 1]')
    h, w = frame.shape[:2]
    people=[list(map(float,p)) for p in people]
    for person in people:
        if len(person)!=4 or not all(math.isfinite(v) for v in person) or person[2]<=person[0] or person[3]<=person[1]:
            raise ValueError('Invalid person box')
    observations = []
    for index, person in enumerate(people):
        person = list(map(float, person))
        if len(person) != 4 or not all(math.isfinite(v) for v in person):
            raise ValueError('Expected finite XYXY person box')
        x1, y1, x2, y2 = person
        pw, ph = x2 - x1, y2 - y1
        if pw <= 0 or ph <= 0:
            raise ValueError('Invalid person box')
        a, b = max(0, int(x1 - .15 * pw)), max(0, int(y1 - .1 * ph))
        c, d = min(w, math.ceil(x2 + .15 * pw)), min(h, math.ceil(y1 + crop_height_fraction * ph))
        record = {'person_index': index, 'person_bbox_xyxy': person,
                  'crop_bbox_xyxy': [a, b, c, d], 'state': 'unknown',
                  'head_candidates': [], 'rejected_candidates': [],
                  'risk_status': 'not_evaluated'}
        for candidate in full_frame_heads or []:
            if candidate['confidence'] >= conf and head_owner(candidate['bbox_xyxy'], people,h)==index:
                record['head_candidates'].append({**candidate, 'source': candidate.get('source','full_frame')})
        if c <= a or d <= b:
            observations.append(record)
            continue
        prediction = model.predict(frame[b:d, a:c], imgsz=imgsz, conf=conf,
                                   device='cpu', verbose=False)[0]
        for box in prediction.boxes:
            hx1, hy1, hx2, hy2 = box.xyxy[0].tolist()
            head = [hx1 + a, hy1 + b, hx2 + a, hy2 + b]
            candidate = {'class': model.names[int(box.cls.item())],
                         'confidence': float(box.conf.item()), 'bbox_xyxy': head,
                         'source': 'person_crop',
                         'model_sources': getattr(box, 'model_sources', ['single_ppe_model'])}
            key = 'head_candidates' if head_owner(head, people,h)==index else 'rejected_candidates'
            record[key].append(candidate)
        classes = {r['class'] for r in record['head_candidates']}
        if classes == {'helmeted_head'}:
            record['state'] = 'helmet_detected'
        elif classes == {'no_helmet_head'}:
            # A hood or occluded head can be misclassified; no automatic violation.
            record['state'] = 'no_helmet_candidate'
        elif len(classes) > 1:
            record['state'] = 'conflicting_evidence'
        observations.append(record)
    return observations
