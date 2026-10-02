"""Word-level diff producing styled runs for change visualization."""
import difflib
import re

from app.docmodel.blocks import Run

_WORD = re.compile(r"\S+\s*|\s+")


def word_diff(old: str, new: str) -> list[Run]:
    """Diff two texts at word level.

    Deleted words get style 'del' (strikethrough), inserted words 'ins'
    (highlight). Everything else 'normal'.
    """
    a = _WORD.findall(old)
    b = _WORD.findall(new)
    runs: list[Run] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b).get_opcodes():
        if tag == "equal":
            runs.append(Run(text="".join(a[i1:i2]), style="normal"))
        elif tag == "delete":
            runs.append(Run(text="".join(a[i1:i2]), style="del"))
        elif tag == "insert":
            runs.append(Run(text="".join(b[j1:j2]), style="ins"))
        else:  # replace
            runs.append(Run(text="".join(a[i1:i2]), style="del"))
            runs.append(Run(text="".join(b[j1:j2]), style="ins"))
    return _merge_adjacent(runs)


def _merge_adjacent(runs: list[Run]) -> list[Run]:
    merged: list[Run] = []
    for r in runs:
        if merged and merged[-1].style == r.style:
            merged[-1].text += r.text
        else:
            merged.append(r)
    return [r for r in merged if r.text]
