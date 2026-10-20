# 역할: 지게차와 사람이 한 박스에 합쳐진 경우 보행자 박스를 분리·보존한다.
"""지게차와 사람이 한 박스에 합쳐진 경우 보행자 박스를 분리·보존한다."""


def separate_merged_vehicle_people(detections):
    vehicles = [d for d in detections if d["class"] == "forklift"]
    people = [d for d in detections if d["class"] == "person"]
    rejected = []
    blocked = set()

    def area(b):
        return max(1, (b[2] - b[0]) * (b[3] - b[1]))

    def inter(a, b):
        return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
            0, min(a[3], b[3]) - max(a[1], b[1])
        )

    for p in people:
        b = p["bbox_xyxy"]
        ph = b[3] - b[1]
        for other in people:
            if other is p:
                continue
            a = other["bbox_xyxy"]
            ah = a[3] - a[1]
            same_extent = abs(a[1] - b[1]) < 0.15 * max(ph, ah) and abs(
                a[3] - b[3]
            ) < 0.15 * max(ph, ah)
            common_vehicle = any(
                inter(a, v["bbox_xyxy"]) / area(a) > 0.9
                and inter(b, v["bbox_xyxy"]) / area(b) > 0.9
                for v in vehicles
            )
            if (
                area(a) > 1.4 * area(b)
                and inter(a, b) / area(b) > 0.9
                and same_extent
                and common_vehicle
            ):
                blocked.add(id(p))
                rejected.append(
                    {
                        **p,
                        "review_reason": "duplicate_body_same_vehicle_and_vertical_extent",
                        "role": "duplicate",
                    }
                )
                break
        if id(p) in blocked:
            continue
        for v in vehicles:
            vb = v["bbox_xyxy"]
            # A box spanning upper rider/vehicle and a separately detected lower pedestrian is not a reliable single body.
            if not (
                b[1] < vb[3] - 0.25 * (vb[3] - vb[1])
                and b[3] > vb[3] + 0.2 * ph
                and inter(b, vb) / area(b) > 0.25
            ):
                continue
            separate = any(
                q is not p
                and area(b) > 1.4 * area(q["bbox_xyxy"])
                and inter(b, q["bbox_xyxy"]) / area(q["bbox_xyxy"]) > 0.85
                and q["bbox_xyxy"][1] > b[1] + 0.25 * ph
                and abs(q["bbox_xyxy"][3] - b[3]) < 0.15 * ph
                for q in people
            )
            if separate:
                rejected.append(
                    {
                        **p,
                        "review_reason": "merged_vehicle_rider_and_separate_pedestrian",
                        "role": "unassessable",
                    }
                )
                blocked.add(id(p))
                break
    return [d for d in detections if id(d) not in blocked], rejected
