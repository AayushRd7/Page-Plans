"""Document block model.

Single source of truth for a page plan. Every pipeline stage writes blocks,
every renderer (PDF, DOCX, paste-ready TXT, web preview) consumes them.
Adding an output format never touches pipeline code.
"""
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class Run(BaseModel):
    """A styled text run, used for word-level change diffs."""
    text: str
    style: Literal["normal", "del", "ins"] = "normal"


class Block(BaseModel):
    type: str


class H1(Block):
    type: Literal["h1"] = "h1"
    text: str


class H2(Block):
    type: Literal["h2"] = "h2"
    text: str
    badge: Optional[str] = None  # IMPROVE / MERGE / REMOVE / KEEP / ADD / NEW


class H3(Block):
    type: Literal["h3"] = "h3"
    text: str
    badge: Optional[str] = None


class Paragraph(Block):
    type: Literal["p"] = "p"
    text: str


class Note(Block):
    type: Literal["note"] = "note"
    text: str  # small grey italic, used for caveats and meta commentary


class Label(Block):
    type: Literal["label"] = "label"
    text: str  # small-caps marker, e.g. CHANGES / PASTE-READY / KEEP


class PageBreak(Block):
    type: Literal["pagebreak"] = "pagebreak"


class KVTable(Block):
    type: Literal["kv"] = "kv"
    pairs: list[list[str]]  # 2-column key/value


class Table(Block):
    type: Literal["table"] = "table"
    header: list[str]
    rows: list[list[str]]
    caption: Optional[str] = None


class Bullets(Block):
    type: Literal["bullets"] = "bullets"
    items: list[str]


class Numbered(Block):
    type: Literal["numbered"] = "numbered"
    items: list[str]


class DiffPara(Block):
    type: Literal["diff"] = "diff"
    runs: list[Run]


AnyBlock = Annotated[
    Union[
        H1, H2, H3, Paragraph, Note, Label, PageBreak,
        KVTable, Table, Bullets, Numbered, DiffPara,
    ],
    Field(discriminator="type"),
]


class PlanDocument(BaseModel):
    title: str
    subtitle: str = ""
    market_note: str = ""
    blocks: list[AnyBlock]

    def paste_ready_text(self) -> str:
        """Extract paste-ready copy (labels + following paragraphs/diffs)."""
        lines: list[str] = [f"Page plan — {self.subtitle or self.title}"]
        current_h = ""
        for b in self.blocks:
            if isinstance(b, (H2, H3)):
                current_h = b.text
            elif isinstance(b, Label) and b.text.upper().startswith("PASTE-READY"):
                if current_h:
                    lines.append(f"\n=== {current_h} ===")
            elif isinstance(b, Paragraph) and current_h:
                lines.append(b.text)
            elif isinstance(b, DiffPara) and current_h:
                added = "".join(r.text for r in b.runs if r.style != "del")
                lines.append(added)
        return "\n".join(lines) + "\n"
