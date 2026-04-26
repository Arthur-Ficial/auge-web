#!/usr/bin/env bash
# Fetch corpus images from Wikimedia Commons.
# Resolves URLs via the Commons API (using the wiki_file title) so the manifest
# stays robust across thumbnail server changes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/corpus/manifest.json"
DEST="$ROOT/corpus/files"
USER_AGENT="auge-web/1.0 (https://github.com/Arthur-Ficial/auge-web; arti.ficial@fullstackoptimization.com)"
WIDTH=1200

mkdir -p "$DEST"

count=$(jq '.items | length' "$MANIFEST")
echo "auge-web: fetching $count corpus items via Wikimedia API..."

for i in $(seq 0 $((count - 1))); do
    id=$(jq -r ".items[$i].id" "$MANIFEST")
    wiki_file=$(jq -r ".items[$i].wiki_file" "$MANIFEST")
    filename=$(jq -r ".items[$i].filename" "$MANIFEST")
    is_local=$(jq -r ".items[$i].local // false" "$MANIFEST")
    target="$DEST/$filename"

    # Locally generated items (e.g. QR codes via qrencode) are pre-placed
    # under corpus/files/ — skip remote resolution.
    if [ "$is_local" = "true" ]; then
        if [ -f "$target" ] && [ -s "$target" ]; then
            printf "  %-40s [local]\n" "$id"
        else
            printf "  %-40s [LOCAL MISSING %s]\n" "$id" "$target"
        fi
        continue
    fi

    if [ -f "$target" ] && [ -s "$target" ]; then
        printf "  %-40s [cached]\n" "$id"
        continue
    fi

    # URL-encode the file title (handles spaces, umlauts, accents, parentheses)
    encoded=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1].replace(' ','_'), safe=''))" "$wiki_file")
    api="https://commons.wikimedia.org/w/api.php?action=query&titles=File:${encoded}&prop=imageinfo&iiprop=url&iiurlwidth=${WIDTH}&format=json"
    resolved=$(curl -fsSL --max-time 30 -A "$USER_AGENT" "$api" 2>/dev/null \
        | jq -r '.query.pages | to_entries[0].value.imageinfo[0] | (.thumburl // .url) // empty' 2>/dev/null || true)

    if [ -z "$resolved" ] || [ "$resolved" = "null" ]; then
        printf "  %-40s [API resolve FAILED]\n" "$id"
        continue
    fi

    printf "  %-40s [fetching...] " "$id"
    if ! curl -fsSL --max-time 60 -A "$USER_AGENT" -o "$target.tmp" "$resolved"; then
        echo "DOWNLOAD FAILED"
        mv "$target.tmp" "$target.tmp.failed-$(date +%s)" 2>/dev/null || true
        continue
    fi
    mv "$target.tmp" "$target"

    # Flatten alpha for PNGs — Vision's barcode/QR decoder dislikes alpha-only grayscale.
    if [[ "$target" == *.png ]] || [[ "$target" == *.PNG ]]; then
        if command -v magick >/dev/null 2>&1; then
            magick "$target" -background white -alpha remove -alpha off -colorspace sRGB "$target.flat" 2>/dev/null \
              && mv "$target.flat" "$target"
        elif command -v convert >/dev/null 2>&1; then
            convert "$target" -background white -alpha remove -alpha off -colorspace sRGB "$target.flat" 2>/dev/null \
              && mv "$target.flat" "$target"
        fi
    fi

    size=$(stat -f%z "$target" 2>/dev/null || stat -c%s "$target")
    echo "$((size/1024)) KB"
done

echo ""
echo "auge-web: corpus in $DEST"
ls -lh "$DEST" | tail -n +2
