from itertools import combinations

import cv2
import numpy as np
from skimage.metrics import structural_similarity

from ..pipeline.evidence import MANIPULATION, finding, location


def locate(doc, page, image, number):
    labels = page.search_for("signature") if page is not None else []
    if not labels:
        return []
    label = labels[-1] * page.rotation_matrix
    width, height = page.rect.width, page.rect.height
    box = [max(0, label.x1/width + .04), max(0, label.y0/height - .03),
           min(1, label.x1/width + .37), min(1, label.y1/height + .03)]
    crop = np.asarray(image.convert("L").crop(tuple(int(v * size) for v, size in zip(box, (image.width, image.height)*2))))
    if not crop.size:
        return []
    y, x = np.where(crop < 125)
    if x.size < 85 or x.max() - x.min() < 20 or y.max() - y.min() < 10:
        return []
    ink = cv2.resize(crop[y.min():y.max()+1, x.min():x.max()+1], (160, 48), interpolation=cv2.INTER_AREA)
    return [(location(doc, number, box), ink)]


def compare(signatures):
    results = []
    for (left, a), (right, b) in combinations(signatures[:24], 2):
        if left["document_id"] == right["document_id"]:
            continue
        ssim = float(structural_similarity(a, b, data_range=255))
        if ssim >= .94:
            results.append(finding("signature_reuse", MANIPULATION, "Two signature regions are pixel-near-identical.", left,
                                   method="Signature-label crop, ink normalization and SSIM ≥ 0.94",
                                   limits="A shared authorized stamp can produce an identical image. No biometric inference.",
                                   confidence=round(ssim, 3), values={"ssim": round(ssim, 3)}, related=[right], layer="signature"))
    return results
