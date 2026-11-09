import re

import pymupdf as fitz

from ..pipeline.evidence import MANIPULATION, OBSERVED, finding, location
from ..pipeline.ocr import normalized

INSTRUCTION = re.compile(r"ignore.{0,60}instruction|(?:ai|automated) reviewer|(?:approve|clear).{0,40}(?:application|applicant|document)", re.I)


def white_on_light(page, rect, color):
    if min(color, default=0) <= .98:
        return False
    clip = (fitz.Rect(rect) * page.rotation_matrix) & page.rect
    if clip.is_empty:
        return False
    scale = min(.5, (4000 / clip.get_area()) ** .5)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, colorspace=fitz.csGRAY, annots=False)
    samples = pixmap.samples
    return bool(samples) and sum(value >= 242 for value in samples) >= .90 * len(samples)


def inspect(page, doc, number):
    results = []
    hidden = []
    for span in page.get_texttrace():
        content = "".join(chr(c[0]) for c in span["chars"] if 0 <= c[0] <= 0x10FFFF).strip()
        if not content:
            continue
        rect = fitz.Rect(span["bbox"]) * page.rotation_matrix
        x0, y0, x1, y1 = rect
        color = span.get("color", ())
        invisible = (span.get("opacity", 1) < .05 or span["type"] == 3 or span["size"] < 3 or
                     x1 < 0 or y1 < 0 or x0 > page.rect.width or y0 > page.rect.height or
                     white_on_light(page, span["bbox"], color))
        if not invisible:
            continue
        box = normalized((x0, y0, x1, y1), page.rect.width, page.rect.height)
        hidden.append(box)
        instruction = bool(INSTRUCTION.search(content))
        results.append(finding("hidden_text", MANIPULATION if instruction else OBSERVED,
                               "Embedded text attempting to instruct an automated reviewer." if instruction else
                               "Low-visibility embedded text observed.", location(doc, number, box),
                               method="PDF text trace, visibility heuristics and instruction pattern",
                               limits="White text can be visible on dark backgrounds. Phrase rules miss paraphrases and split instructions.",
                               confidence=.92 if instruction else .65,
                               values={"excerpt": content[:220], "handled_as": "Untrusted document data"},
                               layer="hidden"))
    return results[:12], hidden
