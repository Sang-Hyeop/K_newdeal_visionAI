# 역할: 사람과 지게차 겹침으로 탑승자(라이더) 후보를 추정한다. 역할 확정은 아니다.
"""사람과 지게차 겹침으로 탑승자(라이더) 후보를 추정한다. 역할 확정은 아니다."""


def probable_rider(person, vehicle):
    p = person.get("detected_bbox_xyxy", person["bbox_xyxy"])
    f = vehicle.get("detected_bbox_xyxy", vehicle["bbox_xyxy"])
    ph = p[3] - p[1]
    fh = f[3] - f[1]
    inter = max(0, min(p[2], f[2]) - max(p[0], f[0])) * max(
        0, min(p[3], f[3]) - max(p[1], f[1])
    )
    seated_extent = ph <= 0.75 * fh and p[3] <= f[1] + 0.85 * fh
    open_rider_extent = (
        ph <= 0.98 * fh and (p[2] - p[0]) / ph >= 0.4 and p[3] <= f[1] + 0.99 * fh
    )
    return inter / max(1, ph * (p[2] - p[0])) >= 0.9 and (
        seated_extent or open_rider_extent
    )


class OperatorAssociation:
    def __init__(self, max_gap=1):
        self.max_gap = max_gap
        self.pedestrians = {}

    def reset(self):
        self.pedestrians.clear()

    def update(self, timestamp, people, vehicles):
        result = {}
        for p in people:
            pid = p["track_id"]
            box = p.get("detected_bbox_xyxy", p["bbox_xyxy"])
            owners = [v for v in vehicles if probable_rider(p, v)]
            if not owners:
                self.pedestrians[pid] = timestamp
                continue
            # Preserve recent outside-vehicle evidence when a pedestrian becomes occluded.
            if (
                pid in self.pedestrians
                and timestamp - self.pedestrians[pid] <= self.max_gap
            ):
                continue
            owner = min(
                owners,
                key=lambda v: (
                    (v["bbox_xyxy"][2] - v["bbox_xyxy"][0])
                    * (v["bbox_xyxy"][3] - v["bbox_xyxy"][1])
                ),
            )
            result[pid] = owner["track_id"]
        return result


class TemporalOperatorAssociation:
    """Confirm a rider across images; preserve brief gaps, release independently moving people."""

    def __init__(self, max_gap=1.0, minimum_observations=3):
        self.gap = max_gap
        self.minimum = minimum_observations
        self.states = {}
        self.history = {}

    def reset(self):
        self.states.clear()
        self.history.clear()

    @staticmethod
    def center(box):
        return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

    def update(self, timestamp, people, vehicles):
        result = {}
        now = {}
        present = {p["track_id"] for p in people}
        for p in people:
            pid = p["track_id"]
            pb = p.get("detected_bbox_xyxy", p["bbox_xyxy"])
            pc = self.center(pb)
            old = self.states.get(pid)
            prior = self.history.get(pid)
            if old is None:
                transfers = [
                    (key, state)
                    for key, state in self.states.items()
                    if key not in present
                    and timestamp - state["timestamp"] <= self.gap
                    and (
                        (pc[0] - state["person_center"][0]) ** 2
                        + (pc[1] - state["person_center"][1]) ** 2
                    )
                    ** 0.5
                    < max(10, (pb[3] - pb[1]) * 0.4)
                ]
                if len(transfers) == 1:
                    old = self.states.pop(transfers[0][0])
                    prior = None
            candidates = []
            for v in vehicles:
                vb = v.get("detected_bbox_xyxy", v["bbox_xyxy"])
                vc = self.center(vb)
                vh = max(1, vb[3] - vb[1])
                vid = v["track_id"]
                plausible = probable_rider(p, v)
                consistent = False
                moving = False
                if old and timestamp - old["timestamp"] <= self.gap:
                    dx, dy = (
                        vc[0] - old["vehicle_center"][0],
                        vc[1] - old["vehicle_center"][1],
                    )
                    error = (
                        (pc[0] - old["person_center"][0] - dx) ** 2
                        + (pc[1] - old["person_center"][1] - dy) ** 2
                    ) ** 0.5 / vh
                    consistent = (
                        error < 0.18
                        and abs(vc[0] - old["vehicle_center"][0]) < vh * 0.8
                        and abs(vc[1] - old["vehicle_center"][1]) < vh * 0.8
                    )
                    moving = (dx * dx + dy * dy) ** 0.5 / vh > 0.025
                # Independent walking followed by a single overlap must not hide a pedestrian.
                recent_outside = (
                    prior
                    and not prior["candidate"]
                    and timestamp - prior["timestamp"] <= self.gap
                )
                if plausible:
                    candidates.append((v, consistent, moving))
            if candidates:
                v, consistent, moving = min(
                    candidates,
                    key=lambda pair: (
                        (pair[0]["bbox_xyxy"][2] - pair[0]["bbox_xyxy"][0])
                        * (pair[0]["bbox_xyxy"][3] - pair[0]["bbox_xyxy"][1])
                    ),
                )
                count = old["count"] + 1 if old and consistent else 1
                was_outside = (
                    old.get("was_outside", False)
                    if old
                    else bool(prior and not prior["candidate"])
                )
                movement_count = (
                    old.get("movement_count", 0) if old and consistent else 0
                ) + int(consistent and moving)
                state = dict(
                    timestamp=timestamp,
                    last_vehicle_observed=timestamp,
                    person_center=pc,
                    vehicle_center=self.center(
                        v.get("detected_bbox_xyxy", v["bbox_xyxy"])
                    ),
                    vehicle_id=v["track_id"],
                    count=count,
                    was_outside=was_outside,
                    movement_count=movement_count,
                )
                self.states[pid] = state
                if count >= self.minimum and (not was_outside or movement_count >= 2):
                    result[pid] = v["track_id"]
                    state["role_confirmed"] = True
                now[pid] = {"timestamp": timestamp, "candidate": True}
            elif (
                old
                and old.get("role_confirmed")
                and timestamp - old["last_vehicle_observed"] <= self.gap
            ):
                # No frozen body box: only a currently observed, geometrically continuous person retains its role.
                distance = (
                    (pc[0] - old["person_center"][0]) ** 2
                    + (pc[1] - old["person_center"][1]) ** 2
                ) ** 0.5
                owner = next(
                    (v for v in vehicles if v["track_id"] == old["vehicle_id"]), None
                )
                inside = True
                if owner:
                    vb = owner.get("detected_bbox_xyxy", owner["bbox_xyxy"])
                    inside = vb[0] <= pc[0] <= vb[2] and vb[1] <= pc[1] <= vb[3]
                if inside and distance < max(12, (pb[3] - pb[1]) * 0.25):
                    result[pid] = old["vehicle_id"]
                    self.states[pid] = {
                        **old,
                        "timestamp": timestamp,
                        "person_center": pc,
                    }
                else:
                    self.states.pop(pid, None)
                now[pid] = {"timestamp": timestamp, "candidate": False}
            else:
                self.states.pop(pid, None)
                now[pid] = {"timestamp": timestamp, "candidate": False}
        self.history = now
        self.states = {
            pid: s
            for pid, s in self.states.items()
            if timestamp - s["timestamp"] <= self.gap
        }
        return result
