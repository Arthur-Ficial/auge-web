#!/usr/bin/env python3
"""Per-instance pose section renderer: each detected body / hand / animal gets
its own bbox-cutout SVG with skeleton edges + colored joint dots drawn at the
correct image position, plus the FULL coordinate list (x, y, confidence) of
every joint. No counts-only summaries — every joint name and value is shown.

Usage: _pose_render.py <json_file> <kind> <image_url> <image_w_px> <image_h_px>

kind ∈ {body, hand, animal}.

Vision delivers joints either as:
  - full image coords (current auge body-pose / hand-pose / animal-pose) — x, y in [0..1]
    over the whole image, bottom-origin
We draw them in the image's pixel space, then crop the SVG viewBox to a
padded bounding box around the instance's joints. Aspect ratio preserved.
"""

import html, json, os, sys

if len(sys.argv) != 6:
    sys.exit(0)

json_file, kind, img, w_arg, h_arg = sys.argv[1:6]

try:
    w_img = float(w_arg)
    h_img = float(h_arg)
except ValueError:
    sys.exit(0)

if not os.path.exists(json_file):
    sys.exit(0)

CONF_THRESHOLD = 0.05

BODY_EDGES = [
    ("head_joint", "neck_1_joint"),
    ("head_joint", "left_ear_joint"),
    ("head_joint", "right_ear_joint"),
    ("left_ear_joint", "left_eye_joint"),
    ("right_ear_joint", "right_eye_joint"),
    ("neck_1_joint", "left_shoulder_1_joint"),
    ("neck_1_joint", "right_shoulder_1_joint"),
    ("neck_1_joint", "root"),
    ("left_shoulder_1_joint", "left_forearm_joint"),
    ("left_forearm_joint", "left_hand_joint"),
    ("right_shoulder_1_joint", "right_forearm_joint"),
    ("right_forearm_joint", "right_hand_joint"),
    ("root", "left_upLeg_joint"),
    ("left_upLeg_joint", "left_leg_joint"),
    ("left_leg_joint", "left_foot_joint"),
    ("root", "right_upLeg_joint"),
    ("right_upLeg_joint", "right_leg_joint"),
    ("right_leg_joint", "right_foot_joint"),
]

HAND_EDGES = [
    ("VNHLKWRI", "VNHLKTCMC"),
    ("VNHLKTCMC", "VNHLKTMP"),
    ("VNHLKTMP", "VNHLKTIP"),
    ("VNHLKTIP", "VNHLKTTIP"),
    ("VNHLKWRI", "VNHLKIMCP"),
    ("VNHLKIMCP", "VNHLKIPIP"),
    ("VNHLKIPIP", "VNHLKIDIP"),
    ("VNHLKIDIP", "VNHLKITIP"),
    ("VNHLKWRI", "VNHLKMMCP"),
    ("VNHLKMMCP", "VNHLKMPIP"),
    ("VNHLKMPIP", "VNHLKMDIP"),
    ("VNHLKMDIP", "VNHLKMTIP"),
    ("VNHLKWRI", "VNHLKRMCP"),
    ("VNHLKRMCP", "VNHLKRPIP"),
    ("VNHLKRPIP", "VNHLKRDIP"),
    ("VNHLKRDIP", "VNHLKRTIP"),
    ("VNHLKWRI", "VNHLKPMCP"),
    ("VNHLKPMCP", "VNHLKPPIP"),
    ("VNHLKPPIP", "VNHLKPDIP"),
    ("VNHLKPDIP", "VNHLKPTIP"),
]

