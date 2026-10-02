"""Deterministic 8-dimension checklist scoring.

Rules come from app/templates/onpage/onpage_checklist.md. Anything
measurable without judgment lives here; the LLM handles prose, prioritization,
and drafted replacements. The same checks run as the pre-publish gate on
drafted content (check_draft) before a plan ships.
"""
from dataclasses import dataclass

from app.audit.snapshot import BAD_ANCHORS, PageSnapshot

PASS, NEEDS, FAIL, INFO = "Pass", "Needs work", "Fail", "Info"

TITLE_MIN, TITLE_MAX = 50, 60
META_MIN, META_MAX = 150, 160


@dataclass
class CheckResult:
    dimension: str
    check: str
    status: str
    note: str = ""


def _len(s: str) -> int:
    return len(s.strip())


def run_checks(snap: PageSnapshot, query: str) -> list[CheckResult]:
    q = query.lower().strip()
    r: list[CheckResult] = []
    add = r.append

    # 1. Title tag
    tl = _len(snap.title)
    if not snap.title:
        add(CheckResult("Title tag", "Exists", FAIL, "no <title> found"))
    else:
        add(CheckResult("Title tag", "Length 50-60", PASS if TITLE_MIN <= tl <= TITLE_MAX else NEEDS,
                        f"{tl} chars"))
        front = snap.title.lower()[:40]
        add(CheckResult("Title tag", "Query near front", PASS if q.split()[0] in front else NEEDS,
                        "primary word in first 40 chars" if q.split()[0] in front else "primary word not near front"))
        same = snap.title.strip().lower() == (snap.h1s[0].strip().lower() if snap.h1s else "")
        add(CheckResult("Title tag", "Not identical to H1", PASS if not same else NEEDS,
                        "identical to H1" if same else ""))
        add(CheckResult("Title tag", "Uniqueness", INFO, "needs site crawl"))

    # 2. Meta description
    ml = _len(snap.meta_desc)
    if not snap.meta_desc:
        add(CheckResult("Meta description", "Exists", FAIL, "no meta description"))
    else:
        add(CheckResult("Meta description", "Length 150-160", PASS if META_MIN <= ml <= META_MAX else NEEDS,
                        f"{ml} chars"))
        add(CheckResult("Meta description", "Differs from title", PASS if snap.meta_desc.strip().lower() not in snap.title.lower() else NEEDS,
                        "" if snap.meta_desc.strip().lower() not in snap.title.lower() else "repeats title"))
        add(CheckResult("Meta description", "Uniqueness", INFO, "needs site crawl"))

    # 3. Header structure
    add(CheckResult("Header structure", "Exactly one H1",
                    PASS if len(snap.h1s) == 1 else FAIL, f"{len(snap.h1s)} H1"))
    if snap.h1s:
        add(CheckResult("Header structure", "H1 has query", PASS if q in snap.h1s[0].lower() else NEEDS,
                        snap.h1s[0][:60]))
    levels = [l for l, _ in snap.headings]
    skipped = any(b - a > 1 for a, b in zip(levels, levels[1:]) if a)
    add(CheckResult("Header structure", "No skipped levels", PASS if not skipped else NEEDS,
                    "" if not skipped else "heading level jump"))

    # 4. Body content
    add(CheckResult("Body content", "Word count", PASS if snap.word_count >= 300 else NEEDS,
                    f"{snap.word_count} words"))
    add(CheckResult("Body content", "First paragraph answers intent",
                    PASS if q.split()[0] in snap.first_paragraph.lower() else NEEDS,
                    snap.first_paragraph[:70]))

    # 5. Internal links
    n = len(snap.internal_links)
    add(CheckResult("Internal links", "2-3+ outbound internal", PASS if n >= 2 else NEEDS, f"{n} found"))
    bad = [l for l in snap.internal_links if l["anchor"].lower() in BAD_ANCHORS]
    add(CheckResult("Internal links", "Anchors descriptive", PASS if not bad else NEEDS,
                    "" if not bad else f"{len(bad)} generic anchors"))
    add(CheckResult("Internal links", "Inbound links", INFO, "needs site crawl"))
    add(CheckResult("Internal links", "No redirects/broken", INFO, "needs link checker"))

    # 6. Images
    total = len(snap.images)
    if total:
        with_alt = sum(1 for i in snap.images if i["alt"])
        dims = sum(1 for i in snap.images if i["has_dims"])
        lazy = sum(1 for i in snap.images if i["lazy"])
        modern = sum(1 for i in snap.images if i["modern"])
        add(CheckResult("Images and media", "Alt coverage", PASS if with_alt / total >= 0.9 else NEEDS,
                        f"{with_alt}/{total}"))
        add(CheckResult("Images and media", "Width/height set", PASS if dims / total >= 0.9 else NEEDS,
                        f"{dims}/{total}"))
        add(CheckResult("Images and media", "Lazy loading", PASS if lazy / total >= 0.5 else NEEDS,
                        f"{lazy}/{total}"))
        add(CheckResult("Images and media", "Modern formats", PASS if modern / total >= 0.5 else NEEDS,
                        f"{modern}/{total} webp/avif"))
    else:
        add(CheckResult("Images and media", "Images present", INFO, "none found"))

    # 7. URL slug
    slug = snap.slug.lower()
    add(CheckResult("URL slug", "Lowercase hyphenated",
                    PASS if slug == snap.slug and " " not in slug else NEEDS, snap.slug))
    add(CheckResult("URL slug", "Length < 60", PASS if len(snap.slug) < 60 else NEEDS,
                    f"{len(snap.slug)} chars"))
    add(CheckResult("URL slug", "Query in slug", PASS if q.split()[0] in slug else NEEDS, ""))
    add(CheckResult("URL slug", "No dates/params", PASS if not any(c.isdigit() for c in slug) and "=" not in snap.url else NEEDS, ""))

    # 8. Schema
    add(CheckResult("On-page schema", "Schema present", PASS if snap.schema_types else FAIL,
                    ", ".join(sorted(set(snap.schema_types)))[:80] or "none"))
    add(CheckResult("On-page schema", "BreadcrumbList", PASS if snap.has_breadcrumb_schema else NEEDS, ""))
    add(CheckResult("On-page schema", "Rich results valid", INFO, "needs Rich Results Test"))
    return r


