"""DataForSEO client — only the endpoints the plan uses.

Per page plan, caps at: 1x keywords volumes, 1x SERP, 1x labs related.
Domain Analytics / App Data deliberately excluded; Content Analysis and
On-Page reserved for competitor-depth and parsing fallbacks.
"""
import os

import requests

BASE = "https://api.dataforseo.com/v3"
LOCATION = "United States"
LANGUAGE = "en"


class DataForSEOClient:
    def __init__(self, login: str | None = None, password: str | None = None):
        self.auth = (login or os.environ.get("DATAFORSEO_LOGIN", ""),
                     password or os.environ.get("DATAFORSEO_PASSWORD", ""))

    def _post(self, path: str, payload: list[dict]) -> tuple[dict, list]:
        r = requests.post(f"{BASE}{path}", auth=self.auth, json=payload, timeout=60)
        r.raise_for_status()
        body = r.json()
        if body.get("status_code") != 20000:
            raise RuntimeError(f"DataForSEO {path}: {body.get('status_message')}")
        task = body["tasks"][0]
        results = task.get("result") or []
        return (results[0] if results else {}), results

    def serp(self, query: str, depth: int = 10) -> dict:
        """Organic results + People Also Ask, merged."""
        res, _ = self._post("/serp/google/organic/live/regular", [{
            "keyword": query, "location_code": 2840, "language_code": "en",
            "depth": depth, "people_also_ask": True,
        }])
        items = res.get("items") or []
        organic = [{"rank": i.get("rank_group"), "url": i.get("url"),
                    "title": i.get("title"), "domain": i.get("domain"),
                    "description": i.get("description"), "type": i.get("type")}
                   for i in items if i.get("type") == "organic"]
        paa = [{"question": i.get("title"), "answers": len(i.get("items") or [])}
               for i in items if i.get("type") == "people_also_ask"]
        return {"query": query, "organic": organic, "paa": paa}

    def volumes(self, keywords: list[str]) -> dict:
        _, rows = self._post("/keywords_data/google_ads/search_volume/live", [{
            "keywords": keywords[:1000], "location_code": 2840, "language_code": "en",
        }])
        out = {}
        for row in rows:
            out[(row.get("keyword") or "").lower()] = {
                "volume": row.get("search_volume", 0),
                "cpc": row.get("cpc"),
                "competition": row.get("competition"),
                "competition_index": row.get("competition_index"),
            }
        return out

    def related_keywords(self, query: str, limit: int = 30) -> list[dict]:
        res, _ = self._post("/dataforseo_labs/google/related_keywords/live", [{
            "keyword": query, "location_code": 2840, "language_code": "en",
            "limit": limit,
        }])
        items = res.get("items") or []
        out = []
        seen = set()
        for i in items:
            for kw in i.get("related_keywords") or []:
                if kw and kw.lower() not in seen:
                    seen.add(kw.lower())
                    out.append({"keyword": kw, "volume": None})
        return out[:limit]
