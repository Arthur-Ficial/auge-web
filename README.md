# auge-web

Real-world showcase of [`auge`](https://github.com/Arthur-Ficial/auge) — Apple Vision from the command line — running on a curated corpus of public-domain documents.

**Live:** [auge.franzai.com](https://auge.franzai.com)

## What this is

Two things in one repo:

1. **A landing page** for `auge` with hero, install instructions, and links to the source.
2. **A test corpus + report.** Every document on the site is licensed CC0 or in the public domain. The OCR / classify / barcode / faces results shown next to each one are produced by running real `auge` over that document at build time. No mocks, no cherry-picked examples — what you see is what auge does.

## Build

```bash
# 1. Fetch the corpus from Wikimedia (idempotent, only downloads missing)
make fetch

# 2. Run auge over every corpus item, write JSON to data/
make run

# 3. Generate the static site
make build

# 4. Local preview
make preview
```

## Deploy

Hosted on Cloudflare Pages. Domain: `auge.franzai.com`.

```bash
make deploy
```

## License

Site code: MIT.
Corpus content: CC0 / Public Domain only — see [`corpus/manifest.json`](./corpus/manifest.json) for per-file attribution.
