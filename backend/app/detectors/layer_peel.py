from difflib import SequenceMatcher
import re
from io import BytesIO

import fitz
import pikepdf

from ..pipeline.evidence import MANIPULATION, finding, location
from ..pipeline.ocr import pdf_open

END = re.compile(rb"startxref\s+(\d+)\s+%%EOF(?=\s|$)")


def revisions(raw):
    candidates = [m for m in END.finditer(raw) if 0 < int(m[1]) < m.start()]
    previous = []
    for marker in candidates[-5:-1]:
        prefix = raw[:marker.end()] + b"\n"
        try:
            with pikepdf.Pdf.open(BytesIO(prefix), attempt_recovery=False):
                pass
            with pdf_open(prefix):
                previous.append(prefix)
        except (pikepdf.PdfError, ValueError, RuntimeError):
            continue
    return previous


def compare(raw, current, doc):
    records = []
    findings = []
    prefixes = revisions(raw)
    for index, prefix in enumerate(prefixes, 1):
        with pdf_open(prefix) as before:
            changes = []
            for page_number, (old, new) in enumerate(zip(before, current), 1):
                old_lines = [line for line in old.get_text().splitlines() if line.strip()][:1000]
                new_lines = [line for line in new.get_text().splitlines() if line.strip()][:1000]
                matcher = SequenceMatcher(a=old_lines, b=new_lines, autojunk=True)
                for operation, i, j, k, l in matcher.get_opcodes():
                    if operation == "equal" or len(changes) >= 12:
                        continue
                    prior, present = " / ".join(old_lines[i:j])[:220], " / ".join(new_lines[k:l])[:220]
                    search = new.search_for(new_lines[k]) if k < l else []
                    box = None
                    if search:
                        rect = search[0] * new.rotation_matrix
                        box = [rect.x0 / new.rect.width, rect.y0 / new.rect.height, rect.x1 / new.rect.width, rect.y1 / new.rect.height]
                    changes.append({"before": prior, "current": present, "page": page_number, "bbox": box, "revision": index})
            records.append({"revision": index, "metadata": before.metadata, "pages": len(before), "changes": changes})
    if records and records[-1]["changes"]:
        for change in records[-1]["changes"]:
            findings.append(finding("layer_peel", MANIPULATION, "A prior PDF revision contains different text.",
                                    location(doc, change["page"], change["bbox"]),
                                    method="Validated prior startxref/EOF and compared embedded text",
                                    limits="Only retained incremental history is recoverable. A legitimate correction can leave the same trace.",
                                    confidence=.99, values=change, layer="revisions"))
    return records, findings
