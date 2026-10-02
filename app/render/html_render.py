"""Blocks -> HTML. The HTML is the shared visual source for PDF (Chromium
print), web preview, and is the styling reference for the DOCX renderer."""
import html

from app.docmodel.blocks import (
    AnyBlock, Bullets, DiffPara, H1, H2, H3, KVTable, Label, Note,
    Numbered, PageBreak, Paragraph, PlanDocument, Table,
)

BADGE_COLORS = {
    "IMPROVE": "#1d4ed8", "MERGE": "#7c3aed", "REMOVE": "#b91c1c",
    "KEEP": "#15803d", "ADD": "#15803d", "NEW": "#15803d",
}

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt;
       color: #111; line-height: 1.45; margin: 0; }
h1 { font-size: 20pt; margin: 0 0 2mm 0; }
.subtitle { font-size: 13pt; color: #333; margin-bottom: 6mm; }
.market-note { font-size: 8.5pt; color: #555; font-style: italic; margin-bottom: 6mm; }
h2 { font-size: 12.5pt; margin: 7mm 0 2.5mm 0; padding-bottom: 1mm;
     border-bottom: 1.5px solid #111; page-break-after: avoid; }
h3 { font-size: 10.5pt; margin: 4mm 0 1.5mm 0; page-break-after: avoid; }
.badge { display: inline-block; font-size: 7pt; font-weight: 700; color: #fff;
         padding: 0.5mm 1.6mm; border-radius: 2px; vertical-align: middle;
         margin-right: 1.5mm; letter-spacing: 0.4px; }
p { margin: 0 0 2.5mm 0; }
.note { font-size: 8.5pt; color: #555; font-style: italic; margin-bottom: 2.5mm; }
.label { font-size: 7.5pt; font-weight: 700; letter-spacing: 1px; color: #555;
         margin: 3mm 0 1mm 0; }
table { border-collapse: collapse; width: 100%; margin: 0 0 3.5mm 0;
        page-break-inside: auto; }
th, td { border: 1px solid #ccc; padding: 1.2mm 2mm; text-align: left;
         vertical-align: top; font-size: 8.5pt; }
th { background: #f3f4f6; font-weight: 700; }
td.k { font-weight: 700; width: 32%; background: #fafafa; }
caption, .caption { caption-side: top; text-align: left; font-size: 8pt;
        color: #555; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 1mm; }
ul, ol { margin: 0 0 2.5mm 0; padding-left: 5mm; }
li { margin-bottom: 1mm; font-size: 9pt; }
del { color: #b91c1c; text-decoration: line-through; }
ins { background: #fff3a3; text-decoration: none; }
.pagebreak { page-break-before: always; }
.diff { margin-bottom: 2.5mm; }
"""


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def esc_br(text: str) -> str:
    """Escape and preserve newlines as line breaks."""
    return esc(text).replace("\n", "<br>")


def _badge_html(badge: str | None) -> str:
    if not badge:
        return ""
    color = BADGE_COLORS.get(badge.upper(), "#374151")
    return f'<span class="badge" style="background:{color}">{esc(badge.upper())}</span>'


def render_block(b: AnyBlock) -> str:
    if isinstance(b, H1):
        return f"<h1>{esc(b.text)}</h1>"
    if isinstance(b, H2):
        return f"<h2>{_badge_html(b.badge)}{esc(b.text)}</h2>"
    if isinstance(b, H3):
        return f"<h3>{_badge_html(b.badge)}{esc(b.text)}</h3>"
    if isinstance(b, Paragraph):
        return f"<p>{esc_br(b.text)}</p>"
    if isinstance(b, Note):
        return f'<p class="note">{esc(b.text)}</p>'
    if isinstance(b, Label):
        return f'<p class="label">{esc(b.text)}</p>'
    if isinstance(b, PageBreak):
        return '<div class="pagebreak"></div>'
    if isinstance(b, KVTable):
        rows = "".join(
            f'<tr><td class="k">{esc_br(k)}</td><td>{esc_br(v)}</td></tr>'
            for k, v in b.pairs
        )
        return f"<table>{rows}</table>"
    if isinstance(b, Table):
        head = "".join(f"<th>{esc_br(h)}</th>" for h in b.header)
        body = "".join(
            "<tr>" + "".join(f"<td>{esc_br(c)}</td>" for c in row) + "</tr>"
            for row in b.rows
        )
        cap = f'<p class="caption">{esc(b.caption)}</p>' if b.caption else ""
        return f"{cap}<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    if isinstance(b, Bullets):
        items = "".join(f"<li>{esc(i)}</li>" for i in b.items)
        return f"<ul>{items}</ul>"
    if isinstance(b, Numbered):
        items = "".join(f"<li>{esc(i)}</li>" for i in b.items)
        return f"<ol>{items}</ol>"
    if isinstance(b, DiffPara):
        parts: list[str] = []
        for r in b.runs:
            t = esc(r.text)
            if r.style == "del":
                parts.append(f"<del>{t}</del>")
            elif r.style == "ins":
                parts.append(f"<ins>{t}</ins>")
            else:
                parts.append(t)
        return f'<p class="diff">{"".join(parts)}</p>'
    raise ValueError(f"unknown block: {type(b)}")


def render_html(doc: PlanDocument) -> str:
    body = "\n".join(render_block(b) for b in doc.blocks)
    subtitle = f'<p class="subtitle">{esc(doc.subtitle)}</p>' if doc.subtitle else ""
    note = (f'<p class="market-note">{esc(doc.market_note)}</p>'
            if doc.market_note else "")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<h1>{esc(doc.title)}</h1>
{subtitle}{note}
{body}
</body></html>"""
