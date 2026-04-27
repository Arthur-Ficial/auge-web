#!/usr/bin/env python3
"""Emit an aspect-ratio-correct inline SVG that shows just the bbox region of
an image.

Usage: _bbox_thumb.py <image_url> <image_w_px> <image_h_px> <x> <y> <w> <h>

Coordinates x/y/w/h are normalized [0..1], Vision-style (bottom-origin).
The SVG's viewBox is in PIXEL units of the source image — so the SVG's
intrinsic aspect ratio equals the bbox's real aspect ratio. CSS can size
it freely with max-width / max-height; the browser preserves the ratio.
"""

import sys

if len(sys.argv) != 8:
    sys.exit(2)

img = sys.argv[1]
try:
    w_img = float(sys.argv[2])
    h_img = float(sys.argv[3])
    x = float(sys.argv[4])
    y = float(sys.argv[5])
    w = float(sys.argv[6])
    h = float(sys.argv[7])
except ValueError:
    sys.exit(2)

if w_img <= 0 or h_img <= 0:
    sys.exit(0)

# Vision (bottom-origin) → SVG (top-origin).
top_y = max(0.0, 1.0 - y - h)
# Clamp to [0, 1].
nx = max(0.0, min(1.0, x))
ny = max(0.0, min(1.0, top_y))
nw = max(1e-6, min(1.0 - nx, w))
nh = max(1e-6, min(1.0 - ny, h))

# Convert to pixel coords; viewBox in pixels gives the SVG the bbox's real
# aspect ratio as its intrinsic dimension.
px_x = nx * w_img
px_y = ny * h_img
px_w = max(1.0, nw * w_img)
px_h = max(1.0, nh * h_img)

# The embedded <image> spans the full source-image extent. The viewBox crops.
print(
    '<svg class="bbox-thumb" viewBox="{:.2f} {:.2f} {:.2f} {:.2f}" '
    'preserveAspectRatio="xMidYMid meet">'
    '<image href="{}" x="0" y="0" width="{}" height="{}" preserveAspectRatio="none"/>'
    '</svg>'.format(px_x, px_y, px_w, px_h, img, w_img, h_img)
)
