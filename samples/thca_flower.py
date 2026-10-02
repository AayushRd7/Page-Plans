"""Reference encoding of the thca flower page plan (client-supplied sample).

Fidelity rules: every section from the sample is encoded, tables carry all
rows, and every draft section has its real CHANGES view (word-level diff,
reconstructed from the sample PDF's own strikeout/highlight geometry) plus
the sample's own ADDED/REMOVED counts. This file is the acceptance test
for the renderers and, later, for the live pipeline.
"""
import json
from pathlib import Path

from app.diffing import word_diff
from app.docmodel.blocks import (
    Bullets, DiffPara, H2, H3, KVTable, Label, Note, Numbered, PageBreak,
    Paragraph, PlanDocument, Table,
)

DATA = Path(__file__).parent / "data"
DIFFS: dict = json.loads((DATA / "thca_diffs.json").read_text())
PASTE: dict = json.loads((DATA / "thca_paste_ready.json").read_text())

# The reconstructed old text for this section is completed by hand where
# the sample's own change view wraps across its page break.
DIFFS["How to Order THCA Flower Online (H2)"]["old"] = (
    "Shopping for thca flower online shouldn't feel like a pop quiz. Start by "
    "checking the lab report, then match the strain to your vibe. Here's the "
    "game plan: Check the lab report for potency and cannabinoid content Match "
    "the strain type to your plans (indica for chill nights, sativa for active "
    "days) Pick your size, from grams to bulk options Add to cart and let us "
    "handle the rest If you want to wind down after a long day, thca indica "
    "options like Granddaddy Purple are your move. Need a daytime boost? Sativa "
    "strains have your back. Hybrid picks split the difference. When you buy "
    "thca flower online from Everything 420, you get clear descriptions, real "
    "reviews, and no sketchy surprises. Plus, our federally compliant thca "
    "flower ships discreetly to your door, so you can skip the dispensary line "
    "and keep things simple."
)

FAQ1_OLD = ('THC is the primary psychoactive compound in cannabis that is '
            'responsible for the "high" sensation. THCa is the non-psychoactive '
            'acidic precursor to THC found in raw and unprocessed cannabis '
            'plants. It converts to THC when decarboxylated, typically through '
            'heat. Delta 8 is an analogue of THC that has a slightly different '
            'chemical structure, leading to milder psychoactive effects '
            'compared to delta 9 THC. Delta 9 is another term for the THC '
            'compound, emphasizing the position of the double bond in its '
            'chemical structure, which is the most abundant and potent form of '
            'THC found in cannabis. You don\'t have to stress about a weird '
            'thca side effect when you know exactly what you\'re puffing!')
FAQ1_NEW = FAQ1_OLD[:FAQ1_OLD.index(" You don't have to stress")]
FAQ_NEW_Q = "Does THCA flower get you high?"
FAQ_NEW_A = ("Yes, once it's heated. Raw THCA is non-psychoactive, but smoking "
             "or vaping the flower converts THCA into THC, which is what "
             "produces the high. Effects vary from person to person, so if "
             "you're new, start with a small amount and see how you feel.")

# (diff title, paste-ready key) pairs for the nine body sections
DRAFT_MAP = [
    ("Lead paragraph (no heading)", "Lead paragraph (no heading)"),
    ("Buy THCA Flower Online (H2)", "Buy THCA Flower Online"),
    ("Why Shop THCA Flower at Everything 420 (H2)", "Why Shop THCA Flower at Everything 420"),
    ("THCA Strains: Indica, Sativa and Hybrid (H2)", "THCA Strains: Indica, Sativa and Hybrid"),
    ("THC-A Flower Quality and Lab Testing (H2)", "THC-A Flower Quality and Lab Testing"),
    ("THCA Flower Sizes and Shipping (H2)", "THCA Flower Sizes and Shipping"),
    ("More THCA Products to Explore (H2)", "More THCA Products to Explore"),
    ("Where and How Our THCA Flower Is Grown (H2)", "Where and How Our THCA Flower Is Grown"),
    ("Understanding THCA Vs. THC: What You're Actually Smoking (H2)",
     "Understanding THCA Vs. THC: What You're Actually Smoking"),
    ("How to Order THCA Flower Online (H2)", "How to Order THCA Flower Online"),
]


def _squash(text: str) -> str:
    return " ".join(text.split())


def _draft_section(blocks, diff_title: str, paste_key: str) -> None:
    d = DIFFS[diff_title]
    new = _squash(PASTE[paste_key])
    blocks.append(H3(text=diff_title))
    if d["label"]:
        blocks.append(Note(text=d["label"]))
    blocks.append(Label(text="CHANGES"))
    blocks.append(DiffPara(runs=word_diff(d["old"], new)))
    blocks.append(Label(text="PASTE-READY"))
    if paste_key == "How to Order THCA Flower Online":
        lines = PASTE[paste_key].split("\n")
        blocks.append(Paragraph(text=lines[0]))
        blocks.append(Numbered(items=lines[1:5]))
        blocks.append(Paragraph(text=_squash(" ".join(lines[5:]))))
    else:
        blocks.append(Paragraph(text=PASTE[paste_key]))


