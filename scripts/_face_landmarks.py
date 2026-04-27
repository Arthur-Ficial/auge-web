#!/usr/bin/env python3
"""Render every face's landmarks: the face thumbnail with each landmark
region's points drawn at the correct image position in a distinct colour,
plus the FULL coordinate list for every point — no counts-only summary.

Usage: _face_landmarks.py <json_file> <image_url> <image_w_px> <image_h_px>
"""

import html, json, sys

if len(sys.argv) != 5:
    sys.exit(0)

json_file = sys.argv[1]
img = sys.argv[2]
try:
    w_img = float(sys.argv[3])
    h_img = float(sys.argv[4])
except ValueError:
    sys.exit(0)

try:
    with open(json_file) as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)

faces = (data.get("results") or {}).get("faces") or []
if not faces:
    sys.exit(0)

# Distinct, nameable colours per landmark region. Match a perceptual hue.
REGION_COLOR = {
    "faceContour":  "#94a3b8",  # slate
    "leftEye":      "#3b82f6",  # blue
    "rightEye":     "#06b6d4",  # cyan
    "leftPupil":    "#dc2626",  # red
    "rightPupil":   "#f87171",  # red-light
    "leftEyebrow":  "#8b5cf6",  # violet
    "rightEyebrow": "#a855f7",  # purple
    "nose":         "#f97316",  # orange
    "noseCrest":    "#f59e0b",  # amber
    "medianLine":   "#10b981",  # emerald
    "innerLips":    "#be185d",  # rose-deep
    "outerLips":    "#ec4899",  # rose
}
DEFAULT_COLOR = "#374151"


def vis_to_px(face_box, px, py):
    """Convert a landmark point (normalized to the face bbox, Vision bottom-origin)
    into pixel coords of the source image (top-origin SVG)."""
    fx, fy, fw, fh = face_box["x"], face_box["y"], face_box["width"], face_box["height"]
    norm_x = fx + px * fw
    norm_y = fy + py * fh   # still bottom-origin
    return norm_x * w_img, (1.0 - norm_y) * h_img


def fmt_coord(p):
    return f"({p['x']:.3f}, {p['y']:.3f})"


for fi, face in enumerate(faces, start=1):
    fx, fy, fw, fh = face["x"], face["y"], face["width"], face["height"]
    # Pixel rect of the face crop (top-origin for SVG).
    top_y = max(0.0, 1.0 - fy - fh)
    px_x = fx * w_img
    px_y = top_y * h_img
    px_w = max(1.0, fw * w_img)
    px_h = max(1.0, fh * h_img)

    landmarks = face.get("landmarks") or {}
    # Sorted region names for consistent output.
    region_names = sorted(landmarks.keys())

    # Build the SVG with: image + landmark circles in pixel coords.
    svg_parts = [
        f'<svg class="bbox-thumb landmark-thumb" '
        f'viewBox="{px_x:.2f} {px_y:.2f} {px_w:.2f} {px_h:.2f}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'<image href="{html.escape(img)}" x="0" y="0" '
        f'width="{w_img:.0f}" height="{h_img:.0f}" preserveAspectRatio="none"/>'
    ]
    radius = max(1.0, min(px_w, px_h) * 0.012)
    for region in region_names:
        color = REGION_COLOR.get(region, DEFAULT_COLOR)
        for pt in landmarks[region]:
            cx, cy = vis_to_px(face, pt["x"], pt["y"])
            svg_parts.append(
                f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" '
                f'fill="{color}" stroke="white" stroke-width="{radius*0.35:.2f}"/>'
            )
    svg_parts.append("</svg>")
    svg = "".join(svg_parts)

    # Pose (roll/yaw/pitch) line.
    roll = face.get("roll")
    yaw  = face.get("yaw")
    pitch = face.get("pitch")
    if roll is not None and yaw is not None and pitch is not None:
        import math
        deg = lambda r: r * 180.0 / math.pi
        pose_html = (
            f'roll <strong>{deg(roll):.2f}°</strong> · '
            f'yaw <strong>{deg(yaw):.2f}°</strong> · '
            f'pitch <strong>{deg(pitch):.2f}°</strong>'
        )
    else:
        pose_html = '<em class="dim">pose not reported</em>'

    # Region legend with FULL coordinates per point.
    region_html_lines = []
    for region in region_names:
        color = REGION_COLOR.get(region, DEFAULT_COLOR)
        pts = landmarks[region]
        coords = ", ".join(fmt_coord(p) for p in pts)
        region_html_lines.append(
            f'      <div class="lm-region">'
            f'<span class="lm-swatch" style="background:{color}"></span>'
            f'<strong>{html.escape(region)}</strong> '
            f'<span class="lm-count">{len(pts)} pt{"s" if len(pts) != 1 else ""}</span>'
            f' <span class="lm-coords">{coords}</span>'
            f'</div>'
        )

    print(
        f'    <div class="bbox-row landmark-row">'
        f'{svg}'
        f'<span>face {fi} — bbox=({fx:.3f}, {fy:.3f}, {fw:.3f}, {fh:.3f}) — {pose_html}</span>'
        f'</div>'
    )
    print("\n".join(region_html_lines))
