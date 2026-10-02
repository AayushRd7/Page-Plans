"""Parse a page's HTML into an audit snapshot.

Everything the 8-dimension checklist needs, collected once at crawl time
and shared by the audit stage, the pre-publish gate, and the page plan.
"""
import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bs4 import BeautifulSoup

MODERN_IMG = (".webp", ".avif")
BAD_ANCHORS = {"click here", "learn more", "read more", "here"}


@dataclass
class PageSnapshot:
    url: str
    slug: str = ""
    title: str = ""
    meta_desc: str = ""
    h1s: list[str] = field(default_factory=list)
    headings: list[tuple[int, str]] = field(default_factory=list)  # (level, text)
    body_text: str = ""
    word_count: int = 0
    first_paragraph: str = ""
    images: list[dict] = field(default_factory=list)  # src, alt, has_dims, lazy
    internal_links: list[dict] = field(default_factory=list)  # href, anchor
    external_link_count: int = 0
    schema_types: list[str] = field(default_factory=list)
    has_breadcrumb_schema: bool = False


def snapshot_from_html(html: str, url: str) -> PageSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    parsed = urlparse(url)
    snap = PageSnapshot(url=url, slug=parsed.path.strip("/").split("/")[-1] or "/")

    t = soup.find("title")
    snap.title = t.get_text(strip=True) if t else ""
    md = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    snap.meta_desc = (md.get("content") or "").strip() if md else ""

    for h in soup.find_all(re.compile("^h[1-6]$")):
        level = int(h.name[1])
        text = h.get_text(" ", strip=True)
        if level == 1:
            snap.h1s.append(text)
        snap.headings.append((level, text))

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or script.get_text() or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if "@graph" in item:
                items.extend(item.pop("@graph"))
            t_ = item.get("@type") if isinstance(item, dict) else None
            if t_:
                types = t_ if isinstance(t_, list) else [t_]
                snap.schema_types.extend(str(x) for x in types)
                if "BreadcrumbList" in types:
                    snap.has_breadcrumb_schema = True

    host = parsed.netloc
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].split("#")[0]
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        if urlparse(href).netloc not in ("", host):
            snap.external_link_count += 1
            continue
        anchor = a.get_text(" ", strip=True)
        key = (href, anchor)
        if key in seen:
            continue
        seen.add(key)
        snap.internal_links.append({"href": href, "anchor": anchor})

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        snap.images.append({
            "src": src,
            "alt": img.get("alt"),
            "has_dims": bool(img.get("width") and img.get("height")),
            "lazy": (img.get("loading") == "lazy") or ("lazy" in (img.get("class") or [])),
            "modern": src.lower().split("?")[0].endswith(MODERN_IMG),
        })

    for bad in soup(["script", "style", "noscript"]):
        bad.decompose()
    body = soup.body or soup
    snap.body_text = " ".join(body.get_text(" ", strip=True).split())
    snap.word_count = len(snap.body_text.split())
    p = (body.find("p") or body).get_text(" ", strip=True) if body else ""
    snap.first_paragraph = p
    return snap