ANIMAL_EDGES = [
    ("animal_joint_left_eye", "animal_joint_right_eye"),
    ("animal_joint_left_eye", "animal_joint_nose"),
    ("animal_joint_right_eye", "animal_joint_nose"),
    ("animal_joint_left_ear_top", "animal_joint_left_ear_middle"),
    ("animal_joint_left_ear_middle", "animal_joint_left_ear_bottom"),
    ("animal_joint_right_ear_top", "animal_joint_right_ear_middle"),
    ("animal_joint_right_ear_middle", "animal_joint_right_ear_bottom"),
    ("animal_joint_neck", "animal_joint_heck"),
    ("animal_joint_neck", "animal_joint_left_front_elbow"),
    ("animal_joint_left_front_elbow", "animal_joint_left_front_knee"),
    ("animal_joint_left_front_knee", "animal_joint_left_front_paw"),
    ("animal_joint_neck", "animal_joint_right_front_elbow"),
    ("animal_joint_right_front_elbow", "animal_joint_right_front_knee"),
    ("animal_joint_right_front_knee", "animal_joint_right_front_paw"),
    ("animal_joint_heck", "animal_joint_left_back_elbow"),
    ("animal_joint_left_back_elbow", "animal_joint_left_back_knee"),
    ("animal_joint_left_back_knee", "animal_joint_left_back_paw"),
    ("animal_joint_heck", "animal_joint_right_back_elbow"),
    ("animal_joint_right_back_elbow", "animal_joint_right_back_knee"),
    ("animal_joint_right_back_knee", "animal_joint_right_back_paw"),
    ("animal_joint_heck", "animal_joint_tail_top"),
    ("animal_joint_tail_top", "animal_joint_tail_middle"),
    ("animal_joint_tail_middle", "animal_joint_tail_bottom"),
]

# Per-joint-group color codes. Reused for the swatch in the coord listing.
BODY_GROUPS = {
    "head_joint": ("#f97316", "head"),
    "left_ear_joint": ("#fb923c", "head"),
    "right_ear_joint": ("#fb923c", "head"),
    "left_eye_joint": ("#3b82f6", "eyes"),
    "right_eye_joint": ("#06b6d4", "eyes"),
    "neck_1_joint": ("#a855f7", "torso"),
    "root": ("#7c3aed", "torso"),
    "left_shoulder_1_joint": ("#10b981", "left arm"),
    "left_forearm_joint":    ("#10b981", "left arm"),
    "left_hand_joint":       ("#10b981", "left arm"),
    "right_shoulder_1_joint":("#22c55e", "right arm"),
    "right_forearm_joint":   ("#22c55e", "right arm"),
    "right_hand_joint":      ("#22c55e", "right arm"),
    "left_upLeg_joint":      ("#dc2626", "left leg"),
    "left_leg_joint":        ("#dc2626", "left leg"),
    "left_foot_joint":       ("#dc2626", "left leg"),
    "right_upLeg_joint":     ("#f43f5e", "right leg"),
    "right_leg_joint":       ("#f43f5e", "right leg"),
    "right_foot_joint":      ("#f43f5e", "right leg"),
}

HAND_GROUPS = {
    "VNHLKWRI": ("#94a3b8", "wrist"),
    # thumb
    "VNHLKTCMC": ("#dc2626", "thumb"), "VNHLKTMP": ("#dc2626", "thumb"),
    "VNHLKTIP":  ("#dc2626", "thumb"), "VNHLKTTIP":("#dc2626", "thumb"),
    # index
    "VNHLKIMCP": ("#f97316", "index"), "VNHLKIPIP": ("#f97316", "index"),
    "VNHLKIDIP": ("#f97316", "index"), "VNHLKITIP": ("#f97316", "index"),
    # middle
    "VNHLKMMCP": ("#10b981", "middle"), "VNHLKMPIP": ("#10b981", "middle"),
    "VNHLKMDIP": ("#10b981", "middle"), "VNHLKMTIP": ("#10b981", "middle"),
    # ring
    "VNHLKRMCP": ("#3b82f6", "ring"),  "VNHLKRPIP": ("#3b82f6", "ring"),
    "VNHLKRDIP": ("#3b82f6", "ring"),  "VNHLKRTIP": ("#3b82f6", "ring"),
    # pinky
    "VNHLKPMCP": ("#a855f7", "pinky"), "VNHLKPPIP": ("#a855f7", "pinky"),
    "VNHLKPDIP": ("#a855f7", "pinky"), "VNHLKPTIP": ("#a855f7", "pinky"),
}

