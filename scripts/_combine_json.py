#!/usr/bin/env python3
"""Combine all auge capability JSON files for a single corpus item into one
big payload. NO truncation — every byte that auge produced is included so
readers can see the truthful, full output.

Usage: _combine_json.py <data_dir> <id>
"""
import json, os, sys, glob

data_dir = sys.argv[1]
id_ = sys.argv[2]

result = {}

# Main --all run goes under "all".
all_path = os.path.join(data_dir, f"{id_}.json")
if os.path.exists(all_path):
    try:
        with open(all_path) as fh:
            result["all"] = json.load(fh)
    except Exception as e:
        result["all"] = {"error": str(e)}

# Each enrichment capability gets its own top-level key, named after the
# capability (e.g. "aesthetics", "body-pose", "feature-print").
for path in sorted(glob.glob(os.path.join(data_dir, f"{id_}.*.json"))):
    base = os.path.basename(path)
    cap = base[len(id_) + 1:][:-5]  # between "$id." and ".json"
    if not cap:
        continue
    try:
        with open(path) as fh:
            result[cap] = json.load(fh)
    except Exception as e:
        result[cap] = {"error": str(e)}

print(json.dumps(result, indent=2, ensure_ascii=False))
