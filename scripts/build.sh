#!/usr/bin/env bash
# Generate site/index.html from corpus/manifest.json + data/<id>.json (auge --all).
# Renders each card with rich per-section visualization (OCR text, classify bars,
# face bounding-box overlay, barcode payloads), plus the full JSON inline.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/corpus/manifest.json"
DATA="$ROOT/data"
SOURCE="$ROOT/corpus/files"
SITE="$ROOT/site"
IMAGES="$SITE/images"

mkdir -p "$IMAGES"

VERSION=$(auge --version 2>/dev/null | awk '{print $2}' | sed 's/^v//' || echo "—")
GENERATED=$(date "+%Y-%m-%d")

echo "auge-web: building site/index.html (auge v$VERSION)..."

html_escape() { python3 -c 'import sys, html; print(html.escape(sys.stdin.read()), end="")'; }

# Pretty-print a JSON file, returning empty string if missing.
pretty_json_file() {
  if [ -f "$1" ] && [ -s "$1" ]; then
    cat "$1" | python3 -c 'import sys,json; sys.stdout.write(json.dumps(json.load(sys.stdin), indent=2, ensure_ascii=False))'
  fi
}

# Render the auge command line as syntax-colored HTML.
render_cmdline() {
  local args_json="$1"
  local filename="$2"
  local out='<span class="prompt">$</span> <span>auge</span>'
  while IFS= read -r arg; do
    if [[ "$arg" == --* ]]; then
      out+=" <span class=\"flag\">$(echo "$arg" | html_escape)</span>"
    else
      out+=" <span class=\"arg\">$(echo "$arg" | html_escape)</span>"
    fi
  done < <(echo "$args_json" | jq -r '.[]')
  out+=" <span>$(echo "$filename" | html_escape)</span>"
  echo "$out"
}

# ---- Render an OCR section from the JSON object ----
render_ocr_section() {
  local json_file="$1"
  local lines_json
  lines_json=$(jq -c '.results.ocr.lines // .results.lines // []' "$json_file" 2>/dev/null || echo '[]')
  local count
  count=$(echo "$lines_json" | jq 'length')
  local text
  text=$(echo "$lines_json" | jq -r 'join("\n")')
  local chars
  chars=$(printf '%s' "$text" | wc -c | tr -d ' ')

  if [ "$count" -eq 0 ] || [ -z "$text" ]; then
    cat <<EOF
<div class="section empty">
  <div class="section-head">
    <span class="icon ocr">A</span>
    <span class="label">OCR</span>
    <span class="stats">no text</span>
  </div>
  <div class="empty-msg">No text detected in this image.</div>
</div>
EOF
    return
  fi

  cat <<EOF
<div class="section">
  <div class="section-head">
    <span class="icon ocr">A</span>
    <span class="label">OCR</span>
    <span class="stats">${count} line$([ "$count" -ne 1 ] && echo s || true) · ${chars} chars</span>
  </div>
  <pre class="ocr-text">$(printf '%s' "$text" | html_escape)</pre>
</div>
EOF
}

# ---- Render a CLASSIFY section ----
render_classify_section() {
  local json_file="$1"
  local items_json
  items_json=$(jq -c '.results.classify.classifications // .results.classifications // []' "$json_file" 2>/dev/null || echo '[]')
  local count
  count=$(echo "$items_json" | jq 'length')

  if [ "$count" -eq 0 ]; then
    cat <<EOF
<div class="section empty">
  <div class="section-head">
    <span class="icon classify">#</span>
    <span class="label">Classify</span>
    <span class="stats">no labels</span>
  </div>
  <div class="empty-msg">No classification labels above the confidence threshold.</div>
</div>
EOF
    return
  fi

  cat <<EOF
<div class="section">
  <div class="section-head">
    <span class="icon classify">#</span>
    <span class="label">Classify</span>
    <span class="stats">${count} label$([ "$count" -ne 1 ] && echo s || true)</span>
  </div>
  <div class="classify-list">
EOF

  echo "$items_json" | jq -c '.[]' | while IFS= read -r row; do
    local label conf pct
    label=$(echo "$row" | jq -r '.label')
    conf=$(echo "$row" | jq -r '.confidence')
    pct=$(awk "BEGIN { printf \"%.0f\", $conf * 100 }")
    label_e=$(echo "$label" | html_escape)
    cat <<EOF
    <div class="classify-row">
      <div class="classify-bar"><div class="fill" style="width:${pct}%"></div><div class="text">${label_e}</div></div>
      <div class="classify-pct">${pct}%</div>
    </div>
EOF
  done

  cat <<EOF
  </div>
</div>
EOF
}

