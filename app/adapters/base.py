"""Store adapters: any platform -> one Catalog schema.

Detection order: Shopify markers -> WooCommerce markers -> generic crawl.
Each adapter only has to fill the Catalog; the pipeline never cares
which platform the client runs.
"""
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class Product:
    handle: str
    title: str
    vendor: str = ""
    price_min: float = 0.0
    price_max: float = 0.0
    grams: list[float] = field(default_factory=list)   # variant sizes in g
    tags: list[str] = field(default_factory=list)
    available: bool = True


@dataclass
class Catalog:
    platform: str
    collection_title: str
    collection_handle: str
    products: list[Product] = field(default_factory=list)
    source: str = "json"   # json | crawl-grid | store-wide-json

    @property
    def price_range(self) -> tuple[float, float]:
        prices = [p for prod in self.products for p in (prod.price_min, prod.price_max) if p]
        return (min(prices), max(prices)) if prices else (0.0, 0.0)

    def gram_sizes(self) -> list[float]:
        sizes = sorted({g for prod in self.products for g in prod.grams})
        return sizes


def detect_platform(url: str, html: str) -> str:
    if "myshopify.com" in url or re.search(r"cdn\.shopify\.com|Shopify\.theme|/collections/[\w-]+/products", html or ""):
        return "shopify"
    if re.search(r"wp-content|woocommerce|wc-cart|/wp-json/", html or ""):
        return "woocommerce"
    return "crawl"


def get_adapter(platform: str):
    if platform == "shopify":
        from app.adapters.shopify import ShopifyAdapter
        return ShopifyAdapter()
    if platform == "woocommerce":
        from app.adapters.woocommerce import WooCommerceAdapter
        return WooCommerceAdapter()
    from app.adapters.crawl import CrawlAdapter
    return CrawlAdapter()


def collection_handle_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    m = re.search(r"collections/([\w-]+)", path)
    return m.group(1) if m else path.split("/")[-1] or "home"


_GRAM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(g|gram|grams)\b", re.I)


def extract_grams(title: str, variant_titles: list[str]) -> list[float]:
    grams = set()
    for text in [title, *variant_titles]:
        for m in _GRAM_RE.finditer(text or ""):
            grams.add(float(m.group(1)))
    return sorted(grams)
