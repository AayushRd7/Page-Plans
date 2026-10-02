"""Universal fallback: parse product cards out of the collection HTML."""
import re

from app.adapters.base import Catalog, Product, collection_handle_from_url

_PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d{2})?)")


class CrawlAdapter:
    platform = "crawl"

    def fetch_collection(self, url: str, html: str = "") -> Catalog:
        from bs4 import BeautifulSoup
        handle = collection_handle_from_url(url)
        title = handle.replace("-", " ").title()
        products: dict[str, Product] = {}
        soup = BeautifulSoup(html or "", "html.parser")
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True)

        seen = set()
        for a in soup.find_all("a", href=re.compile(r"/products?/[\w-]+")):
            href = a["href"].split("#")[0].split("?")[0]
            if href in seen:
                continue
            seen.add(href)
            card = a.find_parent(["li", "article", "div"])
            text = card.get_text(" ", strip=True)[:300] if card else a.get_text(" ", strip=True)
            name_el = a.find(class_=re.compile("title|name", re.I)) if card else None
            name = name_el.get_text(strip=True) if name_el else a.get_text(" ", strip=True)[:80]
            prices = [float(m) for m in _PRICE_RE.findall(text)]
            slug = href.rstrip("/").split("/")[-1]
            products[slug] = Product(
                handle=slug, title=name,
                price_min=min(prices) if prices else 0.0,
                price_max=max(prices) if prices else 0.0,
            )
        return Catalog(platform=self.platform, collection_title=title,
                       collection_handle=handle, products=list(products.values()))
