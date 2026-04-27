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

# Per-joint-group NEON colours. Bright, saturated, visible on any background.
# The head joint gets a flashing-magenta-style hue and is drawn larger so it's
# unmissable.
BODY_GROUPS = {
    "head_joint":             ("#ff00aa", "head"),   # neon magenta — biggest dot
    "left_ear_joint":         ("#ff7f00", "head"),   # neon orange
    "right_ear_joint":        ("#ff7f00", "head"),
    "left_eye_joint":         ("#00e0ff", "eyes"),   # neon cyan
    "right_eye_joint":        ("#00ffff", "eyes"),   # bright cyan
    "neck_1_joint":           ("#bf00ff", "torso"),  # neon violet
    "root":                   ("#9d00ff", "torso"),
    "left_shoulder_1_joint":  ("#00ff66", "left arm"),  # neon green
    "left_forearm_joint":     ("#00ff66", "left arm"),
    "left_hand_joint":        ("#00ff66", "left arm"),
    "right_shoulder_1_joint": ("#39ff14", "right arm"), # electric green
    "right_forearm_joint":    ("#39ff14", "right arm"),
    "right_hand_joint":       ("#39ff14", "right arm"),
    "left_upLeg_joint":       ("#ff1744", "left leg"),  # neon red
    "left_leg_joint":         ("#ff1744", "left leg"),
    "left_foot_joint":        ("#ff1744", "left leg"),
    "right_upLeg_joint":      ("#ff4081", "right leg"), # hot pink
    "right_leg_joint":        ("#ff4081", "right leg"),
    "right_foot_joint":       ("#ff4081", "right leg"),
}

HAND_GROUPS = {
    "VNHLKWRI": ("#ffffff", "wrist"),
    # thumb — neon red
    "VNHLKTCMC": ("#ff1744", "thumb"), "VNHLKTMP":  ("#ff1744", "thumb"),
    "VNHLKTIP":  ("#ff1744", "thumb"), "VNHLKTTIP": ("#ff1744", "thumb"),
    # index — neon orange
    "VNHLKIMCP": ("#ff7f00", "index"), "VNHLKIPIP": ("#ff7f00", "index"),
    "VNHLKIDIP": ("#ff7f00", "index"), "VNHLKITIP": ("#ff7f00", "index"),
    # middle — neon green
    "VNHLKMMCP": ("#39ff14", "middle"), "VNHLKMPIP": ("#39ff14", "middle"),
    "VNHLKMDIP": ("#39ff14", "middle"), "VNHLKMTIP": ("#39ff14", "middle"),
    # ring — neon cyan
    "VNHLKRMCP": ("#00e0ff", "ring"), "VNHLKRPIP": ("#00e0ff", "ring"),
    "VNHLKRDIP": ("#00e0ff", "ring"), "VNHLKRTIP": ("#00e0ff", "ring"),
    # pinky — neon magenta
    "VNHLKPMCP": ("#ff00aa", "pinky"), "VNHLKPPIP": ("#ff00aa", "pinky"),
    "VNHLKPDIP": ("#ff00aa", "pinky"), "VNHLKPTIP": ("#ff00aa", "pinky"),
}

ANIMAL_GROUPS = {
    "animal_joint_left_eye":          ("#00e0ff", "head"),
    "animal_joint_right_eye":         ("#00ffff", "head"),
    "animal_joint_nose":              ("#ff00aa", "head"),
    "animal_joint_left_ear_top":      ("#ff7f00", "head"),
    "animal_joint_left_ear_middle":   ("#ff7f00", "head"),
    "animal_joint_left_ear_bottom":   ("#ff7f00", "head"),
    "animal_joint_right_ear_top":     ("#ff7f00", "head"),
    "animal_joint_right_ear_middle":  ("#ff7f00", "head"),
    "animal_joint_right_ear_bottom":  ("#ff7f00", "head"),
    "animal_joint_neck":              ("#bf00ff", "neck/back"),
    "animal_joint_heck":              ("#bf00ff", "neck/back"),
    "animal_joint_left_front_elbow":  ("#00ff66", "left front"),
    "animal_joint_left_front_knee":   ("#00ff66", "left front"),
    "animal_joint_left_front_paw":    ("#00ff66", "left front"),
    "animal_joint_right_front_elbow": ("#39ff14", "right front"),
    "animal_joint_right_front_knee":  ("#39ff14", "right front"),
    "animal_joint_right_front_paw":   ("#39ff14", "right front"),
    "animal_joint_left_back_elbow":   ("#ff1744", "left back"),
    "animal_joint_left_back_knee":    ("#ff1744", "left back"),
    "animal_joint_left_back_paw":     ("#ff1744", "left back"),
    "animal_joint_right_back_elbow":  ("#ff4081", "right back"),
    "animal_joint_right_back_knee":   ("#ff4081", "right back"),
    "animal_joint_right_back_paw":    ("#ff4081", "right back"),
    "animal_joint_tail_top":          ("#fff200", "tail"),
    "animal_joint_tail_middle":       ("#fff200", "tail"),
    "animal_joint_tail_bottom":       ("#fff200", "tail"),
}

