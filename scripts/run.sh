#!/usr/bin/env bash
# Run auge over every corpus item using the args in the manifest.
# Output: data/<id>.json (the auge JSON output) + data/<id>.txt (plain text).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/corpus/manifest.json"
SOURCE="$ROOT/corpus/files"
DEST="$ROOT/data"

mkdir -p "$DEST"

if ! command -v auge >/dev/null 2>&1; then
    echo "auge-web: auge binary not found in PATH. Build & install auge first."
    exit 1
fi

AUGE="$(command -v auge)"
VERSION=$($AUGE --version | awk '{print $2}' | sed 's/^v//')
echo "auge-web: running auge $VERSION over corpus..."

count=$(jq '.items | length' "$MANIFEST")

for i in $(seq 0 $((count - 1))); do
    id=$(jq -r ".items[$i].id" "$MANIFEST")
    filename=$(jq -r ".items[$i].filename" "$MANIFEST")
    file="$SOURCE/$filename"

    if [ ! -f "$file" ]; then
        echo "  $id  SKIP (file not fetched)"
        continue
    fi

    args_json=$(jq -c ".items[$i].auge_args" "$MANIFEST")
    # Convert JSON array to bash args
    mapfile -t args < <(echo "$args_json" | jq -r '.[]')

    json_out="$DEST/$id.json"
    txt_out="$DEST/$id.txt"
    err_out="$DEST/$id.err"

    printf "  %-40s " "$id"

    if "$AUGE" "${args[@]}" -o json "$file" > "$json_out" 2> "$err_out"; then
        "$AUGE" "${args[@]}" "$file" > "$txt_out" 2>> "$err_out" || true
        # Compact NDJSON variant for the showcase footer
        "$AUGE" "${args[@]}" --ndjson "$file" > "$DEST/$id.ndjson" 2>> "$err_out" || true

        # v1.3 enrichment passes — every item gets these extra analyses.
        # Empty / null results are fine; templates render conditionally.
        for cap in aesthetics smudge saliency-attention saliency-objectness rectangles horizon face-landmarks animals body-pose hand-pose animal-pose contours text-rectangles feature-print subject persons-mask; do
            "$AUGE" "--$cap" -o json "$file" > "$DEST/$id.$cap.json" 2>> "$err_out" || true
        done
        echo "OK + v1.3"
    else
        echo "ERROR — see $err_out"
    fi
done

echo ""
echo "auge-web: results written to $DEST/"
