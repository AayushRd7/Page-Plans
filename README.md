# Page Plans

Tool that turns a collection URL into a complete SEO page plan: audit,
entities, keywords, SERP and review analysis, section-level outline, and
paste-ready rewritten copy with word-level change diffs. Output: DOCX + PDF
+ paste-ready TXT, in the client-approved template format.

## Architecture principles

1. **One document model.** Every pipeline stage writes blocks (see
   `app/docmodel/blocks.py`). Renderers consume blocks. Adding an output
   format never touches pipeline code.
2. **One pipeline, tiers as gate configs.** A run is a state machine; a
   tier is just which stages may pause for human input. Never three flows.
   See `app/pipeline/stages.py`.
3. **Store adapters.** Shopify API, WooCommerce API, and a universal crawl
   fallback all normalize into the same catalog schema. The pipeline never
   knows the platform.
4. **Paid calls are gated and cached.** Preflight validates the URL before
   any paid API fires. Volumes cache 30 days. Stage artifacts on disk, so
   re-running one stage never re-bills another.

## Status

Done (this commit):
- [x] Block schema + frozen section template (`app/docmodel/`)
- [x] Word-level diff engine (`app/diffing.py`)
- [x] PDF renderer: blocks -> HTML -> headless Chromium (`app/render/`)
- [x] DOCX renderer: native strikethrough + highlight (`app/render/`)
- [x] Paste-ready TXT extraction
- [x] Pipeline skeleton: stages, outcomes, tier gate configs (`app/pipeline/`)
- [x] Reference sample: thca flower plan encoded full-fidelity (`samples/thca_flower.py`
      + `samples/data/`). Every section, all table rows, and every draft section's
      CHANGES view: old text reconstructed from the sample PDF's own strikeout /
      highlight geometry, new text from the client paste-ready txt, counts matching
      the sample's own ADDED/REMOVED labels.

Next:
- [ ] Store adapters (Shopify / WooCommerce / crawl)
- [ ] DataForSEO client (SERP, Keywords, Labs, Content Analysis, On-Page)
- [ ] GSC OAuth connect flow
- [ ] Ahrefs free DR client (+ attribution line, already in template)
- [ ] LLM stage prompts (OpenRouter), humanizer pass on drafts
- [ ] FastAPI app + worker + Postgres + queue
- [ ] Tier 2 approval screens (keywords, outline, claims)
- [ ] Tier 3 stage editor + override-to-rule promotion

## Run

```bash
pip install -r requirements.txt
playwright install chromium   # if not already present
python -m app.cli sample      # renders out/thca_sample.pdf/.docx + paste-ready txt
```

## Environment

Copy `.env.example` to `.env` and fill in. Never commit `.env`.
Rotate any credential that has ever been pasted in chat.

## Deploy

Backend: Docker on a Linux box (FastAPI + worker + Postgres + Redis),
fronted by Cloudflare (Tunnel/proxy). Frontend: static build, Cloudflare
Pages. Repo ships no deploy config yet; it lands with the app skeleton.
