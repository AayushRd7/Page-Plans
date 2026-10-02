"""OpenRouter client + the drafting prompt.

The humanizer rules from the uploaded skill sit in the system layer as
hard constraints, not suggestions — the draft comes back already
de-AI-ed so the diff stage isn't laundering slop.
"""
import json
import os

import requests

HUMANIZER_RULES = """You are an SEO copywriter for ecommerce collection pages, writing under a strict house style.

HARD STYLE RULES (violations get the draft rejected):
- No em dashes. Use commas, periods, or parentheses.
- No rule-of-three lists ("fast, discreet, and reliable" style stacking).
- No AI vocabulary: delve, leverage, elevate, unlock, supercharge, landscape, testament, journey, vibrant, rich tapestry, in today's world.
- No promotional filler ("premium quality", "top-notch", "world-class") — state facts instead.
- No negative parallelisms ("It's not just X, it's Y").
- Vary sentence length on purpose. One short sentence. Then a longer one that earns its length.
- No vague attributions ("experts agree", "studies show") — name the thing or drop the claim.
- Have a point of view where the brand allows it; acknowledge tradeoffs honestly.
- First paragraph must answer the query directly, not warm up to it.

LEGAL/HEALTH CLAIMS RULE (hemp/CBD clients): never claim medical benefits, cures, or FDA endorsement. Use "may", comply-style hedging only where true. Hemp products must be described as hemp with compliant language. Flag any sentence you were unsure about in a "claim_flags" array instead of shipping it silently."""


def chat(messages: list[dict], model: str | None = None,
         api_key: str | None = None, max_tokens: int = 16384,
         response_format: dict | None = None) -> str:
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    model = model or os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "messages": messages,
                            "max_tokens": max_tokens,
                            "reasoning": {"max_tokens": 1500},
                            **({"response_format": response_format} if response_format else {})},
                      timeout=300)
    r.raise_for_status()
    payload = r.json()
    choice = payload["choices"][0]
    content = choice["message"].get("content")
    if content is None:
        raise RuntimeError(
            f"model returned empty content (finish={choice.get('finish_reason')}, "
            f"usage={payload.get('usage')})")
    return content


def draft_collection_copy(brief: dict) -> dict:
    """brief: {query, collection_title, catalog_facts, audit_fixes, outline, examples}
    returns parsed JSON draft."""
    user = f"""Write paste-ready collection page copy for a {brief['platform']} store.

TARGET QUERY: {brief['query']}
COLLECTION: {brief['collection_title']}

VERIFIED CATALOG FACTS (use only these — no invented strains, prices, or sizes):
{json.dumps(brief['catalog_facts'], indent=1)}

AUDIT FIXES THE COPY MUST RESOLVE:
{json.dumps(brief['audit_fixes'], indent=1)}

DECIDED OUTLINE:
{json.dumps(brief['outline'], indent=1)}

Return ONLY JSON with keys:
- "title": 50-60 chars, query near front, not identical to the h1
- "meta_description": 150-160 chars, different angle from title
- "h1": contains the query
- "intro": 80-120 words, first sentence answers "{brief['query']}?"
- "sections": object keyed by outline heading -> 60-120 words each
- "faqs": array of 4-8 objects {{"q": ..., "a": 40-80 words}}
- "claim_flags": array of strings, may be empty"""
    raw = chat([{"role": "system", "content": HUMANIZER_RULES},
                {"role": "user", "content": user}])
    return _extract_json(raw)


def _extract_json(raw: str) -> dict:
    """Models love leading whitespace, preamble, or markdown fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.index("\n") + 1:] if "\n" in raw else raw
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {raw[:120]!r}")
    return json.loads(raw[start:end + 1])
