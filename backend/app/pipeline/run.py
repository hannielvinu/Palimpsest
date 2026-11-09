from io import BytesIO
from time import perf_counter

import cv2
import numpy as np

from ..core.config import STEPS
from ..detectors import copy_move, ela, font_baseline, layer_peel, signature_reuse
from ..explain.template_explainer import summarize
from .classify import classify
from .context import context
from .crosscheck import compare
from .evidence import OBSERVED, finding, location
from .extract import extract
from .injection import inspect as inspect_hidden
from .ocr import image_open, joined, lines, ocr_tokens, pdf_open, pdf_tokens, raster

cv2.setNumThreads(1)


def render(raw, mime, page=1, revision=0, layer="source"):
    if layer == "ela":
        if mime != "image/jpeg" or page != 1 or revision:
            raise ValueError("ELA heatmap requires a current JPEG page")
        im = ela.heatmap(image_open(raw))
    elif mime == "application/pdf":
        if revision:
            versions = layer_peel.revisions(raw)
            if not 1 <= revision <= len(versions):
                raise ValueError("Revision unavailable")
            raw = versions[revision - 1]
        with pdf_open(raw) as pdf:
            if not 1 <= page <= len(pdf):
                raise ValueError("Page unavailable")
            im = raster(pdf[page-1])
    else:
        if page != 1 or revision:
            raise ValueError("Page unavailable")
        im = image_open(raw)
    stream = BytesIO()
    im.save(stream, "PNG")
    return stream.getvalue()


def read_pages(raw, mime, doc):
    pages = []
    if mime == "application/pdf":
        with pdf_open(raw) as pdf:
            doc["metadata"] = {key: pdf.metadata.get(key) for key in ("producer", "creator", "creationDate", "modDate")}
            doc["pages"] = len(pdf)
            for number, page in enumerate(pdf, 1):
                flagged, hidden = inspect_hidden(page, doc, number)
                tokens = pdf_tokens(page)
                im = None
                method = "Embedded text"
                tokens = [token for token in tokens if not any(
                    box[0] <= (token["bbox"][0] + token["bbox"][2]) / 2 <= box[2]
                    and box[1] <= (token["bbox"][1] + token["bbox"][3]) / 2 <= box[3] for box in hidden
                )]
                if len(tokens) < 6:
                    im = raster(page)
                    tokens = ocr_tokens(im)
                    method = "OCR"
                pages.append((lines(tokens, .028), method, im, flagged))
    else:
        im = image_open(raw)
        pages.append((lines(ocr_tokens(im)), "OCR", im, []))
    return pages


def analyze(records, report=lambda *_: None):
    docs, page_sets, evidence = [], [], []
    timings = []
    stage_start = perf_counter()

    def complete(index, detail=None):
        nonlocal stage_start
        elapsed = round((perf_counter() - stage_start) * 1000)
        timings.append({"step": STEPS[index], "ms": elapsed, "detail": detail or ""})
        report(timings[-1])
        stage_start = perf_counter()

    for record in records:
        docs.append({key: record[key] for key in ("id", "name", "mime", "sha256")} |
                    {"pages": 1, "fields": [], "revisions": [], "status": "Ready", "metadata": {}})
    complete(0, f"{len(docs)} originals hashed")
    for doc, record in zip(docs, records):
        try:
            pages = read_pages(record["original"], doc["mime"], doc)
            text = "\n".join(joined(group) for groups, _, _, _ in pages for group in groups)
            doc["type"] = classify(text)
            count = sum(len(g) for groups, _, _, _ in pages for g in groups)
            if count < 5:
                raise ValueError("Too few readable words. Obtain a higher-quality copy.")
            page_sets.append(pages)
        except (RuntimeError, ValueError, OSError) as exc:
            doc.update(type="Unknown", status="Cannot determine", reason=str(exc)[:240])
            page_sets.append([])
    complete(1, "Embedded text first. Scans use Tesseract.")
    for doc, pages in zip(docs, page_sets):
        for number, (groups, method, image, flagged) in enumerate(pages, 1):
            doc["fields"].extend(extract(groups, doc["id"], number, method))
            evidence.extend(flagged)
            if method == "OCR":
                reason = "A scanned source was read using unverified OCR."
                if image and cv2.Laplacian(np.asarray(image.convert("L")), cv2.CV_64F).var() < 120:
                    reason = "Scan blur was observed; extracted text is unverified."
                evidence.append(finding("quality", OBSERVED, reason, location(doc, number), method="OCR and raster edge energy",
                                        limits="Blur measurements depend on scan scale and content.", confidence=.73, layer="fields"))
        if doc["status"] == "Ready" and (doc["type"] == "Unknown" or not doc["fields"]):
            doc.update(status="Cannot determine", reason="The layout or field labels could not be interpreted reliably.")
        if doc["status"] == "Cannot determine":
            evidence.append(finding("quality", OBSERVED, doc["reason"], location(doc), method="Parser and OCR readability gate",
                                    limits="A higher-quality source may allow analysis.", confidence=1, layer="fields"))
    complete(2, f"{sum(len(d['fields']) for d in docs)} field regions")
    signatures = []
    for doc, record, pages in zip(docs, records, page_sets):
        if not pages:
            continue
        raw = record["original"]
        try:
            if doc["mime"] == "application/pdf":
                with pdf_open(raw) as pdf:
                    doc["revisions"], found = layer_peel.compare(raw, pdf, doc)
                    evidence.extend(found)
                    for index, (page, (groups, _, image, _)) in enumerate(zip(pdf, pages), 1):
                        image = image or raster(page)
                        evidence.extend(font_baseline.inspect(doc, page, [t for g in groups for t in g], image, index))
                        signatures.extend(signature_reuse.locate(doc, page, image, index))
            else:
                groups, _, image, _ = pages[0]
                evidence.extend(font_baseline.inspect(doc, None, [t for g in groups for t in g], image, 1))
                evidence.extend(copy_move.inspect(image, doc, 1))
                if doc["mime"] == "image/jpeg":
                    evidence.extend(ela.inspect(image, doc, 1))
        except (RuntimeError, ValueError, OSError):
            doc.update(status="Cannot determine", reason="A page could not be rendered for visual inspection.")
            evidence.append(finding("quality", OBSERVED, doc["reason"], location(doc), method="Bounded page renderer",
                                    limits="Request a new issuer export.", confidence=1))
    evidence.extend(signature_reuse.compare(signatures))
    complete(3, f"{sum(1 for e in evidence if e['layer'] != 'fields')} visual or structural observations")
    for doc in docs:
        evidence.extend(context(doc))
    complete(4, "Field relationships, formats and payroll arithmetic")
    cross, matrix = compare(docs)
    evidence.extend(cross)
    complete(5, f"{len(cross)} cross-document observations")
    summary = summarize(evidence, any(d["status"] == "Cannot determine" for d in docs))
    complete(6, f"{len(evidence)} evidence records")
    result = {"documents": docs, "findings": evidence, "matrix": matrix, "summary": summary, "timings": timings}
    complete(7, "Dossier data assembled")
    return result
