"""Shopify public JSON endpoints — no Admin token needed for read-only
catalog data on most themes. Falls back to full-catalog scan when the
per-collection endpoint is unavailable.
"""
from urllib.parse import urlparse

from app.adapters.base import Catalog, Product, collection_handle_from_url, extract_grams
from app.fetch import fetch_json


class ShopifyAdapter:
    platform = "shopify"

    def fetch_collection(self, url: str, html: str = "") -> Catalog:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        handle = collection_handle_from_url(url)

        status, _, data = fetch_json(f"{base}/collections/{handle}.json")
        title = handle.replace("-", " ").title()
        products = []
        if status == 200 and data and "collection" in data:
            title = data["collection"].get("title") or title

        store_wide, source = False, "json"
        status, _, data = fetch_json(f"{base}/collections/{handle}/products.json?limit=250")
        if status != 200 or not data or "products" not in data:
            data = None
            if html:
                # JSON blocked/rate-limited: parse the rendered collection
                # grid, following ?page=N pagination until it runs dry
                from app.adapters.crawl import CrawlAdapter
                from app.fetch import fetch_text
                products = CrawlAdapter().fetch_collection(url, html).products
                if products:
                    source = "crawl-grid"
                    seen = {p.handle for p in products}
                    for n in range(2, 6):
                        sep = "&" if "?" in url else "?"
                        s2, _, html_n = fetch_text(f"{url}{sep}page={n}")
                        batch = CrawlAdapter().fetch_collection(url, html_n or "").products
                        fresh = [p for p in batch if p.handle not in seen]
                        if not fresh:
                            break
                        seen.update(p.handle for p in fresh)
                        products.extend(fresh)
            if not products:
                # last resort: whole-store catalog (flagged, not collection-scoped)
                status, _, data = fetch_json(f"{base}/products.json?limit=250")
                store_wide = status == 200 and bool(data)
                if store_wide:
                    source = "store-wide-json"
        if data and data.get("products"):
            products = [self._norm(p) for p in data["products"]]
        cat = Catalog(platform=self.platform, collection_title=title,
                      collection_handle=handle, products=products, source=source)
        if store_wide:
            cat.collection_title += " (store-wide fallback)"
        return cat

    @staticmethod
    def _norm(p: dict) -> Product:
        variants = p.get("variants", [])
        prices = [float(v["price"]) for v in variants if v.get("price")]
        vt = [v.get("title", "") for v in variants]
        grams = extract_grams(p.get("title", ""), vt)
        grams = grams or ([0.0] if not vt else [])
        return Product(
            handle=p.get("handle", ""),
            title=p.get("title", ""),
            vendor=p.get("vendor", ""),
            price_min=min(prices) if prices else 0.0,
            price_max=max(prices) if prices else 0.0,
            grams=[g for g in grams if g],
            tags=p.get("tags", []) if isinstance(p.get("tags"), list) else
                 [t.strip() for t in str(p.get("tags", "")).split(",") if t.strip()],
            available=any(v.get("available", True) for v in variants) if variants else True,
        )
