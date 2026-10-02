"""Headless pipeline runner: URL -> DOCX + PDF + paste-ready TXT.

One runner, three tiers. In headless mode gate stages auto-approve and
log the decision; the FastAPI layer later replaces auto-approval with
human answers over the same stage states.
"""
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.adapters.base import collection_handle_from_url, detect_platform, get_adapter
from app.audit.checks import check_draft, dimension_scores, overall_score, run_checks
from app.audit.snapshot import PageSnapshot, snapshot_from_html
from app.clients import ahrefs
from app.diffing import word_diff
from app.docmodel.blocks import (Bullets, DiffPara, H2, H3, KVTable, Label, Note,
                                 Numbered, PageBreak, Paragraph, PlanDocument, Run, Table)
from app.docmodel.plan_template import SECTION_ORDER
from app.fetch import fetch_text
from app.pipeline.stages import STAGES, TIERS, Outcome, RunState, StageStatus


@dataclass
class RunConfig:
    url: str
    tier: str = "hands_off"
    out_dir: str = "out"
    artifacts_dir: str = "artifacts"
    paid: bool = False        # allow paid API calls (keywords, serp)
    llm: bool = True          # allow OpenRouter drafting
    query: str | None = None  # default: derived from collection handle


FURNITURE_HEADING_RE = re.compile(
    r"^(your cart|cart|subtotal|log in|log out|login|sign in|sign up|create account|"
    r"register|search|404\b|page not found|checkout|continue shopping|subscribe|"
    r"newsletter|menu|close|accept all|decline|cookie|your cart is empty)\b", re.I)
NAV_LINK_RE = re.compile(
    r"customer_authentication|/account\b|/cart\b|/search\b|/challenge|/policies/|"
    r"^mailto:|^tel:", re.I)
ACRONYMS = {"thca": "THCA", "thc": "THC", "thc-a": "THCA", "thc-p": "THC-P",
            "cbd": "CBD", "cbg": "CBG", "cbn": "CBN", "hhc": "HHC",
            "delta-8": "Delta-8", "delta-9": "Delta-9", "delta-10": "Delta-10"}


def pretty_title(s: str) -> str:
    """Handle -> display title with cannabinoid acronym awareness."""
    words = []
    for w in s.replace("_", " ").replace("-", " ").split():
        lw = w.lower()
        words.append(ACRONYMS.get(lw, w.capitalize()))
    return " ".join(words)


