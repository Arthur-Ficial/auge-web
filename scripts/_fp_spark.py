#!/usr/bin/env python3
"""Render a feature-print vector slice as a tiny SVG bar sparkline.

Reads a JSON array from stdin, prints an inline <svg>. Used by build.sh.
"""
import json, sys

raw = sys.stdin.read().strip()
if not raw:
    sys.exit(0)
try:
    arr = json.loads(raw)
except Exception:
    sys.exit(0)
if not arr:
    sys.exit(0)

mn, mx = min(arr), max(arr)
rng = (mx - mn) or 1
width = 320
height = 36
n = len(arr)
bars = []
bar_w = max(0.0, width / n - 0.5)
for i, v in enumerate(arr):
    h = (v - mn) / rng * (height - 2)
    x = i * (width / n)
    y = height - h - 1
    bars.append(
        '<rect x="{:.2f}" y="{:.2f}" width="{:.2f}" height="{:.2f}"/>'.format(
            x, y, bar_w, h
        )
    )
print(
    '<svg class="fp-spark" viewBox="0 0 {} {}" preserveAspectRatio="none">{}</svg>'.format(
        width, height, "".join(bars)
    )
)
