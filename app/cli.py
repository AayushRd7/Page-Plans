"""CLI for local development.

    python -m app.cli sample        render the reference sample (DOCX + PDF + TXT)
    python -m app.cli diff "old" "new"   debug word diff
"""
import sys
from pathlib import Path

from app.diffing import word_diff
from app.render.docx_render import render_docx
from app.render.pdf_render import render_pdf

OUT = Path(__file__).resolve().parent.parent / "out"


def cmd_sample() -> None:
    from samples.thca_flower import build

    doc = build()
    OUT.mkdir(exist_ok=True)
    pdf_path = OUT / "thca_sample.pdf"
    docx_path = OUT / "thca_sample.docx"
    txt_path = OUT / "thca_paste_ready.txt"
    render_pdf(doc, str(pdf_path))
    render_docx(doc, str(docx_path))
    txt_path.write_text(doc.paste_ready_text(), encoding="utf-8")
    print(f"PDF : {pdf_path}")
    print(f"DOCX: {docx_path}")
    print(f"TXT : {txt_path}")


def cmd_diff(old: str, new: str) -> None:
    for r in word_diff(old, new):
        marker = {"normal": " ", "del": "-", "ins": "+"}[r.style]
        print(f"{marker} {r.text!r}")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "sample":
        cmd_sample()
    elif args[0] == "diff" and len(args) == 3:
        cmd_diff(args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