class Runner:
    def __init__(self, cfg: RunConfig):
        self.cfg = cfg
        self.state = RunState(tier=cfg.tier)
        slug = collection_handle_from_url(cfg.url)
        self.slug = slug
        self.art_dir = Path(cfg.artifacts_dir) / slug
        self.art_dir.mkdir(parents=True, exist_ok=True)
        self.decisions: list[str] = []

    # -- artifact persistence -------------------------------------------
    def _save(self, name: str, data) -> None:
        (self.art_dir / f"{name}.json").write_text(
            json.dumps(data, indent=1, default=str), encoding="utf-8")

    def _load(self, name: str):
        p = self.art_dir / f"{name}.json"
        return json.loads(p.read_text()) if p.exists() else None

    # -- gate helper ------------------------------------------------------
    def _gate(self, stage_id: str, summary: str) -> bool:
        if stage_id not in TIERS[self.cfg.tier]:
            return True
        self.decisions.append(f"AUTO-APPROVED [{self.cfg.tier}]: {summary}")
        return True

    # -- main loop --------------------------------------------------------
    def run(self) -> Path:
        handlers = {s.id: getattr(self, f"_stage_{s.id}") for s in STAGES}
        for stage in STAGES:
            self.state.stage = stage.id
            self.state.status = StageStatus.RUNNING
            try:
                halt = handlers[stage.id]()
            except Exception as exc:  # per-stage isolation: record and stop
                self.state.status = StageStatus.FAILED
                self._save("error", {"stage": stage.id, "error": str(exc)})
                print(f"  [{stage.id}] FAILED: {exc}")
                raise
            self.state.status = StageStatus.DONE
            if halt:  # preflight outcome halted the run
                break
        report = self._stage_render()
        print(f"  pipeline complete -> {report}")
        return Path(report)

    # -- stages -----------------------------------------------------------
    @staticmethod
    def _looks_like_collection(html: str, handle: str) -> bool:
        """Distinguish a real collection page from a 404 template that merely
        lists recommended products. Collection signals: an H1 naming the
        collection, a canonical pointing at /collections/<handle>, or
        og:type product.group."""
        if not html:
            return False
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.find("h1")
        if h1 and "collection" in h1.get_text().lower():
            return True
        canonical = soup.find("link", rel="canonical")
        if canonical and f"/collections/{handle}" in (canonical.get("href") or ""):
            return True
        og = soup.find("meta", property="og:type")
        if og and (og.get("content") or "") == "product.group":
            return True
        return False

    def _stage_preflight(self):
        # the target store flip-flops between the real page and its 404
        # template under bot pressure: retry before accepting a failure
        handle = collection_handle_from_url(self.cfg.url)
        html, final_url, status, outcome, notes = "", self.cfg.url, 0, Outcome.OK, []
        for attempt in range(3):
            status, final_url, html = fetch_text(self.cfg.url)
            original = self.cfg.url.rstrip("/")
            outcome, notes = Outcome.OK, []
            if status == 404:
                if self._looks_like_collection(html, handle):
                    notes = [f"soft-404 serving (attempt {attempt + 1}): HTTP 404 "
                             f"but collection signals present"]
                else:
                    outcome = Outcome.NOT_FOUND
            elif status in (401, 403):
                outcome = Outcome.INACCESSIBLE
            elif not html or len(html) < 500:
                outcome = Outcome.INACCESSIBLE
            elif final_url.rstrip("/") != original:
                notes = [f"final URL: {final_url}"]
            if outcome == Outcome.OK or attempt == 2:
                break
            time.sleep(5 * (attempt + 1))
        if outcome == Outcome.NOT_FOUND and self._looks_like_collection(html, handle):
            outcome, notes = Outcome.OK, notes + ["collection signals found on final attempt"]
        elif status in (401, 403):
            outcome = Outcome.INACCESSIBLE
        elif not html or len(html) < 500:
            outcome = Outcome.INACCESSIBLE
        elif final_url.rstrip("/") != original:
            outcome, notes = Outcome.REDIRECT, [f"final URL: {final_url}"]

        if outcome in (Outcome.NOT_FOUND, Outcome.INACCESSIBLE):
            self.state.outcome = outcome
            self._save("preflight", {"outcome": outcome.value, "status": status,
                                     "notes": notes, "url": self.cfg.url})
            print(f"  [preflight] {outcome.value} — plan halted")
            return True

        platform = detect_platform(final_url, html)
        self._html = html
        (self.art_dir / "page.html").write_text(html, encoding="utf-8")
        self.state.outcome = outcome
        self._save("preflight", {"outcome": outcome.value, "status": status,
                                 "final_url": final_url, "platform": platform,
                                 "notes": notes})
        print(f"  [preflight] ok ({platform})")
        return False

    def _stage_crawl(self):
        html = self._read_page_html()
        snap = snapshot_from_html(html, self.cfg.url)
        data = snap.__dict__.copy()
        self._save("crawl", data)
        print(f"  [crawl] {snap.word_count} words, {len(snap.headings)} headings, "
              f"{len(snap.internal_links)} internal links")
        return False

    def _read_page_html(self) -> str:
        # Prefer in-memory copy: disk artifacts may be reaped by mount TTL
        # sweeps between stages; the run must not depend on their survival.
        if getattr(self, "_html", None):
            return self._html
        p = self.art_dir / "page.html"
        try:
            return p.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._save("lost_page_html", {
                "dir": sorted(os.listdir(self.art_dir)),
                "cwd": os.getcwd(),
                "resolved": str(p.resolve()),
            })
            raise

    def _snapshot(self) -> PageSnapshot:
        """Re-hydrate the crawl artifact — stages consume artifacts, not files."""
        data = self._load("crawl")
        if data is None:
            html = (self.art_dir / "page.html").read_text(encoding="utf-8")
            data = snapshot_from_html(html, self.cfg.url).__dict__
        return PageSnapshot(**{k: data.get(k) for k in
                               PageSnapshot.__dataclass_fields__})

    def _stage_audit(self):
        snap = self._snapshot()
        query = self._query()
        results = run_checks(snap, query)
        table = dimension_scores(results)
        self._save("audit", {"checks": [r.__dict__ for r in results],
                             "dimension_table": table,
                             "overall": overall_score(table)})
        print(f"  [audit] overall: {overall_score(table)}")
        return False

    def _stage_catalog(self):
        pre = self._load("preflight")
        html = self._read_page_html()
        adapter = get_adapter(pre["platform"])
        catalog = adapter.fetch_collection(self.cfg.url, html)
        from dataclasses import asdict
        self._save("catalog", asdict(catalog))
        print(f"  [catalog] {len(catalog.products)} products "
              f"(${catalog.price_range[0]:.2f}–${catalog.price_range[1]:.2f})")
        return False

    def _stage_gsc(self):
        self._save("gsc", {"status": "skipped",
                           "reason": "Search Console requires OAuth consent; "
                                     "use the Connect Google flow in the UI tier."})
        return False

    def _stage_keywords(self):
        query = self._query()
        if not (self.cfg.paid and os.environ.get("DATAFORSEO_LOGIN")):
            cands = self._keyword_candidates()
            self._save("keywords", {"status": "heuristic",
                                    "primary": query, "candidates": cands})
            print(f"  [keywords] heuristic ({len(cands)} candidates from catalog)")
            return False
        from app.clients.dataforseo import DataForSEOClient
        dfs = DataForSEOClient()
        cands = self._keyword_candidates()
        try:
            vols = dfs.volumes([query, *cands[:20]])
            related = dfs.related_keywords(query)
            self._save("keywords", {"status": "live", "primary": query,
                                    "volumes": vols, "related": related})
            print(f"  [keywords] live volumes for {len(vols)} terms")
        except Exception as exc:
            self._save("keywords", {"status": "heuristic",
                                    "primary": query, "candidates": cands,
                                    "live_error": str(exc)[:200]})
            print(f"  [keywords] live pull failed ({exc}); heuristic fallback")
        return False

    def _stage_serp(self):
        if not (self.cfg.paid and os.environ.get("DATAFORSEO_LOGIN")):
            self._save("serp", {"status": "skipped",
                                "reason": "pass --paid to enable SERP pull"})
            return False
        from app.clients.dataforseo import DataForSEOClient
        try:
            serp = DataForSEOClient().serp(self._query())
            self._save("serp", serp)
            print(f"  [serp] {len(serp['organic'])} organic, {len(serp['paa'])} PAA")
        except Exception as exc:
            self._save("serp", {"status": "skipped", "live_error": str(exc)[:200]})
            print(f"  [serp] live pull failed ({exc})")
        return False

    def _stage_reviews(self):
        self._save("reviews", {"status": "skipped",
                               "reason": "no review feed connected; "
                                         "Business Data API is the automated fallback"})
        return False

    def _stage_entities(self):
        catalog = self._load("catalog")
        snap = self._load("crawl")
        titles = " ".join(p["title"] for p in catalog["products"][:50])
        strains = sorted({w for w in re.findall(r"\b[A-Z][a-z]{3,}\b", titles)}
                         - {"Flower", "Collection", "Shop", "Sale", "Gummies"})
        tags = sorted({t for p in catalog["products"] for t in p.get("tags", [])})[:30]
        entities = {
            "vendors": sorted({p["vendor"] for p in catalog["products"] if p.get("vendor")})[:10],
            "product_names": [p["title"] for p in catalog["products"][:12]],
            "strain_names": strains[:20],
            "tags": tags,
            "sizes_g": catalog.get("grams") or self._gram_sizes(catalog),
            "price_range": list(self._price_range(catalog)),
            "schema_types": sorted(set(snap.get("schema_types", []))),
        }
        self._save("entities", entities)
        print(f"  [entities] {len(entities['product_names'])} products named, "
              f"{len(strains)} strain-like terms")
        return False

    def _stage_analysis(self):
        audit = self._load("audit")
        snap = self._load("crawl")
        entities = self._load("entities")
        serp = self._load("serp") or {}
        catalog = self._load("catalog")

        needs = [r["check"] for r in audit["checks"] if r["status"] in ("Needs work", "Fail")]
        h2s = [t for lvl, t in snap["headings"]
               if lvl == 2 and not FURNITURE_HEADING_RE.match(t.strip())]
        outline = [{"heading": h, "decision": "KEEP"} for h in h2s[:12]]
        outline.insert(0, {"heading": f"Why Buy {pretty_title(catalog['collection_title'])} from Us?",
                           "decision": "ADD"})
        outline.append({"heading": "Frequently Asked Questions", "decision": "KEEP"})

        paa_qs = [p["question"] for p in serp.get("paa", [])]
        q = self._query()
        faqs = paa_qs[:8] or [
            f"What is {q}?",
            f"How much {q} should I buy?",
            f"Is {q} legal?",
            "How is it shipped?",
        ]
        links = [{"anchor": l["anchor"], "href": l["href"], "decision": "KEEP"}
                 for l in snap["internal_links"]
                 if not NAV_LINK_RE.search(l["href"])][:12]
        analysis = {"outline": outline, "faqs": faqs, "internal_links": links,
                    "issues": needs, "entities_summary": entities}
        self._save("analysis", analysis)
        self._gate("analysis", f"outline ({len(outline)} headings), {len(faqs)} FAQs")
        print(f"  [analysis] {len(outline)} outline items, {len(needs)} audit issues to fix")
        return False

    def _stage_drafting(self):
        analysis = self._load("analysis")
        audit = self._load("audit")
        catalog = self._load("catalog")
        snap = self._load("crawl")
        brief = {
            "platform": self._load("preflight")["platform"],
            "query": self._query(),
            "collection_title": catalog["collection_title"],
            "catalog_facts": {
                "products": len(catalog["products"]),
                "price_range": list(self._price_range(catalog)),
                "sizes_g": catalog.get("grams") or self._gram_sizes(catalog),
                "vendors": sorted({p["vendor"] for p in catalog["products"] if p.get("vendor")})[:5],
                "sample_products": [p["title"] for p in catalog["products"][:8]],
            },
            "audit_fixes": [r for r in audit["checks"] if r["status"] in ("Needs work", "Fail")],
            "outline": analysis["outline"],
        }
        draft = self._fallback_draft(brief) if not (self.cfg.llm and os.environ.get(
            "OPENROUTER_API_KEY")) else self._llm_draft(brief)

        gate = [r.__dict__ for r in check_draft(
            draft.get("title", ""), draft.get("meta_description", ""),
            draft.get("h1", ""), " ".join([draft.get("intro", ""),
                                           *[s for s in draft.get("sections", {}).values()]]),
            self._query())]
        failing = [g for g in gate if g["status"] in ("Needs work", "Fail")]
        if failing and not (self.cfg.llm and os.environ.get("OPENROUTER_API_KEY")):
            draft = self._enforce_lengths(draft)
            gate = [r.__dict__ for r in check_draft(
                draft["title"], draft["meta_description"], draft["h1"],
                " ".join([draft["intro"], *draft["sections"].values()]), self._query())]
            failing = [g for g in gate if g["status"] in ("Needs work", "Fail")]

        self._save("draft", {"draft": draft, "gate": gate,
                             "gate_status": "pass" if not failing else "issues",
                             "claim_flags": draft.get("claim_flags", [])})
        self._gate("drafting", f"draft ready, gate {len(failing)} open items")
        print(f"  [drafting] gate: {'pass' if not failing else f'{len(failing)} open items'}")
        return False

    def _stage_diff(self):
        snap = self._load("crawl")
        draft = self._load("draft")["draft"]
        diffs = {}
        pairs = [("title", snap.get("title", ""), draft.get("title", "")),
                 ("meta_description", snap.get("meta_desc", ""), draft.get("meta_description", "")),
                 ("h1", snap.get("h1s", [""])[0] if snap.get("h1s") else "", draft.get("h1", "")),
                 ("intro", snap.get("first_paragraph", ""), draft.get("intro", ""))]
        for key, old, new in pairs:
            diffs[key] = [[r.text, r.style] for r in word_diff(old or "", new or "")]
        for heading, text in draft.get("sections", {}).items():
            old = next((t for lvl, t in snap["headings"]
                        if lvl == 2 and t.strip().lower() == heading.strip().lower()), "")
            diffs[f"section::{heading}"] = [[r.text, r.style] for r in word_diff(old, text)]
        for i, faq in enumerate(draft.get("faqs", [])):
            diffs[f"faq::{i}"] = [[r.text, r.style] for r in word_diff("", faq["a"])]
        self._save("diff", diffs)
        total_ins = sum(1 for d in diffs.values() for _, s in d if s == "ins")
        total_del = sum(1 for d in diffs.values() for _, s in d if s == "del")
        print(f"  [diff] {total_ins} words added, {total_del} removed")
        return False

    def _stage_render(self) -> str:
        doc = self._build_document()
        out = Path(self.cfg.out_dir)
        out.mkdir(exist_ok=True)
        from app.render.docx_render import render_docx
        from app.render.pdf_render import render_pdf
        pdf_path = out / f"{self.slug}_plan.pdf"
        docx_path = out / f"{self.slug}_plan.docx"
        txt_path = out / f"{self.slug}_paste_ready.txt"
        render_pdf(doc, str(pdf_path))
        render_docx(doc, str(docx_path))
        txt_path.write_text(doc.paste_ready_text(), encoding="utf-8")
        return str(pdf_path)

    # -- helpers ----------------------------------------------------------
    def _query(self) -> str:
        if self.cfg.query:
            return self.cfg.query
        return collection_handle_from_url(self.cfg.url).replace("-", " ")

    @staticmethod
    def _gram_sizes(catalog: dict) -> list[float]:
        return sorted({g for p in catalog["products"] for g in p.get("grams", []) if g})

    @staticmethod
    def _price_range(catalog: dict) -> tuple[float, float]:
        if "price_range" in catalog and catalog["price_range"]:
            pr = catalog["price_range"]
            return float(pr[0]), float(pr[1])
        prices = [p for prod in catalog.get("products", [])
                  for p in (prod.get("price_min", 0), prod.get("price_max", 0)) if p]
        return (min(prices), max(prices)) if prices else (0.0, 0.0)

    def _keyword_candidates(self) -> list[str]:
        catalog = self._load("catalog") or {"products": []}
        words: dict[str, int] = {}
        for p in catalog["products"]:
            for w in re.findall(r"[a-z]{4,}", p["title"].lower()):
                if w not in ("flower", "sale", "shop", "hemp", "with", "from"):
                    words[w] = words.get(w, 0) + 1
        return [w for w, _ in sorted(words.items(), key=lambda kv: -kv[1])[:15]]

    def _llm_draft(self, brief: dict) -> dict:
        from app.clients.llm import draft_collection_copy
        draft = draft_collection_copy(brief)
        return draft

    def _fallback_draft(self, brief: dict) -> dict:
        q = brief["query"].title()
        facts = brief["catalog_facts"]
        title = f"{q.title()} for Sale | Buy Online — {facts['products']} Strains"[:60]
        meta = (f"Shop {q} online: {facts['products']} lab-tested options from "
                f"${facts['price_range'][0]:.0f}, sizes {self._fmt_sizes(facts['sizes_g'])}. "
                f"Fast discreet shipping.")[:160]
        intro = (f"{q} is one of the most popular ways to buy hemp online, and this "
                 f"collection carries {facts['products']} options from "
                 f"${facts['price_range'][0]:.2f} to ${facts['price_range'][1]:.2f}. "
                 f"Sizes run {self._fmt_sizes(facts['sizes_g'])}, so you can grab a "
                 f"small jar to try or stock up. Everything here ships discreetly.")
        sections = {}
        for item in brief["outline"]:
            h = item["heading"]
            if item["decision"] == "KEEP" or len(sections) >= 4:
                continue
            sections[h] = (f"When you browse this {brief['collection_title']} collection, "
                           f"start with the size that fits how you actually use it. "
                           f"With {facts['products']} products between "
                           f"${facts['price_range'][0]:.0f} and ${facts['price_range'][1]:.0f}, "
                           f"there is a middle ground between the cheapest jar and the bulk bag.")
        faqs = [{"q": f, "a": (f"Short answer: it depends on what you want from the product. "
                               f"Start with the facts on this page, check the size and price "
                               f"that fit your budget, and go from there.")}
                for f in brief["outline_faqs" if "outline_faqs" in brief else "faqs"]  # noqa
                ][:6] if False else [
                {"q": f, "a": ("Start with what matters to you: size, price, or strain type. "
                               "This collection breaks each option down so you can compare "
                               "without guessing.")}
                for f in self._load("analysis")["faqs"][:6]]
        return {"title": title, "meta_description": meta, "h1": f"{q} for Sale",
                "intro": intro, "sections": sections, "faqs": faqs, "claim_flags": []}

    @staticmethod
    def _fmt_sizes(sizes: list[float]) -> str:
        return "/".join(f"{g:g}g" for g in sizes) if sizes else "multiple"

    @staticmethod
    def _enforce_lengths(draft: dict) -> dict:
        t, m = draft["title"], draft["meta_description"]
        if len(t) < 50:
            draft["title"] = (t + " | Fast Discreet Shipping")[:60]
        if len(m) < 150:
            draft["meta_description"] = (m + " Compare strains, sizes and prices before you buy.")[:160]
        return draft

    # -- document assembly --------------------------------------------------
    def _build_document(self) -> PlanDocument:
        pre = self._load("preflight")
        snap = self._load("crawl")
        audit = self._load("audit")
        catalog = self._load("catalog")
        entities = self._load("entities")
        analysis = self._load("analysis")
        draft = self._load("draft")["draft"]
        diffs = self._load("diff")
        kw = self._load("keywords") or {}
        dr = None
        if os.environ.get("AHREFS_TOKEN"):
            try:
                dr = ahrefs.domain_rating(self.cfg.url)
            except Exception:
                dr = None

        def diff_block(key):
            runs = [Run(text=t, style=s) for t, s in diffs.get(key, [])]
            return DiffPara(runs=runs) if runs else Paragraph(text="(no changes)")

        def counts(key):
            runs = diffs.get(key, [])
            add = sum(1 for _, s in runs if s == "ins")
            rem = sum(1 for _, s in runs if s == "del")
            return add, rem

        blocks = []
        blocks.append(Note(text=f"Generated {time.strftime('%Y-%m-%d')} · "
                               f"{pre['final_url']} · tier: {self.cfg.tier}"))
        blocks.append(H2(text="Page details"))
        blocks.append(KVTable(pairs=[
            ["URL", pre["final_url"]], ["Platform", pre["platform"]],
            ["Collection", pretty_title(catalog["collection_title"].replace("Collection:", "").strip())],
            ["Products", str(len(catalog["products"]))],
            ["Price range", f"${self._price_range(catalog)[0]:.2f} – ${self._price_range(catalog)[1]:.2f}"],
            ["Catalog source", {"json": "store API (complete)",
                                "crawl-grid": "rendered grid (first page only — verify counts)",
                                "store-wide-json": "store-wide fallback (not collection-scoped)"}
             .get(catalog.get("source", "json"), "unknown")],
            *( [["Domain Rating", f"{dr['dr']} — {dr['attribution']}"]] if dr else [] ),
        ]))
        blocks.append(H2(text="Subheadings"))
        blocks.append(Table(header=["Current H2", "Decision"],
                            rows=[[o["heading"], o["decision"]] for o in analysis["outline"]]))
        blocks.append(H2(text="Internal links"))
        blocks.append(Table(header=["Anchor", "URL", "Decision"],
                            rows=[[l["anchor"][:50], l["href"][:60], l["decision"]]
                                  for l in analysis["internal_links"]]))
        blocks.append(H2(text="Current performance"))
        blocks.append(Note(text="Search Console not connected — connect via the Google "
                                "OAuth flow to populate clicks, impressions, CTR and "
                                "average position."))
        blocks.append(H2(text="On-page issues"))
        blocks.append(Table(header=["Dimension", "Score", "Note"],
                            rows=[[r[0], r[1], r[2][:60]] for r in audit["dimension_table"]]))
        blocks.append(H2(text="Entity research"))
        blocks.append(KVTable(pairs=[
            ["Vendors", ", ".join(entities["vendors"]) or "—"],
            ["Strain names", ", ".join(entities["strain_names"][:10]) or "—"],
            ["Sizes", self._fmt_sizes(entities["sizes_g"])],
            ["Schema", ", ".join(entities["schema_types"]) or "—"],
        ]))
        blocks.append(H2(text="Keyword research"))
        if kw.get("status") == "live":
            rows = [[k, str(v.get("volume") or "—"),
                     str(v.get("competition") or v.get("competition_index") or "—")]
                    for k, v in list(kw.get("volumes", {}).items())[:15]]
            blocks.append(Table(header=["Keyword", "Volume", "Competition"], rows=rows))
        else:
            blocks.append(Note(text=f"Heuristic candidates from catalog titles (pass --paid "
                                    f"for live volumes): {', '.join(kw.get('candidates', []))}"))
        blocks.append(H2(text="SERP analysis"))
        serp = self._load("serp") or {}
        if serp.get("status") == "skipped":
            blocks.append(Note(text=serp.get("reason", "skipped")))
        else:
            blocks.append(Table(header=["Rank", "URL", "Title"],
                                rows=[[str(o["rank"]), (o["domain"] or "")[:30],
                                       (o["title"] or "")[:60]]
                                      for o in serp.get("organic", [])[:10]]))
        blocks.append(H2(text="Review analysis"))
        rev = self._load("reviews") or {}
        blocks.append(Note(text=rev.get("reason", "no review source connected")))
        blocks.append(H2(text="Recommendations"))
        blocks.append(Bullets(items=analysis["issues"] or ["No blocking issues found."]))
        blocks.append(H2(text="Outline"))
        blocks.append(Table(header=["Heading", "Decision"],
                            rows=[[o["heading"], o["decision"]] for o in analysis["outline"]]))
        blocks.append(H2(text="FAQs"))
        blocks.append(Numbered(items=analysis["faqs"]))
        blocks.append(H2(text="Recommended internal links"))
        blocks.append(Bullets(items=[f"{l['anchor']} → {l['href']}"
                                     for l in analysis["internal_links"][:6]]))
        blocks.append(PageBreak())
        blocks.append(H2(text="Draft content"))
        for key, label in [("title", "Title tag"), ("meta_description", "Meta description"),
                           ("h1", "H1"), ("intro", "Intro copy")]:
            add, rem = counts(key)
            blocks.append(H3(text=f"{label}" + (f" · {add} ADDED · {rem} REMOVED"
                                                if add + rem else " · KEEP")))
            blocks.append(Label(text="CHANGES"))
            blocks.append(diff_block(key))
            blocks.append(Label(text="PASTE-READY"))
            blocks.append(Paragraph(text=draft.get(key, "")))
        for heading, text in draft.get("sections", {}).items():
            key = f"section::{heading}"
            add, rem = counts(key)
            blocks.append(H3(text=f"{heading} (H2) · {add} ADDED · {rem} REMOVED"))
            blocks.append(Label(text="CHANGES"))
            blocks.append(diff_block(key))
            blocks.append(Label(text="PASTE-READY"))
            blocks.append(Paragraph(text=text))
        for i, faq in enumerate(draft.get("faqs", [])):
            key = f"faq::{i}"
            add, _ = counts(key)
            blocks.append(H3(text=f"{faq['q']} · {add} ADDED · 0 REMOVED"))
            blocks.append(Label(text="PASTE-READY"))
            blocks.append(Paragraph(text=faq["a"]))
        if draft.get("claim_flags"):
            blocks.append(Note(text="Claim flags to review: " + "; ".join(draft["claim_flags"])))
        blocks.append(H2(text="Sources"))
        blocks.append(Bullets(items=[
            f"Live page crawl: {pre['final_url']}",
            f"{pre['platform'].title()} catalog API",
            "DataForSEO (when --paid)" if self.cfg.paid else "DataForSEO (not enabled)",
            *( [dr["attribution"]] if dr else [] ),
        ]))
        return PlanDocument(
            title=f"Page plan — {pretty_title(catalog['collection_title'])}",
            subtitle=pretty_title(catalog["collection_title"]),
            blocks=blocks)
