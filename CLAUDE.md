# auge-web - Project Instructions

## The Golden Goal

auge-web is the landing and showcase site for the `auge` on-device vision CLI (Apple Vision from your terminal), live at auge.franzai.com. Its one ultimate purpose is to make a newcomer instantly understand what auge does and trust it, by pairing a mobile-first landing page (hero, install instructions, links to the source) with a self-generated test corpus where every OCR, classify, barcode, and faces result is produced by running real auge over real CC0 / public-domain documents at build time - no mocks, no cherry-picking. What you see on the site is exactly what auge produces. This repo IS that website plus its build pipeline (fetch corpus, run auge, generate static site, deploy to Cloudflare Pages). It is NOT the auge tool itself - the vision CLI lives in the separate Arthur-Ficial/auge repo, and this site only demonstrates and links to it.