def build() -> PlanDocument:
    blocks = []

    # ---------------- Page details ----------------
    blocks += [
        H2(text="Page details"),
        KVTable(pairs=[
            ["Client", "Everything 420"],
            ["Market", "United States"],
            ["Page URL", "https://everythingfor420.com/collections/thc-a-flower"],
            ["Page Type", "Collection Page"],
            ["Products", "54"],
            ["Price range", "$11.99 – $319.99, median $29.99 (USD)"],
            ["Product types", "THC-A Flower (45)\nDelta Flower (9)"],
            ["Target keywords", "thca flower, thca online, thca website, thca for sale, "
                                "thca shop, best thca flower online, thca buds"],
            ["Title Tag", "THCA Flower for Sale | Buy Legal THC Flower Online | E420\n"
                          "THCA Flower for Sale | Shop THCA Online | E420"],
            ["Meta Desc", "Shop legal THCA flowers online at E420. Premium, lab-tested "
                          "THC-A strains with fast, discreet shipping. Find indica, sativa, "
                          "and hybrid flowers for sale today!\n"
                          "Shop THCA flower online at E420. Premium, lab-tested THC-A "
                          "strains with fast, discreet shipping. Find indica, sativa, and "
                          "hybrid flowers for sale today!"],
            ["H1", "THCA Flower"],
            ["FAQ Title", "THCA FAQs"],
        ]),
    ]

    # ---------------- Subheadings ----------------
    blocks += [
        H2(text="Subheadings"),
        Table(header=["Subheading", "Action"], rows=[
            ["intro", "improve"],
            ["Buy THCA Flower Online (H2)", "improve"],
            ["Why Shop THCA Flower at Everything 420 (H2)", "merge"],
            ["THCA Strains: Indica, Sativa and Hybrid (H2)", "improve"],
            ["THC-A Flower Quality and Lab Testing (H2)", "improve"],
            ["THCA Flower Sizes and Shipping (H2)", "improve"],
            ["More THCA Products to Explore (H2)", "improve"],
            ["Why Choose Everything420 for Your THCA Needs (H2)", "merge"],
            ["THCA Small Buds: Big Value, Same Fire (H2)", "remove"],
            ["Where and How Our THCA Flower Is Grown (H2)", "merge"],
            ["Indoor THCA Flower: Controlled Chaos, Maximum Potency (H2)", "merge"],
            ["Understanding THCA Vs. THC: What You're Actually Smoking (H2)", "improve"],
            ["How to Order THCA Flower Online (H2)", "improve"],
        ]),
    ]

    # ---------------- Internal links ----------------
    blocks += [
        H2(text="Internal links"),
        Paragraph(text="Main mega-menu (desktop + mobile) promotes VAPES, THCA FLOWER "
                       "(/collections/thc-a-flower), Legal THC (/collections/hemp-thc), "
                       "BONGS, $4.20 STORE, MYSTERY BOX on every page, so this page is in "
                       "the main nav. Live breadcrumb: Everything 420 > Legal THC "
                       "(/collections/hemp-thc) > THC-A (/collections/thc-a-products) > "
                       "THCA Flower."),
        Label(text="RELATED COLLECTIONS"),
        Table(header=["Collection", "Path"], rows=[
            ["Legal THC Flower", "/collections/legal-thc-flower"],
            ["Legal THC", "/collections/hemp-thc"],
            ["THC-A Products", "/collections/thc-a-products"],
            ["THCA Beverages", "/collections/legal-drinks"],
            ["CBD", "/collections/cbd"],
            ["Delta 9", "/collections/delta-9-products"],
        ]),
        Label(text="CURRENT INTERNAL LINKS"),
        Paragraph(text="Also linked from THC-A Products (parent hub, also this page's "
                       "breadcrumb parent) and Legal THC Flower (/collections/legal-thc-flower)."),
        Label(text="LINKS THIS PAGE CURRENTLY MAKES"),
        Bullets(items=[
            "Legal THC Flower /collections/legal-thc-flower",
            "Legal THC /collections/hemp-thc (301 redirects to /collections/all-legal-thc)",
            "THCA Beverages /collections/legal-drinks",
            "THC-A Products /collections/thc-a-products",
            "CBD (now a 404) /collections/cbd",
            "Delta 9 /collections/delta-9-products",
        ]),
        Note(text="Navigation is healthy: the page is in the main mega-menu, is linked from "
                  "its parent hub (5 links on the hub page), and has a proper breadcrumb. "
                  "It is not orphaned, so no breadcrumb or hub-link fix is needed. 2 of the "
                  "6 body links need a fix."),
    ]

    # ---------------- Current performance ----------------
    blocks += [
        H2(text="Current performance"),
        Paragraph(text="Severe decline vs the prior 28 days: clicks 114 vs 1,535 (-92.6%), "
                       "impressions 17,759 vs 37,895 (-53.1%). Nearly every non-brand query "
                       "lost 30 to 60+ positions: 'thca flower' went from 30.8 to 87.2, "
                       "'thca online' from 13.0 to 66.9, 'thca websites' from 5.5 to 47.3, "
                       "'thca flower deals online' from 6.6 to 62.2. The same window shows "
                       "the sibling /collections/legal-thc-flower down 91.0% in clicks and "
                       "the parent hub /collections/thc-a-products down 81.0%, so this is a "
                       "pattern across the client's THC collections, not something unique to "
                       "this page or explained by its copy alone. The average position "
                       "(25.5) is flattered by brand-style queries; the category terms sit "
                       "far lower. DataForSEO Labs rank snapshots predate this window and "
                       "are used as history, not as current rankings."),
        Note(text="Period 2026-08-24 – 2026-09-20"),
        KVTable(pairs=[
            ["Clicks", "114"],
            ["Impressions", "17,759"],
            ["CTR", "0.64%"],
            ["Avg. position", "25.50"],
        ]),
        Table(header=["Query", "Clicks", "Impr.", "Pos."], caption="TOP QUERIES", rows=[
            ["thca flower", "3", "473", "87.20"],
            ["everything420.com", "1", "434", "1.00"],
            ["everything 420 app", "1", "213", "3.30"],
            ["420 websites", "3", "206", "2.10"],
            ["420 store", "1", "187", "4.00"],
            ["420 shop online", "2", "159", "1.10"],
            ["best thca flower", "1", "152", "49.80"],
            ["buy thca flower", "1", "121", "72.40"],
            ["best thca flower online", "1", "104", "51.40"],
            ["thca online", "2", "67", "66.90"],
            ["420store", "1", "49", "2.20"],
            ["cheap thca flower", "3", "45", "53.50"],
            ["everything420", "1", "34", "1.00"],
            ["thca flower deals online", "3", "24", "62.20"],
            ["cheap thca", "1", "17", "45.80"],
        ]),
    ]

    # ---------------- On-page issues ----------------
    blocks += [
        H2(text="On-page issues"),
        Bullets(items=[
            "The body is about 1,360 words across 12 H2s plus 8 FAQs, and the primary "
            "phrase 'thca flower' appears roughly 26 times across title, meta, body and "
            "FAQs. Several passages read as keyword lists rather than sentences, and the "
            "slang tone doesn't match a commercial category page.",
            "The title tag, the opening lead and the first H2 still use 'legal THC flower' "
            "wording, the phrase and product set the sibling /collections/legal-thc-flower "
            "is being repositioned to own. The first H2 also repeats the opening lead "
            "almost word for word.",
            "Several claims don't match the live catalog (checked against all 54 products' "
            "titles, variants, descriptions and tags): named strains Granddaddy Purple, "
            "Purple Punch and Jack Herer (0 products; Sour Diesel only as a 'Sour Apple "
            "Diesel' bong ball), 'from 1g samples' (smallest size is 2g; sizes are 2g, 3.5g, "
            "7g, 14g and 28g), THCA shake (0), small buds (0), and organic / regenerative / "
            "sungrown / outdoor / greenhouse growing (0).",
            "The catalog does support: 'Grown in Oregon' on 21 product descriptions (Smoke "
            "Nation lines), indoor cultivation on 9, and listed THCa percentages on 9 "
            "product pages, ranging 32.5% to 37.0%. The copy's '20-35% THCA' range doesn't "
            "match those listed values.",
            "Health, legal and testing claims are live in several places and are flagged "
            "for the client to verify: 'federally legal under the 2018 Farm Bill', "
            "'therapeutic potential', 'stress relief', 'awesome thca benefits', and 'every "
            "product undergoes third-party testing'. Only 2 of 54 product descriptions "
            "mention lab results.",
            "Sections overlap heavily: the first two H2s both pitch buying online; the "
            "quality, organic and indoor H2s all make quality claims; the shopping-experience "
            "and how-to-buy H2s both cover sizes and ordering; 'Understanding THCA vs THC' "
            "repeats FAQ 1 and FAQ 8.",
            "FAQ block: the live heading is 'THCa Flower FAQS' (inconsistent casing). FAQ 4 "
            "(THCA shake), FAQ 5 (organic) and FAQ 7 ('what makes your THCA strains "
            "special') cover a product the collection doesn't sell, an unsupported claim "
            "and generic filler.",
            "Product check (standing rule): the 54 products really are THC-A flower "
            "(titles, descriptions and breadcrumb agree). The same 54 SKUs also sit on "
            "/collections/legal-thc-flower, a duplicate the client keeps, which is why this "
            "page must keep to 'thca flower' language and drop 'legal THC flower' targeting.",
            "Links: 'CBD product lines' links to /collections/cbd, a 404 (remove link, keep "
            "words as plain text); 'thc-a hemp products' links to /collections/hemp-thc, "
            "which redirects to /collections/all-legal-thc (fix link to the final URL). The "
            "other 4 return 200.",
        ]),
    ]

    # ---------------- Entity research ----------------
    blocks += [
        H2(text="Entity research"),
        Note(text="An entity is a unique 'thing' or concept that Google completely "
                  "understands. Including these on your page shows semantic relevance to "
                  "your target keywords."),
        Table(header=["Type", "Value", "Count"], caption="TOP VALUES BY TYPE", rows=[
            ["Brand", "Smoke Nation", "19"],
            ["Brand", "Emerald", "8"],
            ["Brand", "Smak'd", "6"],
            ["Brand", "Xhale", "6"],
            ["Brand", "Numb", "4"],
            ["Brand", "Fuego", "3"],
            ["Scent flavor", "Citrus", "12"],
            ["Scent flavor", "sweet", "10"],
            ["Scent flavor", "pine", "10"],
            ["Scent flavor", "earthy", "10"],
            ["Scent flavor", "gassy", "5"],
            ["Scent flavor", "vanilla", "5"],
            ["Scent flavor", "Lemon", "4"],
            ["Scent flavor", "nutty", "4"],
            ["Scent flavor", "Candy", "3"],
            ["Product form", "THC-A Flower", "52"],
            ["Product form", "Flower", "36"],
            ["Product form", "Hybrid", "8"],
            ["Product form", "nug", "8"],
            ["Product form", "individually wrapped", "6"],
            ["Product form", "resealable jar", "5"],
            ["Material", "trichomes", "9"],
        ]),
        Label(text="CONTENT ANGLES"),
        Bullets(items=[
            "Real flavor descriptors from the catalog that the copy never uses (citrus, "
            "pine, gassy, lemon, nutty, candy) are a better source of concrete detail than "
            "the generic 'rich aromas' and 'earthy notes' lines, and replace the four "
            "strain names that aren't stocked. Use them as examples of what strains taste "
            "like, not as a product list, since strains rotate.",
            "'trichomes' (9 products) is a real, checkable quality cue that only partly "
            "appears in the copy today; one mention fits the merged quality section.",
            "Vendor names (Smoke Nation 25 products, Five Star Distro 9, Emerald 2.0 9) "
            "aren't recommended for this page's evergreen copy: the vendor mix rotates, and "
            "none are named in the current copy either.",
            "Oregon origin (21 products) and indoor cultivation (9 products) are supported "
            "by product descriptions but only for select strains, so any mention should "
            "say 'select' or 'several', not imply the whole range.",
        ]),
        Label(text="ENTITIES PRESENT IN COPY"),
        Table(header=["Type", "Value", "Match"], rows=[
            ["Product form", "THC-A Flower", "exact"],
            ["Product form", "Flower", "exact"],
            ["Feature", "Cannabinoids", "exact"],
            ["Scent flavor", "earthy", "exact"],
            ["Scent flavor", "sweet", "exact"],
            ["Size", "3.5 grams", "partial"],
            ["Material", "trichomes", "partial"],
            ["Product form", "Delta Flower", "partial"],
            ["Product form", "Hybrid", "exact"],
            ["Product form", "nug", "exact"],
            ["Size", "3.5-gram", "partial"],
            ["Brand", "THC-A", "exact"],
            ["Product form", "THC-A", "exact"],
            ["Product form", "THCa", "exact"],
            ["Brand", "Everything 420", "exact"],
        ]),
        Label(text="ENTITIES MISSING FROM COPY"),
        Table(header=["Type", "Value"], rows=[
            ["Brand", "Smoke Nation"], ["Size", "3.5g"], ["Feature", "Blend"],
            ["Scent flavor", "Citrus"], ["Scent flavor", "pine"], ["Brand", "Delta Warning"],
            ["Brand", "Emerald"], ["Brand", "HempTHC"], ["Occasion", "Sesh"],
            ["Color", "White"], ["Size", "7g"], ["Brand", "Smak'd"],
            ["Brand", "Xhale"], ["Product form", "individually wrapped"], ["Audience", "crew"],
            ["Product form", "resealable jar"], ["Scent flavor", "gassy"], ["Brand", "Numb"],
            ["Product form", "Bong Balls"], ["Scent flavor", "citrusy"],
        ]),
        Label(text="WIKIPEDIA CONCEPTS"),
        Table(header=["Concept", "Why it matters"], rows=[
            ["Cannabinoid", "Definitional anchor for the THCA vs THC vs Delta 8 / Delta 9 "
                            "FAQ that stays on the page."],
            ["Trichome", "Definitional anchor for the trichome quality cue (9 products); "
                         "the cannabis-specific meaning comes from the catalog, not the "
                         "wiki text."],
        ]),
        Label(text="ENTITY GAPS VS REVIEWS"),
        Bullets(items=[
            "Reviews praise effect, flavor, value and shipping; the page copy is heavy on "
            "effect and 'quality' superlatives but has almost no concrete flavor detail, "
            "which is the gap the catalog's flavor descriptors can fill.",
        ]),
    ]

    # ---------------- Keyword research ----------------
    blocks += [
        H2(text="Keyword research"),
        Paragraph(text="These are the keywords we've selected for this page. The primary "
                       "keyword is the target. Secondaries are additional ones that may be "
                       "relevant, not necessarily a priority. Primary: thca flower."),
        Table(header=["Keyword", "Why", "Volume"], caption="SECONDARIES", rows=[
            ["thca online", "The page's biggest historical query (131 clicks at position "
                            "13.0 in the prior 28 days, 2,900/mo); the phrase already "
                            "appears once in the copy and should stay, and it now leads "
                            "the title tag.", "2,900"],
            ["thca website", "'thca websites' and 'thca website' (1,300/mo each) earned 66 "
                             "and 22 clicks at positions 5.5 and 2.0 in the prior period. "
                             "The copy's one 'thca website' mention should survive the "
                             "cleanup in a normal sentence.", "1,300"],
            ["thca for sale", "50 clicks at position 18.0 in the prior period; 'thca sale' "
                              "is 480/mo. Already in the copy twice and in the title tag "
                              "('THCA Flower for Sale').", "480"],
            ["thca shop", "3,600/mo and 38 clicks at position 16.3 in the prior period, but "
                          "the exact phrase appears nowhere in the copy today. One natural "
                          "mention in the merged buying section covers it.", "3,600"],
            ["best thca flower online", "1,600/mo and a competitive SERP where competitors' "
                                        "titles lead with 'Best/Buy/Order THCA Flower "
                                        "Online'. Present twice in the copy today as "
                                        "unbacked superlatives; recommend one softer "
                                        "'looking for the best THCA flower online?' style "
                                        "mention instead.", "1,600"],
            ["thca buds", "1,000/mo ('thca bud' is also 1,000/mo); already in the copy "
                          "once, and 'buds' is how the catalog describes the product.", "1,000"],
        ]),
        Label(text="SEARCH CONSOLE QUERY NOTES"),
        Table(header=["Query", "Note"], rows=[
            ["thca flower", "The primary. 1,736 impressions at position 30.8 (73 clicks) in "
                            "the prior period; 40,500/mo. The page now ranks around "
                            "position 87 for it, the clearest single sign of the decline."],
            ["thca flower uk", "6 clicks from 14 impressions, but a UK query on a US-market "
                               "page; not pursued."],
            ["420 websites", "Likely brand or navigational; ambiguous; not used as keyword "
                             "evidence."],
            ["everything420.com", "Navigational brand query; excluded from keyword decisions."],
            ["thca flower deals online", "40 clicks at position 6.6 in the prior period. "
                                         "Real demand, but no product is discounted (0 on "
                                         "sale), so the plan adds no 'deals' or 'clearance' "
                                         "wording, and the client wants price-led phrasing "
                                         "avoided on this page."],
        ]),
    ]

    # ---------------- SERP analysis ----------------
    blocks += [
        H2(text="SERP analysis"),
        Paragraph(text="Across our researched keywords, these are the competitors we're able "
                       "to compete with, along with questions surfaced that may be relevant "
                       "for content."),
        Table(header=["Question", "Status"], caption="PEOPLE ALSO ASK", rows=[
            ["Does THCA cause a high?", "Answered by a new FAQ ('Does THCA flower get you "
                                        "high?'), replacing the core value of the cut THCA "
                                        "vs THC section"],
            ["Will THCA get me high anymore?", "Not answered: the wording implies a recent "
                                               "legal change and would need the client's own "
                                               "compliance review"],
            ["Why shouldn't you smoke THCA?", "Not answered: health-safety framing; the plan "
                                              "avoids adding health claims either way"],
            ["Can you legally buy THCA online?", "Not answered: a legal-status question that "
                                                 "needs the client's own compliance sign-off"],
        ]),
        Table(header=["Domain", "DR (Ahrefs)", "Note"], caption="SIMILAR SIZED COMPETITORS", rows=[
            ["plainjane.com", "46", "similar-size, ranks #1 for 'thca flower'"],
            ["greenunicornfarms.com", "33", "lower authority, #3 for 'thca flower'"],
            ["gold-spectrum.com", "27", "lower authority, #4"],
            ["avldispensary.com", "36", "lower authority, #6"],
            ["luckyelk.com", "27", "lower authority, #7"],
            ["blacktiecbd.net", "46", "similar-size, #9"],
            ["cbdhemp.direct", "35", "lower authority, #14"],
            ["kushqueen.shop", "51", "similar-size, #17"],
        ]),
        Table(header=["Domain(s)", "Why excluded"], caption="EXCLUDED FROM COMPARISON", rows=[
            ["webmd.com, youtube.com", "Editorial and video results, not retail competitors"],
            ["bulkthcasupply.com", "Wholesale supplier ('THCa Flower Wholesale | Pounds from "
                                   "$250'), a different buyer than this retail collection"],
            ["exhalewell.com", "Higher authority (DR 63, above this client's 56), not a "
                               "similar-size comparison"],
        ]),
        Paragraph(text="'thca flower' is a genuinely commercial SERP: dedicated THCA "
                       "category pages from independent hemp shops hold most of page 1, plus "
                       "a couple of editorial results and an AI overview. Competitors' "
                       "titles mostly lead with 'Buy / Order / Shop THCA Flower Online'. "
                       "Several lower-authority domains (DR 27 to 36) outrank this page's "
                       "56, so authority isn't the barrier; content quality, focus and "
                       "whatever caused the sitewide decline are the more likely factors. "
                       "Content-depth benchmark (measured 2026-09-23 on the collection "
                       "description copy): #1 plainjane.com ~1,280 words, #3 "
                       "greenunicornfarms.com ~690, #4 gold-spectrum.com ~160, #6 "
                       "avldispensary.com ~80, #7 luckyelk.com ~960, #9 blacktiecbd.net "
                       "~2,380, #14 cbdhemp.direct ~1,920, #15 25hourfarms.com ~300, #16 "
                       "exhalewell.com ~1,790, #17 kushqueen.shop ~235 (median ~825). "
                       "Length alone doesn't predict rank here, but the pages that carry "
                       "copy repeat the same topics: what THCA is, THCA vs THC and whether "
                       "it gets you high, how to choose, quality and growing, storage and "
                       "lab results. This client's page is ~1,275 words today, level with "
                       "the #1 result, which is why this plan fixes the copy in place "
                       "rather than cutting it hard."),
    ]

    # ---------------- Review analysis ----------------
    blocks += [
        H2(text="Review analysis"),
        Paragraph(text="We've downloaded as many of your reviews as we could find across all "
                       "platforms. For this page and related products, 1,929 reviews "
                       "matched — here are the relevant themes."),
        Note(text="1,929 reviews matched this collection, but 0 came from these 54 products "
                  "directly (matched instead by full-text search on 'thca flower' and 'thc "
                  "flower' across the whole store, the same pattern flagged on other "
                  "collections for this client). The themes below read as thematically "
                  "consistent with real flower purchases (effect, flavor, value, shipping), "
                  "so they are used with reasonable confidence, but they are not proven "
                  "page-specific."),
        Table(header=["Theme", "Count", "Example"], caption="TOP PRAISE", rows=[
            ["Performance", "1,132", "It smokes good I'm enjoying the effects"],
            ["Scent flavor", "370", "It smelled good and tasted good."],
            ["Quality", "327", "Really good flower definitely worth it"],
            ["Value", "143", "such a good deal"],
            ["Shipping", "58", "ships fast"],
        ]),
        Table(header=["Theme", "Count", "Example"], caption="TOP FRICTION", rows=[
            ["Performance", "35", "it takes awhile to kick in though"],
            ["Scent flavor", "24", "Not incredibly smooth or flavorful"],
            ["Quality", "15", "was little dry when arrived"],
            ["Assortment", "10", "wish still had it but it's gone.was wanting to try others "
                                 "ones also but all gone"],
            ["Value", "10", "price could come down a little to like $10-11/g IMO"],
            ["Accuracy as described", "9", "I dislike when the product name is misleading. "
                                           "Like when it's called a thca vape but its "
                                           "actually delta 8 or thcp."],
            ["Sizing fit", "7", "The nugs were much smaller than expected"],
        ]),
        Label(text="INTENTS"),
        Table(header=["Intent", "Count"], rows=[
            ["self_purchase", "441"], ["repurchase", "310"], ["first_time", "51"], ["gift", "15"],
        ]),
        Label(text="USE CASES"),
        Table(header=["Use case", "Count"], rows=[
            ["smoking flower", "100"], ["recreational use", "53"], ["personal use", "37"],
            ["getting high", "26"],
        ]),
        Label(text="ATTRIBUTE GAPS"),
        Table(header=["Signal", "Theme", "Count", "Note"], rows=[
            ["taste", "Scent flavor", "49", "Real flavor descriptors from the catalog "
                                            "(citrus, pine, gassy, nutty) can ground this, "
                                            "replacing generic 'rich aromas'"],
            ["price", "Value", "31", "Reviewers do praise value; the plan limits this to "
                                     "the page's existing 'competitive pricing' wording "
                                     "rather than price-led copy, per the client"],
            ["smooth", "Performance", "25", ""],
        ]),
        Label(text="CUSTOMER QUESTIONS"),
        Bullets(items=[
            "Does THCA cause a high? (paa)",
            "Can you legally buy THCA online? (paa)",
            "How long does it take for the product to kick in? (review)",
            "Are the nugs smaller than expected? (review)",
            "When will this product be back in stock? (review)",
        ]),
    ]

    # ---------------- Recommendations ----------------
    blocks += [
        H2(text="Recommendations"),
        Label(text="ENTITY EMPHASIS"),
        Bullets(items=[
            "Flavor descriptors already in the catalog but missing from the copy (citrus, "
            "pine, gassy, nutty) as concrete detail in the strains section.",
            "trichomes (9 products) as a single quality cue in the merged quality section.",
            "No vendor names in evergreen copy (the vendor mix rotates); Oregon and indoor "
            "only as 'select' / 'several' strains.",
        ]),
        Label(text="KEYWORD USAGE"),
        Bullets(items=[
            "Primary 'thca flower' (40,500/mo) is given by the client and confirmed by the "
            "SERP. The page ranks around position 87 for it in GSC, so the goal is a "
            "cleaner, more accurate page that keeps its depth: the copy tightens from about "
            "1,360 to about 900 words (about 1,215 with FAQs), in line with the top-ranking "
            "pages (median ~825, #1 ~1,280), instead of adding repetition. The phrase count "
            "falls from roughly 26 mentions to a natural handful.",
            "The title tag moves to 'THCA Flower for Sale | Shop THCA Online | E420'. It "
            "removes 'Buy Legal THC Flower Online' (the phrase legal-thc-flower now owns), "
            "keeps 'for sale', and puts 'thca online' (2,900/mo, the page's biggest "
            "historical query) in the title. Both are commercial, not explainer, in line "
            "with the client's standing preference.",
            "The meta description is a minimal edit: 'legal THCA flowers' becomes 'THCA "
            "flower' and everything else stays.",
            "Protected phrases: 'thca online', 'thca website', 'thca for sale' and 'buy "
            "thca flower online' must each survive the cleanup once in a normal sentence, "
            "because those query families earned this page its clicks before the decline. "
            "'thca shop' (3,600/mo) is added once; it appears nowhere in the copy today.",
            "H1 stays 'THCA Flower'. The FAQ heading changes from 'THCa Flower FAQS' to "
            "'THCA FAQs': it fixes the casing, avoids a third literal repeat of 'THCA "
            "Flower', keeps the format the client chose on thc-p-flower ('THCP FAQs'), and "
            "covers the broader THC / Delta / storage question mix.",
            "Nothing here targets 'legal thc flower' or 'thc flower': the client wants "
            "those on legal-thc-flower. The single existing link to that page stays as a "
            "cross-link.",
            "Per the client (2026-09-23), 'cheap' and cheap-style wording (budget, "
            "discount, bargain, deals) is not used or targeted, even though the products "
            "are lower priced. 'cheap thca flower' (720/mo) is left out of the "
            "secondaries; pricing appears only as the page's existing 'competitive "
            "pricing' idea, with no specific prices.",
        ]),
    ]

    blocks += _outline_blocks()
    blocks += _faq_blocks()
    blocks += _link_blocks()
    blocks += _writing_signal_blocks()

    # ---------------- Draft content ----------------
    blocks += [
        PageBreak(),
        H2(text="Draft content"),
        Paragraph(text="Word-level changes vs the live page, then paste-ready copy. "
                       "Strikeouts are removals; highlights are additions."),
    ]
    for diff_title, paste_key in DRAFT_MAP:
        _draft_section(blocks, diff_title, paste_key)
    blocks += [
        H3(text="FAQ ANSWERS"),
        H3(text="FAQ: What's the difference between THC, THCa, Delta 8, and Delta 9?"),
        Note(text="0 ADDED · 18 REMOVED"),
        Label(text="CHANGES"),
        DiffPara(runs=word_diff(FAQ1_OLD, FAQ1_NEW)),
        Label(text="PASTE-READY"),
        Paragraph(text=FAQ1_NEW),
        H3(text=f"FAQ: {FAQ_NEW_Q}", badge="NEW"),
        Note(text="NEW · 44 WORDS ADDED"),
        Label(text="CHANGES"),
        DiffPara(runs=word_diff("", FAQ_NEW_A)),
        Label(text="PASTE-READY"),
        Paragraph(text=FAQ_NEW_A),
    ]

    # ---------------- Sources ----------------
    blocks += [
        H2(text="Sources"),
        KVTable(pairs=[
            ["Products analysed", "54"],
            ["Reviews analysed", "1,929"],
        ]),
        Paragraph(text="Entities analysed: Smoke Nation, Emerald, Smak'd, Xhale, Numb, "
                       "Fuego, Citrus, sweet, pine, earthy, gassy, vanilla, Lemon, nutty, "
                       "Candy, THC-A Flower, Flower, Hybrid, nug, individually wrapped, "
                       "resealable jar, trichomes, Cannabinoids, 3.5 grams, Delta Flower, "
                       "3.5-gram, THC-A, THCa, Everything 420, jar, Fruity, Sweet vanilla, "
                       "Purple, high potency, terp profile, uplifting, bud, dense buds, "
                       "7 Grams, Red Runtz, Heat, Indoor, power, hemp flower, hemp-derived "
                       "THC-A, daytime sessions, indoor sessions, late-night sessions, main "
                       "event, session, 2 Gram, 4 gram, 4 grams, 4-gram, 8 grams, 3.5g, "
                       "Delta Warning, HempTHC, Sesh, White, 7g, crew, Bong Balls, citrusy, "
                       "0.5g, 2.5g, THC-A distillate, Exodus, Numb Cannabis Co., fruity "
                       "tones, load, THC-A crystals, daytime productivity, social hangs, "
                       "bud, butterscotch, 4g."),
        Note(text="Domain Rating by Ahrefs (https://ahrefs.com/)."),
    ]

    return PlanDocument(
        title="Page Plan",
        subtitle="thca flower",
        market_note="",
        blocks=blocks,
    )


