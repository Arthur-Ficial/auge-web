#!/usr/bin/env python3
"""Combine all auge capability JSON files for a single corpus item into one
big payload. Truncates the 768-d feature-print vector to 8 elements + length
hint so the rendered HTML stays small.

Usage: _combine_json.py <data_dir> <id>
"""
import json, os, sys, glob

data_dir = sys.argv[1]
id_ = sys.argv[2]


def trim(obj, key=None):
    """Recursively shrink large fields so the rendered HTML stays under ~50 KB/card.

    Truncated:
      - feature-print vector → first 8 + total-dim hint
      - contours.paths → first 3 paths with first 6 points each + count of dropped
      - face-landmarks regions point lists → counts only
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "vector" and isinstance(v, list) and len(v) > 16:
                out[k] = v[:8] + ["…", "(truncated; total {} dims)".format(len(v))]
            elif k == "landmarks" and isinstance(v, dict):
                # Each region is a list of {x,y} points — keep counts only.
                out[k] = {region: "{} points (truncated)".format(len(pts))
                          for region, pts in v.items()}
            elif k == "paths" and isinstance(v, list) and len(v) > 0 and "points" in (v[0] or {}):
                # Contour paths can each hold thousands of points.
                kept = []
                for p in v[:3]:
                    pts = p.get("points") or []
                    kept.append({
                        "pointCount": p.get("pointCount", len(pts)),
                        "points": (pts[:6] + ["… (truncated)"]) if len(pts) > 6 else pts,
                    })
                if len(v) > 3:
                    kept.append("… {} more paths (truncated)".format(len(v) - 3))
                out[k] = kept
            else:
                out[k] = trim(v, k)
        return out
    if isinstance(obj, list):
        return [trim(x, key) for x in obj]
    return obj


result = {}
all_path = os.path.join(data_dir, f"{id_}.json")
if os.path.exists(all_path):
    try:
        with open(all_path) as fh:
            result["all"] = trim(json.load(fh))
    except Exception as e:
        result["all"] = {"error": str(e)}

for path in sorted(glob.glob(os.path.join(data_dir, f"{id_}.*.json"))):
    base = os.path.basename(path)
    cap = base[len(id_) + 1:][:-5]  # between "$id." and ".json"
    if not cap:
        continue
    try:
        with open(path) as fh:
            result[cap] = trim(json.load(fh))
    except Exception as e:
        result[cap] = {"error": str(e)}

print(json.dumps(result, indent=2, ensure_ascii=False))
