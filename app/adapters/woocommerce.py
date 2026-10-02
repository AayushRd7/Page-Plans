"""WooCommerce via the public Store API (no consumer keys needed)."""
from urllib.parse import urlparse

from app.adapters.base import Catalog, Product, collection_handle_from_url, extract_grams
from app.fetch import fetch_json


class WooCommerceAdapter:
    platform = "woocommerce"

    def fetch_collection(self, url: str, html: str = "") -> Catalog:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        handle = collection_handle_from_url(url)
        api = f"{base}/wp-json/wc/store/v1"

        title, category_id = handle.replace("-", " ").title(), None
        status, _, data = fetch_json(f"{api}/products/categories?slug={handle}")
        if status == 200 and isinstance(data, list) and data:
            category_id = data[0].get("id")
            title = data[0].get("name") or title

        query = f"{api}/products?per_page=100"
        if category_id:
            query += f"&category={category_id}"
        status, _, data = fetch_json(query)
        products = []
        if status == 200 and isinstance(data, list):
            products = [self._norm(p) for p in data]
        return Catalog(platform=self.platform, collection_title=title,
                       collection_handle=handle, products=products)

    @staticmethod
    def _norm(p: dict) -> Product:
        prices = [float(v["price"]) for v in p.get("variations", [])
                  if isinstance(v.get("price"), (int, float, str)) and v.get("price") not in (None, "")]
        if not prices and p.get("prices", {}).get("price"):
            prices = [float(p["prices"]["price"]) / 100]
        grams = extract_grams(p.get("name", ""),
                              [str(v.get("attributes", "")) for v in p.get("variations", [])])
        return Product(
            handle=p.get("slug", ""),
            title=p.get("name", ""),
            vendor="",
            price_min=min(prices) if prices else 0.0,
            price_max=max(prices) if prices else 0.0,
            grams=grams,
            tags=[t.get("name", "") for t in p.get("tags", []) if isinstance(t, dict)],
            available=p.get("is_in_stock", True),
        )