def _outline_blocks():
    return [
        H2(text="Outline"),
        H3(text="intro", badge="IMPROVE"),
        Bullets(items=[
            "The existing headless lead is short and works, but its first sentence names "
            "'legal THC flower', the sibling legal-thc-flower's target phrase, and the "
            "first H2 then repeats both sentences almost verbatim. Swap that one phrase "
            "for THCA flower and leave the rest. The lead stays headless because it is "
            "already live copy directly under the grid.",
            "Edit: Phrase only. Placement: first sentence of the lead. Topics: replace "
            "'legal THC flower' with 'THCA flower'. Must keep: the second sentence ('Our "
            "premium flower offers a smooth and fun experience!'). Notes: about 22 words, "
            "same length as today. No other wording changes.",
        ]),
        H3(text="Buy THCA Flower Online (H2)", badge="IMPROVE"),
        Bullets(items=[
            "Fix in place. The first two sentences repeat the opening lead, and the rest "
            "is padded with slang ('skip the sketchy gas station weed', 'hands down', "
            "'ridiculously easy', 'thca website setup') and unsupported wording "
            "('farm-fresh'). Keep what works, including the exact phrases this page earns "
            "clicks from ('THCA online', 'THCA for sale online', 'THCA website'). Target "
            "about 105 words, down from 157.",
            "Edit: Rewrite section. Placement: rewrite in place.",
            "Topics: who Everything 420 is and what the range covers (indica, sativa and "
            "hybrid, lab-tested, shipped fast and discreetly); one natural mention each of "
            "'THCA online', 'THCA for sale online', 'THCA website' and 'THCA shop'; one "
            "soft 'looking for the best THCA flower online?' style mention; the existing "
            "pointer to legal THC flowers.",
            "Must keep: the heading; the link to /collections/legal-thc-flower (anchor "
            "'legal THC flowers'); 'you've landed in the right spot', 'handpicked "
            "selection' and 'restock whenever the jar runs low'; the phrases 'thca "
            "online', 'thca for sale' and 'thca website'.",
            "Notes: plain, commercial tone. No new legal-status, testing or 'every "
            "product' claims.",
        ]),
        H3(text="Why Shop THCA Flower at Everything 420 (H2)", badge="MERGE"),
        Bullets(items=[
            "Heading reword plus merge. 'Your Best Source for Premium THCA Flower Online' "
            "is a superlative claim, and 'Why Choose Everything420 for Your THCA Needs' "
            "(44 words of generic praise) says the same thing again. Combine them into one "
            "factual 'why shop here' section of about 80 to 90 words (from 139 combined): "
            "the real Top Shelf / Premium Shelf / Select Shelf range, trusted brands, and "
            "the shipping-only 'no need to search near me' line, which is accurate because "
            "the store has no local shops.",
            "Edit: Rewrite section. Placement: one section replacing this H2 and 'Why "
            "Choose Everything420'.",
            "Topics: variety (Top Shelf, Premium Shelf and Select Shelf strains in indica, "
            "sativa and hybrid, from trusted brands); 'no need to search for THCA flower "
            "near me' (ships straight to your door); real customer reviews and clear "
            "strain details on the product pages.",
            "Must keep: the 'easy to find, easy to order, and even easier to enjoy' line; "
            "the shipping-to-your-door point.",
            "Notes: target about 80 to 90 words. Don't repeat 'best THCA flower online' "
            "here; it appears once in the first H2.",
        ]),
        H3(text="THCA Strains: Indica, Sativa and Hybrid (H2)", badge="IMPROVE"),
        Bullets(items=[
            "Fix in place, with a heading reword: the current heading is a stuffed keyword "
            "list. The body names four strains that aren't in the catalog (Granddaddy "
            "Purple, Purple Punch, Jack Herer, Sour Diesel) and adds health-style claims "
            "('therapeutic potential', 'stress relief'). Keep the indica / sativa / hybrid "
            "explanation and add real flavor detail (competitors such as plainjane.com "
            "explain flavor terms too). Target about 110 words, close to today's 129.",
            "Edit: Rewrite section. Placement: rewrite in place.",
            "Topics: what indica, sativa and hybrid generally mean for the experience; "
            "real flavor descriptors from the catalog (citrus, pine, sweet vanilla, candy, "
            "earthy, nutty, gassy); one natural mention of 'thca buds'; a soft pointer for "
            "newcomers (a hybrid is a middle ground). Entities: citrus, pine, gassy.",
            "Must keep: 'Our diverse THCA strains cater to every preference'; the indica / "
            "sativa / hybrid distinction; 'traditional and modern genetics'.",
            "Notes: if a named example is wanted, take one or two from the live grid at "
            "drafting time and mark them as easy-to-refresh, because strains rotate.",
        ]),
        H3(text="THC-A Flower Quality and Lab Testing (H2)", badge="IMPROVE"),
        Bullets(items=[
            "Fix in place. Keep the heading (it holds the hyphenated 'THC-A flower' "
            "variant, 2,400/mo as 'thc a flower') and keep the lab-testing claim, worded "
            "once. Remove what the catalog doesn't support: 'certified organic farms', "
            "'thousands trust', 'awesome thca benefits' and the '20-35% THCA' range "
            "(listed product-page values are 32.5% to 37.0%). Add the checkable quality "
            "cues the catalog does support. Target about 115 words, close to today's 104.",
            "Edit: Rewrite section. Placement: rewrite in place.",
            "Topics: lab testing, stated once (cannabinoid content, pesticides, "
            "microbials); THCA percentages listed on product pages where available; "
            "trichomes as a visible quality cue; customer reviews as a check on flavor and "
            "freshness; link to Legal THC products. Entities: trichomes.",
            "Must keep: the heading; the link to /collections/hemp-thc (anchor 'thc-a "
            "hemp products'); the lab-testing claim, worded once.",
            "Notes: avoid new 'every product' testing wording until the client confirms "
            "it.",
        ]),
        H3(text="THCA Flower Sizes and Shipping (H2)", badge="IMPROVE"),
        Bullets(items=[
            "Heading reword plus fix in place: 'Premium Online THCa Flower Shopping "
            "Experience with Competitive Pricing' is bloated. The body's 'from 1g samples' "
            "is wrong (the smallest jar is 2g; sizes are 2g, 3.5g, 7g, 14g and 28g) and "
            "'perfect for every budget' is price-led wording the client wants avoided. "
            "Keep the shipping and customer-service points and the existing 'competitive "
            "pricing' idea, with no specific prices. Target about 75 words, close to "
            "today's 93.",
            "Edit: Rewrite section. Placement: rewrite in place.",
            "Topics: sizes from 2g up to 28g; fast, discreet shipping, with free shipping "
            "on select products; customer service can help pick a variety; one neutral "
            "'competitive pricing' line (no prices, no 'cheap', 'budget' or 'discount' "
            "wording).",
            "Must keep: 'Fast, discreet shipping ensures your THCA flower arrives fresh "
            "and secure'; the customer service point.",
            "Notes: sizes should read as refreshable, not permanent (on 2026-09-23 the "
            "range is 2g to 28g).",
        ]),
        H3(text="More THCA Products to Explore (H2)", badge="IMPROVE"),
        Bullets(items=[
            "Heading reword plus fix in place. The section carries two working links "
            "(THCA beverages, THCA products) and one dead one (CBD, a 404 that comes out), "
            "so it stays as the page's 'related products' block, trimmed from 92 to about "
            "50 words. It drops 'exclusive Runtz THCA phenotypes' (only one product is "
            "from the Runtz vendor), 'budget-conscious customers', 'comprehensive wellness "
            "solutions' and 'These cannabis alternatives bring serious heat'.",
            "Edit: Rewrite section. Placement: rewrite in place.",
            "Topics: THCA beverages as a way to enjoy THCA without smoking; the rotating "
            "selection of strains; pointer to the full THCA products range and to the "
            "delta and CBD lines.",
            "Must keep: the links 'THCA beverages' (/collections/legal-drinks) and 'THCA "
            "products' (/collections/thc-a-products); 'CBD product lines' stays as plain "
            "text (its /collections/cbd link is removed, a 404).",
            "Notes: target about 50 words. Keep the two link anchors verbatim.",
        ]),
        H3(text="Why Choose Everything420 for Your THCA Needs (H2)", badge="MERGE"),
        Bullets(items=[
            "Folded into 'Why Shop THCA Flower at Everything 420' above; its 44 words are "
            "generic superlatives with nothing checkable, and the 'trusted brands' idea "
            "carries over.",
        ]),
        H3(text="THCA Small Buds: Big Value, Same Fire (H2)", badge="REMOVE"),
        Bullets(items=[
            "The one section cut outright, pending client confirmation (118 words). No "
            "small-buds product exists in the catalog (0 of 54 titles, variants, "
            "descriptions or tags mention small buds or smalls), so it promotes something "
            "shoppers can't buy from this page, it leans on 'value' framing the client "
            "wants avoided, and 7 reviews already complain that nugs were smaller than "
            "expected. If small buds are sold or planned, keep a rewritten version "
            "instead; the related query 'thca flower smalls' (260/mo) isn't served today.",
        ]),
        H3(text="Where and How Our THCA Flower Is Grown (H2)", badge="MERGE"),
        Bullets(items=[
            "Heading reword plus merge. The organic / sustainable section and the indoor "
            "section overlap, and the first makes claims the catalog doesn't support "
            "(organic, regenerative, sungrown, outdoor, greenhouse: 0 products). "
            "Competitors such as luckyelk.com, blacktiecbd.net and cbdhemp.direct all "
            "carry a cultivation section, so keep one, rewritten around what the catalog "
            "does support: 'Grown in Oregon' on select strains (21 products) and indoor "
            "cultivation on several (9). Target about 120 words, from 240 combined.",
            "Edit: Rewrite section. Placement: one section replacing this H2 and the "
            "indoor H2.",
            "Topics: select strains grown in Oregon; several grown indoors; what indoor "
            "cultivation controls (light, temperature, humidity, nutrients) and why it "
            "helps consistency; flavor detail (sweet vanilla, gas-forward funk, fruity "
            "aromatics); consistency from jar to jar, one reason customers reorder "
            "favorites.",
            "Must keep: the indoor-cultivation explanation (control of light, temperature, "
            "humidity and nutrients); the dense trichome coverage and terpene profile "
            "points.",
            "Notes: say 'select strains' and 'several strains', never the whole range "
            "(Oregon is 21 of 54 products, indoor 9). Growing details beyond the catalog "
            "need client confirmation.",
        ]),
        H3(text="Indoor THCA Flower: Controlled Chaos, Maximum Potency (H2)", badge="MERGE"),
        Bullets(items=[
            "Folded into 'Where and How Our THCA Flower Is Grown' above; the "
            "indoor-cultivation explanation carries over, the slang and the unverifiable "
            "maturity claim do not.",
        ]),
        H3(text="Understanding THCA Vs. THC: What You're Actually Smoking (H2)", badge="IMPROVE"),
        Bullets(items=[
            "Fix in place instead of cutting. Five of the six content-heavy competitors "
            "carry a 'what is THCA / THCA vs THC' section, so this stays. Trim slang "
            "('boom', 'vibing through a creative session') and drop the 'legal pathway "
            "under the 2018 Farm Bill' sentence, a legal-status claim that needs the "
            "client's sign-off before it appears in rewritten copy (it can be restored "
            "verbatim if approved). Target about 90 words, down from 125.",
            "Edit: Rewrite section. Placement: rewrite in place.",
            "Topics: THCA is the non-psychoactive precursor to THC; heat (smoking or "
            "vaping) converts it via decarboxylation; lab reports show the THCA amount in "
            "each strain, so shoppers can gauge potential potency.",
            "Must keep: the heading; 'Let's clear the haze' opener; the link to "
            "/collections/delta-9-products (anchor 'delta 9'); the lab-reports sentence.",
        ]),
        H3(text="How to Order THCA Flower Online (H2)", badge="IMPROVE"),
        Bullets(items=[
            "Heading reword plus fix in place: the current heading repeats 'Buy THCA "
            "Flower Online' from the first H2, so this one moves to 'Order' ('thca order "
            "online' is a real variant, 140/mo). Keep the scannable four-step list and the "
            "strain-type guidance. Fix the wrong size ('from grams to bulk options' becomes "
            "2g up to 28g), and drop the Granddaddy Purple example and 'federally "
            "compliant' (legal-status wording) and 'no sketchy surprises'. Target about 130 "
            "words, close to today's 145.",
            "Edit: Rewrite section. Placement: rewrite in place.",
            "Topics: the four-step list (check the lab report, match the strain type, pick "
            "a size, add to cart); indica for winding down, sativa for daytime, hybrid in "
            "between; clear descriptions, real reviews, discreet shipping to your door.",
            "Must keep: the four-step list; 'skip the dispensary line and keep things "
            "simple'; the phrases 'buy thca flower online' and 'thca indica'.",
            "Notes: sizes should read as refreshable, not permanent.",
        ]),
    ]


