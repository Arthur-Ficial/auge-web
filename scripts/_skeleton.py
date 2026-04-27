#!/usr/bin/env python3
"""Render a Vision pose JSON file as an SVG skeleton overlay.

Usage:
    _skeleton.py <json_file> <kind> <css_class>

kind ∈ {body, hand, animal}.

Emits an SVG with `viewBox="0 0 1 1"` containing one set of bones + dots per
detected instance. Joint Y coords are flipped (Vision uses bottom-origin).

Outputs nothing if file missing, no instances, or all confidences < threshold.
"""

import json, os, sys

CONF_THRESHOLD = 0.05

# --- Edge tables ----------------------------------------------------------

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

EDGE_TABLES = {
    "body":   ("bodies",  BODY_EDGES),
    "hand":   ("hands",   HAND_EDGES),
    "animal": ("animals", ANIMAL_EDGES),
}


def main():
    if len(sys.argv) != 4:
        print("usage: _skeleton.py <json_file> <kind> <css_class>", file=sys.stderr)
        sys.exit(2)

    json_file, kind, cls = sys.argv[1], sys.argv[2], sys.argv[3]
    if not os.path.exists(json_file):
        return
    if kind not in EDGE_TABLES:
        print(f"unknown kind: {kind}", file=sys.stderr)
        sys.exit(2)

    items_key, edges = EDGE_TABLES[kind]
    try:
        with open(json_file) as fh:
            data = json.load(fh)
    except Exception:
        return

    instances = (data.get("results") or {}).get(items_key) or []
    if not instances:
        return

    # Use the same NEON palette as _pose_render.py so big-image overlays and
    # per-instance section thumbs are visually consistent.
    BODY_COLOR = {
        "head_joint": "#ff00aa",
        "left_ear_joint": "#ff7f00", "right_ear_joint": "#ff7f00",
        "left_eye_joint": "#00e0ff", "right_eye_joint": "#00ffff",
        "neck_1_joint": "#bf00ff", "root": "#9d00ff",
        "left_shoulder_1_joint": "#00ff66", "left_forearm_joint": "#00ff66", "left_hand_joint": "#00ff66",
        "right_shoulder_1_joint": "#39ff14", "right_forearm_joint": "#39ff14", "right_hand_joint": "#39ff14",
        "left_upLeg_joint": "#ff1744", "left_leg_joint": "#ff1744", "left_foot_joint": "#ff1744",
        "right_upLeg_joint": "#ff4081", "right_leg_joint": "#ff4081", "right_foot_joint": "#ff4081",
    }
    HAND_COLOR = {
        "VNHLKWRI": "#ffffff",
        "VNHLKTCMC": "#ff1744", "VNHLKTMP": "#ff1744", "VNHLKTIP": "#ff1744", "VNHLKTTIP": "#ff1744",
        "VNHLKIMCP": "#ff7f00", "VNHLKIPIP": "#ff7f00", "VNHLKIDIP": "#ff7f00", "VNHLKITIP": "#ff7f00",
        "VNHLKMMCP": "#39ff14", "VNHLKMPIP": "#39ff14", "VNHLKMDIP": "#39ff14", "VNHLKMTIP": "#39ff14",
        "VNHLKRMCP": "#00e0ff", "VNHLKRPIP": "#00e0ff", "VNHLKRDIP": "#00e0ff", "VNHLKRTIP": "#00e0ff",
        "VNHLKPMCP": "#ff00aa", "VNHLKPPIP": "#ff00aa", "VNHLKPDIP": "#ff00aa", "VNHLKPTIP": "#ff00aa",
    }
    ANIMAL_COLOR = {
        "animal_joint_left_eye": "#00e0ff", "animal_joint_right_eye": "#00ffff",
        "animal_joint_nose": "#ff00aa",
        "animal_joint_left_ear_top": "#ff7f00", "animal_joint_left_ear_middle": "#ff7f00", "animal_joint_left_ear_bottom": "#ff7f00",
        "animal_joint_right_ear_top": "#ff7f00", "animal_joint_right_ear_middle": "#ff7f00", "animal_joint_right_ear_bottom": "#ff7f00",
        "animal_joint_neck": "#bf00ff", "animal_joint_heck": "#bf00ff",
        "animal_joint_left_front_elbow": "#00ff66", "animal_joint_left_front_knee": "#00ff66", "animal_joint_left_front_paw": "#00ff66",
        "animal_joint_right_front_elbow": "#39ff14", "animal_joint_right_front_knee": "#39ff14", "animal_joint_right_front_paw": "#39ff14",
        "animal_joint_left_back_elbow": "#ff1744", "animal_joint_left_back_knee": "#ff1744", "animal_joint_left_back_paw": "#ff1744",
        "animal_joint_right_back_elbow": "#ff4081", "animal_joint_right_back_knee": "#ff4081", "animal_joint_right_back_paw": "#ff4081",
        "animal_joint_tail_top": "#fff200", "animal_joint_tail_middle": "#fff200", "animal_joint_tail_bottom": "#fff200",
    }
    COLOR_TABLE = {"body": BODY_COLOR, "hand": HAND_COLOR, "animal": ANIMAL_COLOR}[kind]
    BIG_JOINTS = {
        "head_joint", "animal_joint_nose",
        "VNHLKWRI", "VNHLKTTIP", "VNHLKITIP", "VNHLKMTIP", "VNHLKRTIP", "VNHLKPTIP",
    }
    DEFAULT = "#ffffff"

    parts = [f'<svg class="{cls}" viewBox="0 0 1 1" preserveAspectRatio="none">']
    any_drawn = False
    for inst in instances:
        joints = {j["name"]: j for j in inst.get("joints", [])}
        # Bones — fat white halo + neon coloured core, matching section thumbs.
        for a, b in edges:
            ja, jb = joints.get(a), joints.get(b)
            if not ja or not jb:
                continue
            if ja.get("confidence", 0) < CONF_THRESHOLD or jb.get("confidence", 0) < CONF_THRESHOLD:
                continue
            ax, ay = ja["x"], 1.0 - ja["y"]
            bx, by = jb["x"], 1.0 - jb["y"]
            limb_color = COLOR_TABLE.get(b, COLOR_TABLE.get(a, DEFAULT))
            parts.append(
                f'<line x1="{ax:.4f}" y1="{ay:.4f}" x2="{bx:.4f}" y2="{by:.4f}" '
                f'stroke="white" stroke-width="0.012" stroke-linecap="round" opacity="0.95"/>'
            )
            parts.append(
                f'<line x1="{ax:.4f}" y1="{ay:.4f}" x2="{bx:.4f}" y2="{by:.4f}" '
                f'stroke="{limb_color}" stroke-width="0.0065" stroke-linecap="round"/>'
            )
            any_drawn = True
        # Joints — neon dot with white halo. Head / nose / wrist / fingertips
        # rendered nearly twice as large.
        for j in inst.get("joints", []):
            if j.get("confidence", 0) < CONF_THRESHOLD:
                continue
            cx, cy = j["x"], 1.0 - j["y"]
            color = COLOR_TABLE.get(j["name"], DEFAULT)
            r = 0.013 if j["name"] in BIG_JOINTS else 0.0085
            parts.append(
                f'<circle cx="{cx:.4f}" cy="{cy:.4f}" r="{r * 1.35:.4f}" '
                f'fill="white" opacity="0.85"/>'
            )
            parts.append(
                f'<circle cx="{cx:.4f}" cy="{cy:.4f}" r="{r:.4f}" fill="{color}"/>'
            )
            any_drawn = True

    if not any_drawn:
        return

    parts.append("</svg>")
    print("".join(parts))


if __name__ == "__main__":
    main()
