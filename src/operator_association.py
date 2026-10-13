"""Camera-local probable rider association; overlap alone never proves a role."""
def probable_rider(person, vehicle):
    p=person.get('detected_bbox_xyxy',person['bbox_xyxy'])
    f=vehicle.get('detected_bbox_xyxy',vehicle['bbox_xyxy'])
    ph=p[3]-p[1];fh=f[3]-f[1]
    inter=max(0,min(p[2],f[2])-max(p[0],f[0]))*max(0,min(p[3],f[3])-max(p[1],f[1]))
    seated_extent=ph<=.75*fh and p[3]<=f[1]+.85*fh
    open_rider_extent=ph<=.98*fh and (p[2]-p[0])/ph>=.4 and p[3]<=f[1]+.99*fh
    return inter/max(1,ph*(p[2]-p[0]))>=.9 and (seated_extent or open_rider_extent)

class OperatorAssociation:
    def __init__(self,max_gap=1):
        self.max_gap=max_gap;self.pedestrians={}
    def reset(self):self.pedestrians.clear()
    def update(self,timestamp,people,vehicles):
        result={}
        for p in people:
            pid=p['track_id'];box=p.get('detected_bbox_xyxy',p['bbox_xyxy'])
            owners=[v for v in vehicles if probable_rider(p,v)]
            if not owners:
                self.pedestrians[pid]=timestamp;continue
            # Preserve recent outside-vehicle evidence when a pedestrian becomes occluded.
            if pid in self.pedestrians and timestamp-self.pedestrians[pid]<=self.max_gap:continue
            owner=min(owners,key=lambda v:(v['bbox_xyxy'][2]-v['bbox_xyxy'][0])*(v['bbox_xyxy'][3]-v['bbox_xyxy'][1]))
            result[pid]=owner['track_id']
        return result