# Joints rendered noticeably larger so they pop out — head + nose primarily.
LARGE_JOINTS = {
    "head_joint",
    "animal_joint_nose",
    # hand wrist + finger tips deserve emphasis too.
    "VNHLKWRI",
    "VNHLKTTIP", "VNHLKITIP", "VNHLKMTIP", "VNHLKRTIP", "VNHLKPTIP",
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

    # Sized so the dots and bones are visibly chunky on small thumbs and the
    # giant overlay alike. Tied to the smaller of the two pixel dimensions.
    base = min(px_w, px_h)
    radius = max(3.0, base * 0.022)        # joint dot
    big_radius = radius * 1.65              # head / nose / wrist / fingertips
    bone_outline = max(2.0, base * 0.012)   # white halo around bones
    bone_core    = max(1.2, base * 0.0065)  # neon coloured inner stroke

    svg = [
        f'<svg class="bbox-thumb pose-thumb" '
        f'viewBox="{px_x:.2f} {px_y:.2f} {px_w:.2f} {px_h:.2f}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'<image href="{html.escape(img)}" x="0" y="0" '
        f'width="{w_img:.0f}" height="{h_img:.0f}" preserveAspectRatio="none"/>'
    ]

    by_name = {j["name"]: j for j in joints}
    # Bones first — drawn as a fat white halo + a neon coloured inner stroke
    # tinted by the limb's joint group. Visible on dark and light images alike.
    for a, b in edges:
        ja, jb = by_name.get(a), by_name.get(b)
        if not ja or not jb:
            continue
        if ja.get("confidence", 0) < CONF_THRESHOLD or jb.get("confidence", 0) < CONF_THRESHOLD:
            continue
        ax, ay = vis_to_px(ja["x"], ja["y"])
        bx2, by2 = vis_to_px(jb["x"], jb["y"])
        # Limb colour: pick the joint that's NOT a generic wrist/root/neck.
        limb_color = (
            groups.get(b, (DEFAULT_COLOR, ""))[0]
            if groups.get(b, (DEFAULT_COLOR, ""))[1] not in ("wrist", "torso")
            else groups.get(a, (DEFAULT_COLOR, ""))[0]
        )
        svg.append(
            f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx2:.2f}" y2="{by2:.2f}" '
            f'stroke="white" stroke-width="{bone_outline:.2f}" '
            f'stroke-linecap="round" opacity="0.95"/>'
        )
        svg.append(
            f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx2:.2f}" y2="{by2:.2f}" '
            f'stroke="{limb_color}" stroke-width="{bone_core:.2f}" '
            f'stroke-linecap="round"/>'
        )

    # Joints on top. Head / nose / wrist / fingertips are drawn LARGER so the
    # focal anatomy reads at any thumbnail size.
    for j in joints:
        color, _ = groups.get(j["name"], (DEFAULT_COLOR, "?"))
        cx, cy = vis_to_px(j["x"], j["y"])
        is_big = j["name"] in LARGE_JOINTS
        r = big_radius if is_big else radius
        opacity = "1.0" if j.get("confidence", 0) >= CONF_THRESHOLD else "0.35"
        # Outer white halo for contrast on any background, then the coloured dot.
        svg.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r * 1.35:.2f}" '
            f'fill="white" opacity="{0.85 if is_big else 0.7}"/>'
        )
        svg.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="{color}" stroke="white" stroke-width="{max(1.0, r * 0.25):.2f}" '
            f'opacity="{opacity}"/>'
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
