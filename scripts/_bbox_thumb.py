#!/usr/bin/env python3
"""Emit a small inline SVG that shows just the bbox region of an image.

Usage: _bbox_thumb.py <image_url> <x> <y> <w> <h>

Coordinates are normalized [0..1], Vision-style (bottom-origin). The SVG uses
a viewBox cropped to the bbox so the embedded <image> is naturally clipped
to that rectangle.
"""

import sys

if len(sys.argv) != 6:
    sys.exit(2)

img, x, y, w, h = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])

# Convert Vision (bottom-origin) → SVG/HTML (top-origin):
# the rectangle's top in image space is (1 - y - h).
top_y = max(0.0, 1.0 - y - h)
vx, vy, vw, vh = max(0.0, x), top_y, max(1e-6, w), max(1e-6, h)

# Clamp to [0, 1]
vw = min(vw, 1.0 - vx)
vh = min(vh, 1.0 - vy)

print(
    '<svg class="bbox-thumb" viewBox="{:.4f} {:.4f} {:.4f} {:.4f}" '
    'preserveAspectRatio="xMidYMid slice">'
    '<image href="{}" x="0" y="0" width="1" height="1" preserveAspectRatio="none"/>'
    '</svg>'.format(vx, vy, vw, vh, img)
)
