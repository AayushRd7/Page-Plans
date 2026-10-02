"""Ahrefs free Domain Rating endpoint (APIv3 public).

Free tier: no credit cost, but reports must carry the attribution
"Domain Rating by Ahrefs" + https://ahrefs.com link. Paid endpoints stay
out of scope until there's a budget line for them.
"""
import os
from urllib.parse import urlparse

import requests

ATTRIBUTION = 'Domain Rating by Ahrefs (https://ahrefs.com)'


def domain_rating(url: str, token: str | None = None) -> dict:
    token = token or os.environ.get("AHREFS_TOKEN", "")
    domain = urlparse(url).netloc or url
    r = requests.get("https://api.ahrefs.com/v3/public/domain-rating-free",
                     params={"target": domain},
                     headers={"Authorization": f"Bearer {token}"}, timeout=20)
    r.raise_for_status()
    data = r.json()
    dr = data.get("domain_rating")
    if isinstance(dr, dict):
        dr = dr.get("domain_rating")
    return {"domain": domain, "dr": dr, "attribution": ATTRIBUTION}