# ---- Render a BARCODES section ----
render_barcodes_section() {
  local json_file="$1"
  local items_json
  items_json=$(jq -c '.results.barcodes.barcodes // .results.barcodes // []' "$json_file" 2>/dev/null || echo '[]')
  local count
  count=$(echo "$items_json" | jq 'length')

  if [ "$count" -eq 0 ]; then
    cat <<EOF
<div class="section empty">
  <div class="section-head">
    <span class="icon barcodes">▦</span>
    <span class="label">Barcodes</span>
    <span class="stats">none</span>
  </div>
  <div class="empty-msg">No barcodes or QR codes detected.</div>
</div>
EOF
    return
  fi

  cat <<EOF
<div class="section">
  <div class="section-head">
    <span class="icon barcodes">▦</span>
    <span class="label">Barcodes</span>
    <span class="stats">${count} found</span>
  </div>
  <div class="barcode-list">
EOF

  echo "$items_json" | jq -c '.[]' | while IFS= read -r row; do
    local sym payload
    sym=$(echo "$row" | jq -r '.symbology // "?"')
    payload=$(echo "$row" | jq -r '.payload // ""')
    sym_e=$(echo "$sym" | html_escape)

    if [[ "$payload" =~ ^https?:// ]]; then
      payload_html="<a href=\"$(echo "$payload" | html_escape)\" target=\"_blank\" rel=\"noopener\">$(echo "$payload" | html_escape)</a>"
    else
      payload_html=$(echo "$payload" | html_escape)
    fi

    cat <<EOF
    <div class="barcode-row">
      <span class="symbology">${sym_e}</span>
      <span class="payload">${payload_html}</span>
    </div>
EOF
  done

  cat <<EOF
  </div>
</div>
EOF
}

# ---- Render a FACES section, with bounding-box overlay HTML ----
render_faces_section() {
  local json_file="$1"
  local items_json
  items_json=$(jq -c '.results.faces.faces // .results.faces // []' "$json_file" 2>/dev/null || echo '[]')
  local count
  count=$(echo "$items_json" | jq 'length')

  cat <<EOF
<div class="section$([ "$count" -eq 0 ] && echo " empty" || true)">
  <div class="section-head">
    <span class="icon faces">☻</span>
    <span class="label">Faces</span>
    <span class="stats">${count} detected</span>
  </div>
EOF

  if [ "$count" -eq 0 ]; then
    cat <<EOF
  <div class="empty-msg">No faces detected.</div>
</div>
EOF
    return
  fi

  cat <<EOF
  <div class="faces-summary">
    <span class="count">${count}</span> face$([ "$count" -ne 1 ] && echo s || true) located. Bounding boxes overlaid on the image above.
  </div>
  <div class="faces-list">
EOF

  echo "$items_json" | jq -c '.[]' | awk '{print NR, $0}' | while IFS= read -r line; do
    local idx row
    idx=$(echo "$line" | awk '{print $1}')
    row=$(echo "$line" | cut -d' ' -f2-)
    local x y w h
    x=$(echo "$row" | jq -r '.x')
    y=$(echo "$row" | jq -r '.y')
    w=$(echo "$row" | jq -r '.width')
    h=$(echo "$row" | jq -r '.height')
    printf '    <div>face %s: x=%.3f y=%.3f w=%.3f h=%.3f</div>\n' "$idx" "$x" "$y" "$w" "$h"
  done

  cat <<EOF
  </div>
</div>
EOF
}

# ---- Render face bounding-box overlay (SVG-like positioning over image) ----
render_face_overlay() {
  local json_file="$1"
  local items_json
  items_json=$(jq -c '.results.faces.faces // .results.faces // []' "$json_file" 2>/dev/null || echo '[]')
  local count
  count=$(echo "$items_json" | jq 'length')

  if [ "$count" -eq 0 ]; then return; fi

  echo '<div class="face-overlay">'
  local i=0
  echo "$items_json" | jq -c '.[]' | while IFS= read -r row; do
    i=$((i+1))
    local x y w h
    x=$(echo "$row" | jq -r '.x')
    y=$(echo "$row" | jq -r '.y')
    w=$(echo "$row" | jq -r '.width')
    h=$(echo "$row" | jq -r '.height')
    # Vision's boundingBox: lower-left origin. CSS uses top-left. Flip Y.
    local left top width height
    left=$(awk "BEGIN { printf \"%.2f\", $x * 100 }")
    top=$(awk "BEGIN { printf \"%.2f\", (1 - $y - $h) * 100 }")
    width=$(awk "BEGIN { printf \"%.2f\", $w * 100 }")
    height=$(awk "BEGIN { printf \"%.2f\", $h * 100 }")
    printf '<div class="face-box" style="left:%s%%;top:%s%%;width:%s%%;height:%s%%"><div class="label">face %d</div></div>\n' \
      "$left" "$top" "$width" "$height" "$i"
  done
  echo '</div>'
}

# ---- Per-item card builder ----
build_card() {
  local idx="$1"

  local id title year category license source_url filename blurb args_json
  id=$(jq -r ".items[$idx].id" "$MANIFEST")
  title=$(jq -r ".items[$idx].title" "$MANIFEST")
  year=$(jq -r ".items[$idx].year" "$MANIFEST")
  category=$(jq -r ".items[$idx].category" "$MANIFEST")
  license=$(jq -r ".items[$idx].license" "$MANIFEST")
  source_url=$(jq -r ".items[$idx].source" "$MANIFEST")
  filename=$(jq -r ".items[$idx].filename" "$MANIFEST")
  blurb=$(jq -r ".items[$idx].blurb" "$MANIFEST")
  args_json=$(jq -c ".items[$idx].auge_args" "$MANIFEST")

  local src_image="$SOURCE/$filename"
  if [ ! -f "$src_image" ]; then return; fi

  # PDFs: render first page as PNG for the card image.
  local display_filename="$filename"
  if [[ "$filename" == *.pdf ]] || [[ "$filename" == *.PDF ]]; then
    local png_thumb="${filename%.*}.png"
    local png_path="$IMAGES/$png_thumb"
    if [ ! -f "$png_path" ]; then
      sips -s format png "$src_image" --out "$png_path" >/dev/null 2>&1 || cp "$src_image" "$png_path"
      sips -Z 900 "$png_path" --out "$png_path" >/dev/null 2>&1 || true
    fi
    display_filename="$png_thumb"
  else
    sips -Z 900 "$src_image" --out "$IMAGES/$filename" >/dev/null 2>&1 || cp "$src_image" "$IMAGES/$filename"
  fi

  local json_file="$DATA/$id.json"
  local cmdline
  cmdline=$(render_cmdline "$args_json" "$filename")
  local pretty
  pretty=$(pretty_json_file "$json_file" | html_escape)

  local title_e blurb_e license_e source_e
  title_e=$(echo "$title" | html_escape)
  blurb_e=$(echo "$blurb" | html_escape)
  license_e=$(echo "$license" | html_escape)
  source_e=$(echo "$source_url" | html_escape)

  cat <<EOF
<article class="card" id="$id">
  <div class="card-image">
    <img src="images/$(echo "$display_filename" | html_escape)" alt="$title_e" loading="lazy">
$(render_face_overlay "$json_file")
  </div>
  <div class="card-body">
    <div class="card-meta">
      <span class="badge $category">$category</span>
      <span>$year</span>
      <span>$license_e</span>
    </div>
    <h3>$title_e</h3>
    <p class="blurb">$blurb_e</p>
    <code class="cmd-line">$cmdline</code>
$(render_ocr_section "$json_file")
$(render_classify_section "$json_file")
$(render_barcodes_section "$json_file")
$(render_faces_section "$json_file")
    <div class="section">
      <div class="section-head">
        <span class="icon ocr">{}</span>
        <span class="label">Raw JSON</span>
        <span class="stats">on-device output</span>
      </div>
      <pre class="json-block">$pretty</pre>
    </div>
    <a class="source-link" href="$source_e" target="_blank" rel="noopener">Wikimedia source</a>
  </div>
</article>
EOF
}

# ---- Compose index.html ----
count=$(jq '.items | length' "$MANIFEST")

cat > "$SITE/index.html" <<HEAD
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>auge — Apple Vision from your terminal</title>
  <meta name="description" content="auge is a UNIX CLI for Apple's on-device Vision framework. Point it at any image — OCR, classification, barcodes, faces — and get everything back. 100% on-device. This site shows it running on real public-domain documents from Wikimedia.">
  <link rel="stylesheet" href="css/style.css">
</head>
<body>

<header class="hero">
  <div class="wrap">
    <div class="brand">
      <h1>auge</h1>
      <span class="version">v${VERSION}</span>
    </div>
    <p class="tagline">Apple Vision from your terminal.</p>
    <p class="subtagline">Point auge at any image. Get everything back — text, labels, barcodes, faces — in one command, all on-device. No API keys. No cloud. No network. Zero dependencies.</p>
    <div class="pills">
      <span class="pill">100% on-device</span>
      <span class="pill">No API keys</span>
      <span class="pill">Zero dependencies</span>
      <span class="pill">Pipe-friendly</span>
      <span class="pill">macOS 10.15+</span>
    </div>
    <pre class="hero-demo"><span class="prompt">\$</span> <span class="cmd">auge --all</span> photo.jpg
<span class="out">=== OCR ===
(no text)

=== CLASSIFY ===
animal: 92%
cat: 92%
feline: 92%

=== BARCODES ===
(none)

=== FACES ===
0 faces detected</span>

<span class="prompt">\$</span> <span class="cmd">auge --all</span> scan.pdf <span class="comment"># pdf input via PDFKit</span>
<span class="prompt">\$</span> <span class="cmd">auge --all</span> qr.png <span class="comment"># OCR + classify + barcode + faces, one pass</span>
<span class="prompt">\$</span> <span class="cmd">auge --all --md</span> doc.png | apfel <span class="cmd">"summarize"</span></pre>
  </div>
</header>

<section class="install">
  <div class="wrap">
    <h2>Install</h2>
    <div class="install-row">
      <div class="install-card">
        <div class="label">Homebrew (recommended)</div>
        <pre>brew tap Arthur-Ficial/tap
brew install Arthur-Ficial/tap/auge</pre>
        <button class="copy-btn">copy</button>
      </div>
      <div class="install-card">
        <div class="label">Build from source</div>
        <pre>git clone https://github.com/Arthur-Ficial/auge
cd auge && make install</pre>
        <button class="copy-btn">copy</button>
      </div>
      <div class="install-card">
        <div class="label">Repo &amp; docs</div>
        <pre><a href="https://github.com/Arthur-Ficial/auge">github.com/Arthur-Ficial/auge</a></pre>
      </div>
    </div>
  </div>
</section>

<section class="showcase-intro">
  <div class="wrap">
    <h2>Real documents, every analysis, real auge.</h2>
    <p>Every example below is processed by running the real <code>auge</code> binary (v${VERSION}) on a public-domain document from Wikimedia Commons — at build time, on a Mac, with no network and no cloud. Each card shows what auge produced: structured OCR text, classification labels with confidence, barcode payloads, face bounding boxes, and the full JSON output, on-device.</p>
  </div>
</section>

<main class="wrap">
  <div class="cards">
HEAD

for i in $(seq 0 $((count - 1))); do
    id=$(jq -r ".items[$i].id" "$MANIFEST")
    printf "  %-40s built\n" "$id"
    build_card "$i" >> "$SITE/index.html"
done

cat >> "$SITE/index.html" <<TAIL
  </div>
</main>

<footer>
  <div class="wrap">
    <p>auge v${VERSION} · generated ${GENERATED} · <a href="https://github.com/Arthur-Ficial/auge">source on GitHub</a> · <a href="https://github.com/Arthur-Ficial/auge-web">site source</a></p>
    <p>All corpus content is CC0 or public domain. Per-file attribution links are above. auge-web site code: MIT.</p>
  </div>
</footer>

<script src="js/main.js" defer></script>
</body>
</html>
TAIL

echo ""
echo "auge-web: site built at $SITE/index.html"
ls -lh "$SITE/index.html"
