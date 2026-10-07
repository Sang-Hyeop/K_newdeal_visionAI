"""Explicit class routing for a separately evaluated person detector."""
import hashlib,json


def route_detections(objects, people=None):
    """Use one person source, retain forklift source; no silent union or veto."""
    if people is None:
        return [dict(d) for d in objects]
    return [dict(d, detection_source='objects') for d in objects if d['class']=='forklift'] + [
        dict(d, detection_source='people') for d in people if d['class']=='person']


def model_version(object_hash, person_hash=None):
    if person_hash is None:
        return object_hash
    return hashlib.sha256(json.dumps({'forklift':object_hash,'person':person_hash,
                                     'routing':'separate_person_source_v1'},sort_keys=True).encode()).hexdigest()
