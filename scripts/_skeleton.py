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

    parts = [f'<svg class="{cls}" viewBox="0 0 1 1" preserveAspectRatio="none">']
    any_drawn = False
    for inst in instances:
        joints = {j["name"]: j for j in inst.get("joints", [])}
        for a, b in edges:
            ja, jb = joints.get(a), joints.get(b)
            if not ja or not jb:
                continue
            if ja.get("confidence", 0) < CONF_THRESHOLD or jb.get("confidence", 0) < CONF_THRESHOLD:
                continue
            ax, ay = ja["x"], 1.0 - ja["y"]
            bx, by = jb["x"], 1.0 - jb["y"]
            parts.append(f'<line x1="{ax:.4f}" y1="{ay:.4f}" x2="{bx:.4f}" y2="{by:.4f}"/>')
            any_drawn = True
        for j in inst.get("joints", []):
            if j.get("confidence", 0) < CONF_THRESHOLD:
                continue
            cx, cy = j["x"], 1.0 - j["y"]
            parts.append(f'<circle cx="{cx:.4f}" cy="{cy:.4f}" r="0.006"/>')
            any_drawn = True

    if not any_drawn:
        return

    parts.append("</svg>")
    print("".join(parts))


if __name__ == "__main__":
    main()