def _faq_blocks():
    return [
        H2(text="FAQs"),
        H3(text="KEEP — What is THCA flower and THC-A flower?"),
        Bullets(items=[
            "Left untouched for now. The answer says the products are 'federally legal "
            "under the 2018 Farm Bill'. That legal-status wording needs the client's own "
            "compliance review before it stays, changes or is repeated anywhere in new "
            "copy.",
        ]),
        H3(text="KEEP — How do I choose between indica, sativa, and hybrid THCA strains?"),
        Bullets(items=["Keep as written."]),
        H3(text="KEEP — Are your THCA flower products lab-tested for quality?"),
        Bullets(items=[
            "Left untouched for now, but flagged for the client to verify. The answer says "
            "every product has third-party testing for heavy metals and that lab reports "
            "exist for each strain; only 2 of 54 product descriptions mention lab results "
            "and none mention a COA or third-party testing (reports may be linked "
            "elsewhere on the product pages).",
        ]),
        H3(text="REMOVE — What's the difference between THCA flower and THCA shake?"),
        Bullets(items=[
            "Cut (about 60 words). It answers a question about THCA shake, which isn't "
            "sold in this collection (0 of 54 products), so it sets up a product shoppers "
            "can't buy here.",
        ]),
        H3(text="REMOVE — Do you offer organic THCA flower options?"),
        Bullets(items=[
            "Cut (about 55 words). 'Organic' isn't supported anywhere in the catalog data "
            "(0 of 54 products mention it) and reads as a certification-style claim. If "
            "some products are certified organic, the client can supply proof and this can "
            "return as a corrected FAQ.",
        ]),
        H3(text="KEEP — How should I store my THCA flower to maintain quality?"),
        Bullets(items=["Keep as written."]),
        H3(text="REMOVE — What makes your THCA strains special compared to other products?"),
        Bullets(items=[
            "Cut (about 60 words). Generic and duplicative ('classic genetics with modern "
            "cultivation techniques', 'best of thca cultivation'); the strains and quality "
            "sections already cover what's real.",
        ]),
        H3(text="IMPROVE — What's the difference between THC, THCa, Delta 8, and Delta 9?"),
        Bullets(items=[
            "Trim only: cut the final sentence ('You don't have to stress about a weird "
            "thca side effect when you know exactly what you're puffing!'). It reads as a "
            "health reassurance and adds a stuffed 'thca side effect' phrase. About 18 "
            "words go; everything before it stays word for word.",
        ]),
        H3(text="ADD — Does THCA flower get you high?", badge="ADD"),
        Bullets(items=[
            "New. Adds the SERP's first People Also Ask question ('Does THCA cause a "
            "high?') as a direct, scannable answer that complements the THCA vs THC "
            "section. One paragraph; keep to chemistry and effects (raw THCA is "
            "non-psychoactive; heating converts it to THC, which produces the effects; "
            "effects vary by person, start low if new); no legal-status claims; stay "
            "consistent with FAQ 1.",
        ]),
    ]


