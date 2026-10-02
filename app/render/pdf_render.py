"""Blocks -> PDF via headless Chromium (Playwright).

The HTML is rendered once and printed to A4 with a page-number footer.
Chromium print gives pixel-level control and matches the web preview.
"""
from playwright.sync_api import sync_playwright

from app.docmodel.blocks import PlanDocument
from app.render.html_render import render_html

FOOTER = """
<div style="width:100%; font-size:7.5pt; color:#666; font-family:Helvetica,Arial;
            text-align:center; padding:0 16mm;">
  Page <span class="pageNumber"></span> of <span class="totalPages"></span>
</div>
"""

HEADER = '<div style="width:100%; font-size:7pt;"></div>'


def render_pdf(doc: PlanDocument, out_path: str) -> None:
    html_str = render_html(doc)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_str, wait_until="networkidle")
        page.pdf(
            path=out_path,
            format="A4",
            display_header_footer=True,
            header_template=HEADER,
            footer_template=FOOTER,
            print_background=True,
            margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
        )
        browser.close()
