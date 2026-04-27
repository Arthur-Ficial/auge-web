#!/usr/bin/env python3
"""Per-contour section renderer: each contour path becomes a bbox-cutout SVG
with the actual contour path drawn on top of the image (correct aspect ratio),
plus the FULL list of (x, y) coordinates as chips. No counts-only summaries.

Usage: _contours_render.py <json_file> <image_url> <image_w_px> <image_h_px>
"""

import html, json, os, sys

if len(sys.argv) != 5:
    sys.exit(0)

json_file, img, w_arg, h_arg = sys.argv[1:5]
try:
    w_img = float(w_arg)
    h_img = float(h_arg)
except ValueError:
    sys.exit(0)

if not os.path.exists(json_file):
    sys.exit(0)

try:
    with open(json_file) as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)

paths = (data.get("results") or {}).get("contours", {}).get("paths") or []

if not paths:
    print('    <div class="empty-msg">No top-level contours returned.</div>')
    sys.exit(0)

# Distinct, scrollable colours per contour.
PALETTE = ["#0d9488", "#dc2626", "#3b82f6", "#f59e0b", "#a855f7",
           "#ec4899", "#22c55e", "#06b6d4", "#f97316", "#8b5cf6"]


def vis_to_px(x, y):
    return x * w_img, (1.0 - y) * h_img


for ii, p in enumerate(paths, start=1):
    pts = p.get("points") or []
    if not pts:
        print(f'    <div class="bbox-row"><span>path {ii} — '
              f'<em class="dim">empty path</em></span></div>')
        continue

    color = PALETTE[(ii - 1) % len(PALETTE)]

    xs = [pt["x"] for pt in pts]
    ys_top = [1.0 - pt["y"] for pt in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys_top), max(ys_top)
    pad = max(0.02, max(maxx - minx, maxy - miny) * 0.12)
    bx = max(0.0, minx - pad)
    by = max(0.0, miny - pad)
    bw = min(1.0 - bx, (maxx - minx) + 2 * pad)
    bh = min(1.0 - by, (maxy - miny) + 2 * pad)

    px_x = bx * w_img
    px_y = by * h_img
    px_w = max(1.0, bw * w_img)
    px_h = max(1.0, bh * h_img)

    svg = [
        f'<svg class="bbox-thumb contour-thumb" '
        f'viewBox="{px_x:.2f} {px_y:.2f} {px_w:.2f} {px_h:.2f}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'<image href="{html.escape(img)}" x="0" y="0" '
        f'width="{w_img:.0f}" height="{h_img:.0f}" preserveAspectRatio="none"/>'
    ]

    d_parts = []
    for k, pt in enumerate(pts):
        cx, cy = vis_to_px(pt["x"], pt["y"])
        d_parts.append(f'{"M" if k == 0 else "L"}{cx:.2f} {cy:.2f}')
    d = " ".join(d_parts) + " Z"
    stroke_w = max(0.6, min(px_w, px_h) * 0.005)
    svg.append(
        f'<path d="{d}" fill="rgba(255,255,255,0.0)" stroke="{color}" '
        f'stroke-width="{stroke_w:.2f}" stroke-linejoin="round"/>'
    )
    svg.append("</svg>")
    svg_html = "".join(svg)

    pc = p.get("pointCount", len(pts))
    print(
        f'    <div class="bbox-row contour-row">{svg_html}'
        f'<span>path {ii} — <strong>{pc}</strong> points — '
        f'<span class="lm-swatch" style="background:{color}"></span></span></div>'
    )

    # First 20 points always visible; the remainder folds into a <details>.
    HEAD = 20
    head_chips = " ".join(
        f'<span class="lm-pt">{k+1}: ({pt["x"]:.3f}, {pt["y"]:.3f})</span>'
        for k, pt in enumerate(pts[:HEAD])
    )
    tail_chips = " ".join(
        f'<span class="lm-pt">{k+1+HEAD}: ({pt["x"]:.3f}, {pt["y"]:.3f})</span>'
        for k, pt in enumerate(pts[HEAD:])
    )
    body = f'<span class="lm-coords">{head_chips}</span>'
    if tail_chips:
        remaining = len(pts) - HEAD
        body += (
            f'<details class="lm-more"><summary>show all {remaining} more '
            f'point{"s" if remaining != 1 else ""}</summary>'
            f'<span class="lm-coords">{tail_chips}</span></details>'
        )
    print(f'      <div class="lm-region">{body}</div>')
