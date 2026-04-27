#!/usr/bin/env bash
# auto.sh — one-shot pipeline that:
#   1. Rebuilds & installs the local auge binary (no version bump unless asked)
#   2. Runs auge across every corpus item (--all + every per-cap enrichment)
#   3. Re-renders the static site from manifest + per-cap JSONs
#   4. Mirrors data/*.json into site/data/ for the per-card download links
#   5. Deploys to Cloudflare Pages (auge-web project)
#
# Usage: ./scripts/auto.sh [--skip-build] [--skip-run] [--skip-deploy]
#
# Use --skip-build to skip rebuilding auge (assumes it's already current).
# Use --skip-run when only template/CSS/Python renderers changed.
# Use --skip-deploy to render locally without pushing to Cloudflare.
set -euo pipefail

WEB_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUGE_ROOT="$(cd "$WEB_ROOT/../auge" && pwd)"

SKIP_BUILD=0
SKIP_RUN=0
SKIP_DEPLOY=0
for a in "$@"; do
    case "$a" in
        --skip-build)  SKIP_BUILD=1 ;;
        --skip-run)    SKIP_RUN=1 ;;
        --skip-deploy) SKIP_DEPLOY=1 ;;
        -h|--help)
            sed -n '2,18p' "$0"
            exit 0
            ;;
        *)
            echo "auto: unknown arg: $a" >&2
            exit 2
            ;;
    esac
done

echo "auto: WEB_ROOT=$WEB_ROOT"
echo "auto: AUGE_ROOT=$AUGE_ROOT"

# ---- 1. Rebuild auge -------------------------------------------------------
if [ "$SKIP_BUILD" = "0" ]; then
    if [ ! -d "$AUGE_ROOT" ]; then
        echo "auto: error — $AUGE_ROOT not found." >&2
        exit 1
    fi
    echo ""
    echo "==> [1/5] building & installing auge from $AUGE_ROOT"
    (cd "$AUGE_ROOT" && swift build -c release 2>&1 | tail -3)
    SUDO_PW="$(pass show system/sudo-password 2>/dev/null || true)"
    if [ -n "$SUDO_PW" ]; then
        echo "$SUDO_PW" | sudo -S cp "$AUGE_ROOT/.build/release/auge" /usr/local/bin/auge
        echo "$SUDO_PW" | sudo -S cp "$AUGE_ROOT/.build/release/auge" /opt/homebrew/bin/auge
    else
        cp "$AUGE_ROOT/.build/release/auge" /usr/local/bin/auge
        cp "$AUGE_ROOT/.build/release/auge" /opt/homebrew/bin/auge
    fi
    auge --version
else
    echo ""
    echo "==> [1/5] skipping auge rebuild (--skip-build); using $(auge --version)"
fi

# ---- 2. Run auge over the corpus ------------------------------------------
if [ "$SKIP_RUN" = "0" ]; then
    echo ""
    echo "==> [2/5] running auge over the corpus (this takes a while)…"
    bash "$WEB_ROOT/scripts/run.sh"
else
    echo ""
    echo "==> [2/5] skipping corpus run (--skip-run)"
fi

# ---- 3. Mirror raw JSON into site/data ------------------------------------
echo ""
echo "==> [3/5] mirroring data/*.json → site/data/ for per-card download links"
mkdir -p "$WEB_ROOT/site/data"
# Remove anything stale, then copy current.
rm -f "$WEB_ROOT/site/data"/*.json 2>/dev/null || true
cp -p "$WEB_ROOT/data"/*.json "$WEB_ROOT/site/data/" 2>/dev/null || true
echo "auto: $(ls "$WEB_ROOT/site/data" | wc -l | tr -d ' ') JSON files in site/data"

# ---- 4. Build the static site ---------------------------------------------
echo ""
echo "==> [4/5] rendering site/index.html"
bash "$WEB_ROOT/scripts/build.sh"
INDEX_SIZE=$(stat -f%z "$WEB_ROOT/site/index.html" 2>/dev/null || stat -c%s "$WEB_ROOT/site/index.html")
INDEX_KB=$((INDEX_SIZE / 1024))
echo "auto: site/index.html → ${INDEX_KB} KB"

# ---- 5. Deploy to Cloudflare Pages ----------------------------------------
if [ "$SKIP_DEPLOY" = "0" ]; then
    echo ""
    echo "==> [5/5] deploying to Cloudflare Pages (auge-web)"
    if ! command -v wrangler >/dev/null 2>&1; then
        echo "auto: wrangler not found — install with: npm i -g wrangler" >&2
        exit 1
    fi
    (cd "$WEB_ROOT" && wrangler pages deploy site --project-name=auge-web --commit-dirty=true 2>&1 | tail -6)
else
    echo ""
    echo "==> [5/5] skipping deploy (--skip-deploy)"
fi

echo ""
echo "auto: done."
