"""Frozen section order, from the client-approved sample plan.

Every plan document follows this section sequence. Renderers and the
review UI rely on it; do not reorder without a template version bump.
"""

TEMPLATE_VERSION = "1.0"

SECTION_ORDER = [
    "page_details",
    "subheadings",
    "internal_links",
    "current_performance",
    "onpage_issues",
    "entity_research",
    "keyword_research",
    "serp_analysis",
    "review_analysis",
    "recommendations",
    "outline",
    "faqs",
    "recommended_internal_links",
    "draft_content",
    "sources",
]
