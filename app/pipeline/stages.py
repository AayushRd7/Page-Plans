"""Pipeline skeleton: one state machine, tiers as gate configs.

A run is a row in Postgres; each stage is a job in the queue. A stage
finishes by writing its JSON artifact to disk and marking itself done.
A gate stage ends in WAITING_INPUT instead, and resumes when a human
answer arrives. Tier 1/2/3 are the same pipeline with different gates
open: never three flows.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"   # gate open, human answer required
    DONE = "done"
    SKIPPED = "skipped"               # e.g. no review feed for this store
    FAILED = "failed"
    OUTCOME = "outcome"               # terminal: preflight result, plan halted


class Outcome(str, Enum):
    OK = "ok"
    REDIRECT = "redirect"             # followed chain, notes final URL
    NOT_FOUND = "not_found"           # 404: emits link-cleanup report instead
    NOT_A_COLLECTION = "not_a_collection"
    EMPTY_COLLECTION = "empty_collection"
    DRAFT_HIDDEN = "draft_hidden"
    INACCESSIBLE = "inaccessible"
    UNKNOWN_DOMAIN = "unknown_domain"


@dataclass(frozen=True)
class Stage:
    id: str
    title: str
    reads: tuple[str, ...]        # artifact ids consumed
    writes: str                   # artifact id produced
    gate: bool = False            # can pause for human input
    paid: bool = False            # makes paid API calls (cost cap accounting)

    def __repr__(self) -> str:  # keep frozen dataclass hashable & readable
        return f"Stage({self.id})"


STAGES: tuple[Stage, ...] = (
    Stage("preflight", "URL validation", (), "preflight", gate=False),
    Stage("crawl", "Live page copy + internal links", ("preflight",), "crawl"),
    Stage("audit", "8-dimension on-page audit", ("crawl",), "audit"),
    Stage("catalog", "Store catalog via adapter", ("preflight",), "catalog"),
    Stage("gsc", "Search Console performance", ("preflight",), "gsc", paid=False),
    Stage("keywords", "Keyword volumes + secondaries", ("gsc", "catalog"), "keywords", gate=True, paid=True),
    Stage("serp", "SERP + PAA + competitor depth", ("keywords",), "serp", paid=True),
    Stage("reviews", "Review themes", ("catalog",), "reviews", gate=False),
    Stage("entities", "Entity extraction from catalog", ("catalog",), "entities"),
    Stage("analysis", "Outline + FAQ + link decisions", ("crawl", "catalog", "gsc", "keywords", "serp", "reviews", "entities"), "analysis", gate=True),
    Stage("drafting", "Paste-ready rewrites", ("analysis", "crawl", "audit"), "draft", gate=True),
    Stage("diff", "Word-level change diff", ("draft", "crawl"), "diffblocks"),
    Stage("render", "DOCX + PDF + paste-ready TXT", ("diffblocks",), "report"),
)

# Gates open per tier. "claims" is checked inside drafting: legal/health
# claims register requires acknowledgment in every tier.
TIERS: dict[str, frozenset[str]] = {
    "hands_off": frozenset(),
    "partial": frozenset({"keywords", "analysis", "drafting"}),
    "pro": frozenset(s.id for s in STAGES if s.gate),
}


@dataclass
class RunState:
    stage: str = "preflight"
    status: StageStatus = StageStatus.PENDING
    tier: str = "hands_off"
    outcome: Optional[Outcome] = None
    artifacts: dict = field(default_factory=dict)
    waiting_for: Optional[str] = None   # question id when WAITING_INPUT