DIMENSIONS = ["Title tag", "Meta description", "Header structure", "Body content",
              "Internal links", "Images and media", "URL slug", "On-page schema"]


def dimension_scores(results: list[CheckResult]) -> list[list[str]]:
    """Aggregate check results into the score table (dimension, score, note)."""
    table = []
    for dim in DIMENSIONS:
        items = [r for r in results if r.dimension == dim]
        judged = [r for r in items if r.status in (PASS, NEEDS, FAIL)]
        if any(r.status == FAIL for r in judged):
            score = FAIL
        elif any(r.status == NEEDS for r in judged):
            score = NEEDS
        else:
            score = PASS
        note = next((r.note for r in judged if r.status in (NEEDS, FAIL) and r.note), "")
        table.append([dim, score, note])
    return table


def overall_score(table: list[list[str]]) -> str:
    scores = [row[1] for row in table]
    if FAIL in scores:
        return FAIL
    if NEEDS in scores:
        return NEEDS
    return PASS


def check_draft(title: str, meta: str, h1: str, body_text: str, query: str) -> list[CheckResult]:
    """Pre-publish gate: run measurable checks on drafted replacements."""
    snap = PageSnapshot(url="", title=title, meta_desc=meta, h1s=[h1] if h1 else [])
    words = body_text.split()
    snap.word_count = len(words)
    snap.first_paragraph = " ".join(words[:60])
    # Slug/schema/link-checks are page-level, not copy-level — the gate only
    # judges the drafted copy itself.
    return [r for r in run_checks(snap, query)
            if r.status != INFO and r.dimension not in
            ("URL slug", "On-page schema") and r.check != "2-3+ outbound internal"]