ANIMAL_GROUPS = {
    "animal_joint_left_eye":  ("#3b82f6", "head"),
    "animal_joint_right_eye": ("#06b6d4", "head"),
    "animal_joint_nose":      ("#f97316", "head"),
    "animal_joint_left_ear_top":    ("#fb923c", "head"),
    "animal_joint_left_ear_middle": ("#fb923c", "head"),
    "animal_joint_left_ear_bottom": ("#fb923c", "head"),
    "animal_joint_right_ear_top":    ("#fb923c", "head"),
    "animal_joint_right_ear_middle": ("#fb923c", "head"),
    "animal_joint_right_ear_bottom": ("#fb923c", "head"),
    "animal_joint_neck":      ("#a855f7", "neck/back"),
    "animal_joint_heck":      ("#a855f7", "neck/back"),
    "animal_joint_left_front_elbow":  ("#10b981", "left front"),
    "animal_joint_left_front_knee":   ("#10b981", "left front"),
    "animal_joint_left_front_paw":    ("#10b981", "left front"),
    "animal_joint_right_front_elbow": ("#22c55e", "right front"),
    "animal_joint_right_front_knee":  ("#22c55e", "right front"),
    "animal_joint_right_front_paw":   ("#22c55e", "right front"),
    "animal_joint_left_back_elbow":   ("#dc2626", "left back"),
    "animal_joint_left_back_knee":    ("#dc2626", "left back"),
    "animal_joint_left_back_paw":     ("#dc2626", "left back"),
    "animal_joint_right_back_elbow":  ("#f43f5e", "right back"),
    "animal_joint_right_back_knee":   ("#f43f5e", "right back"),
    "animal_joint_right_back_paw":    ("#f43f5e", "right back"),
    "animal_joint_tail_top":    ("#facc15", "tail"),
    "animal_joint_tail_middle": ("#facc15", "tail"),
    "animal_joint_tail_bottom": ("#facc15", "tail"),
}

CONFIG = {
    "body":   ("bodies",  BODY_EDGES,   BODY_GROUPS,   "person"),
    "hand":   ("hands",   HAND_EDGES,   HAND_GROUPS,   "hand"),
    "animal": ("animals", ANIMAL_EDGES, ANIMAL_GROUPS, "animal"),
}

if kind not in CONFIG:
    sys.exit(0)

items_key, edges, groups, label = CONFIG[kind]
DEFAULT_COLOR = "#374151"

try:
    with open(json_file) as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)

instances = (data.get("results") or {}).get(items_key) or []
if not instances:
    sys.exit(0)


def vis_to_px(jx, jy):
    return jx * w_img, (1.0 - jy) * h_img