def _link_blocks():
    return [
        H2(text="Recommended internal links"),
        Note(text="Anchor text will appear verbatim in the drafted copy for outbound links "
                  "once drafts are written; an inbound link is an edit for the other page "
                  "listed, not something this plan drafts. Links marked 'Remove link' are "
                  "in the live copy today and should come out (the drafted copy leaves "
                  "them out)."),
        Table(header=["Anchor", "Links to", "Placement", "Why"], rows=[
            ["legal THC flowers", "/collections/legal-thc-flower", "Buy THCA Flower Online",
             "existing link, stays in this section"],
            ["THC-A hemp products", "/collections/all-legal-thc", "THC-A Flower Quality "
             "and Lab Testing", "fix: the live link goes to /collections/hemp-thc, which "
             "301-redirects; link the final URL (same anchor)"],
            ["THCA beverages", "/collections/legal-drinks", "More THCA Products to Explore",
             "existing link, stays in this section"],
            ["THCA products", "/collections/thc-a-products", "More THCA Products to Explore",
             "existing link, stays in this section"],
            ["CBD product lines", "(remove link, words stay as plain text)",
             "More THCA Products to Explore", "the target /collections/cbd is a 404; the "
             "store still sells CBD products, so the sentence stays as plain text"],
            ["delta 9", "/collections/delta-9-products", "Understanding THCA Vs. THC",
             "existing link, stays in this section"],
        ]),
    ]


def _writing_signal_blocks():
    return [
        H2(text="Writing signals"),
        Note(text="1,929 reviews matched this collection, but 0 came from these 54 products "
                  "directly (matched by full-text search on 'thca flower' and 'thc flower' "
                  "across the whole store). The themes read as thematically consistent "
                  "with real flower purchases (effect, flavor, value, shipping) and are "
                  "used with reasonable confidence, but they are not proven "
                  "page-specific."),
    ]
