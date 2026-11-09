from statistics import median

import cv2
import numpy as np

from ..pipeline.evidence import MANIPULATION, finding
from ..pipeline.ocr import lines


def stroke_proxy(gray, bbox):
    h, w = gray.shape
    a, b, c, d = (int(v * size) for v, size in zip(bbox, (w, h, w, h)))
    patch = gray[max(0,b):d, max(0,a):c]
    if patch.size < 25:
        return 0.0, 0.0
    ink = (patch < 145).astype(np.uint8)
    widths = cv2.distanceTransform(ink, cv2.DIST_L2, 3)
    sharpness = float(cv2.Laplacian(patch, cv2.CV_64F).var())
    return round(float(np.percentile(widths[ink > 0], 75)), 2) if ink.any() else 0, round(sharpness, 1)


def inspect(doc, page, tokens, image, number):
    money = [f for f in doc["fields"] if f["page"] == number and f["key"] in {"gross", "deductions", "net", "salary_credit"}]
    if len(money) < 3:
        return []
    gray = np.asarray(image.convert("L"))
    spans = [s for b in page.get_text("dict", flags=fitz_text_flags())["blocks"]
             for line in b.get("lines", []) for s in line["spans"]] if page is not None and not page.rotation else []
    results = []
    for field in money:
        x0, y0, x1, y1 = field["bbox"]
        height = y1 - y0
        controls = [other for other in money if other is not field]
        typical = median(other["bbox"][3] - other["bbox"][1] for other in controls)
        near = [t for line in lines(tokens, .031) if any(abs(t["base"] - (y0 + y1) / 2) < .013 and
                 t["bbox"][0] >= x0 - .005 for t in line) for t in line if t["bbox"][0] < x0 - .035]
        label = min(near, key=lambda t: abs(t["base"] - (y0 + y1) / 2)) if near else None
        baseline_delta = abs(y1 - label["bbox"][3]) if label else 0
        font = ""
        peers = []
        if spans:
            def span_for(target):
                point = target["bbox"][0] * page.rect.width, sum(target["bbox"][1::2]) / 2 * page.rect.height
                return next((s for s in spans if s["bbox"][0] - 1 <= point[0] <= s["bbox"][2]
                             and s["bbox"][1] <= point[1] <= s["bbox"][3]), None)
            field_span = span_for(field)
            label_span = span_for(label) if label else None
            if field_span and label_span:
                baseline_delta = abs(field_span["origin"][1] - label_span["origin"][1]) / page.rect.height
            font = field_span["font"] if field_span else ""
            peers = [(span_for(other) or {}).get("font", "") for other in controls]
        stroke, sharpness = stroke_proxy(gray, field["bbox"])
        peer_metrics = [stroke_proxy(gray, other["bbox"]) for other in controls]
        baseline_diff = baseline_delta > .004
        font_diff = bool(font and all(peer and peer != font for peer in peers))
        if typical > 0 and height / typical >= 1.22 and (font_diff or (baseline_diff and field["method"] == "OCR" and stroke > 1.2 * median(p[0] for p in peer_metrics))):
            results.append(finding("font_baseline", MANIPULATION, "Amount typography differs from neighboring amounts.",
                                   field, method="Relative word height, PDF font and baseline or OCR bottom alignment, raster stroke/edge statistics",
                                   limits="Mixed typography, OCR boxes and scan blur can change these measures.",
                                   confidence=.87 if font_diff else .65,
                                   values={"value": field["value"], "font": font, "peer_fonts": peers,
                                           "height_ratio": round(height / typical, 2), "baseline_offset": round(baseline_delta, 4),
                                           "stroke_proxy": stroke, "peer_stroke": median(p[0] for p in peer_metrics),
                                           "sharpness": sharpness, "peer_sharpness": median(p[1] for p in peer_metrics)}))
    return results


def fitz_text_flags():
    import fitz
    return fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