for ii, inst in enumerate(instances, start=1):
    joints = inst.get("joints", []) or []
    if not joints:
        # Still print a "no-joints" line for truthfulness.
        print(f'    <div class="bbox-row pose-row"><span>{label} {ii} — '
              f'<em class="dim">no joints reported</em></span></div>')
        continue

    # Bounding box from confident joints; fall back to all joints if all lowconf.
    confident_pts = [(j["x"], 1.0 - j["y"])
                     for j in joints
                     if j.get("confidence", 0) >= CONF_THRESHOLD]
    if not confident_pts:
        confident_pts = [(j["x"], 1.0 - j["y"]) for j in joints]

    xs = [p[0] for p in confident_pts]
    ys = [p[1] for p in confident_pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    pad_x = max(0.04, (maxx - minx) * 0.18)
    pad_y = max(0.04, (maxy - miny) * 0.18)
    bx = max(0.0, minx - pad_x)
    by = max(0.0, miny - pad_y)
    bw = min(1.0 - bx, (maxx - minx) + 2 * pad_x)
    bh = min(1.0 - by, (maxy - miny) + 2 * pad_y)

    px_x = bx * w_img
    px_y = by * h_img
    px_w = max(1.0, bw * w_img)
    px_h = max(1.0, bh * h_img)

    radius = max(1.5, min(px_w, px_h) * 0.014)
    stroke = max(0.8, radius * 0.45)

    svg = [
        f'<svg class="bbox-thumb pose-thumb" '
        f'viewBox="{px_x:.2f} {px_y:.2f} {px_w:.2f} {px_h:.2f}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'<image href="{html.escape(img)}" x="0" y="0" '
        f'width="{w_img:.0f}" height="{h_img:.0f}" preserveAspectRatio="none"/>'
    ]

    by_name = {j["name"]: j for j in joints}
    # bones first (under the dots).
    for a, b in edges:
        ja, jb = by_name.get(a), by_name.get(b)
        if not ja or not jb:
            continue
        if ja.get("confidence", 0) < CONF_THRESHOLD or jb.get("confidence", 0) < CONF_THRESHOLD:
            continue
        ax, ay = vis_to_px(ja["x"], ja["y"])
        bx2, by2 = vis_to_px(jb["x"], jb["y"])
        svg.append(
            f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx2:.2f}" y2="{by2:.2f}" '
            f'stroke="white" stroke-width="{stroke*1.5:.2f}" stroke-linecap="round"/>'
        )
        svg.append(
            f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx2:.2f}" y2="{by2:.2f}" '
            f'stroke="#1f2937" stroke-width="{stroke*0.8:.2f}" stroke-linecap="round"/>'
        )

    # joints on top.
    for j in joints:
        color, _ = groups.get(j["name"], (DEFAULT_COLOR, "?"))
        cx, cy = vis_to_px(j["x"], j["y"])
        opacity = "1.0" if j.get("confidence", 0) >= CONF_THRESHOLD else "0.35"
        svg.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" '
            f'fill="{color}" stroke="white" stroke-width="{stroke:.2f}" opacity="{opacity}"/>'
        )

    svg.append("</svg>")
    svg_html = "".join(svg)

    # Compute mean confidence across all joints (always available since
    # auge reports a per-joint confidence in [0..1]).
    confs = [j.get("confidence", 0.0) for j in joints]
    confident_confs = [c for c in confs if c >= CONF_THRESHOLD]
    if confs:
        avg_all = sum(confs) / len(confs)
        avg_html_parts = [f'avg confidence <strong>{avg_all*100:.1f}%</strong>']
        if confident_confs:
            avg_conf = sum(confident_confs) / len(confident_confs)
            avg_html_parts.append(
                f'(of {len(confident_confs)} confident joint{"s" if len(confident_confs) != 1 else ""}: '
                f'<strong>{avg_conf*100:.1f}%</strong>)'
            )
        avg_html = " ".join(avg_html_parts)
    else:
        avg_html = '<em class="dim">no confidence reported</em>'

    print(f'    <div class="bbox-row pose-row">{svg_html}'
          f'<span>{label} {ii} — {len(joints)} joints — {avg_html}</span></div>')

    # Group joints by region so the listing is scannable, but every joint name
    # + (x, y, confidence) value is printed in full.
    region_buckets = {}
    region_order = []
    for j in joints:
        color, region = groups.get(j["name"], (DEFAULT_COLOR, "other"))
        if region not in region_buckets:
            region_buckets[region] = (color, [])
            region_order.append(region)
        region_buckets[region][1].append(j)

    for region in region_order:
        color, group_joints = region_buckets[region]
        items_html = []
        for j in group_joints:
            conf = j.get("confidence", 0)
            items_html.append(
                f'<span class="lm-pt">'
                f'<code>{html.escape(j["name"])}</code> '
                f'({j["x"]:.3f}, {j["y"]:.3f}) c={conf:.2f}'
                f'</span>'
            )
        items = " ".join(items_html)
        print(
            f'      <div class="lm-region">'
            f'<span class="lm-swatch" style="background:{color}"></span>'
            f'<strong>{html.escape(region)}</strong> '
            f'<span class="lm-count">{len(group_joints)} joint{"s" if len(group_joints) != 1 else ""}</span>'
            f' <span class="lm-coords">{items}</span>'
            f'</div>'
        )
