from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps

from ..pipeline.evidence import MANIPULATION, finding, location


def residual(image):
    im = image.copy()
    im.thumbnail((1100, 1100))
    stream = BytesIO()
    im.save(stream, "JPEG", quality=90)
    stream.seek(0)
    with Image.open(stream) as compressed:
        error = np.abs(np.asarray(im, dtype=np.int16) - np.asarray(compressed, dtype=np.int16)).mean(axis=2)
    return im, error


def heatmap(image):
    _, error = residual(image)
    intensity = Image.fromarray(np.uint8(np.clip(error * 8, 0, 255)))
    return ImageOps.colorize(intensity, "#19212d", "#f9c272")


def inspect(image, doc, page):
    im, error = residual(image)
    local = cv2.blur(error, (33, 33))
    peak = float(local.max())
    baseline = float(np.percentile(local, 98))
    if peak < max(18, baseline * 2.6):
        return []
    y, x = np.unravel_index(local.argmax(), local.shape)
    box = [max(0, (x-28)/im.width), max(0, (y-28)/im.height), min(1, (x+28)/im.width), min(1, (y+28)/im.height)]
    return [finding("ela", MANIPULATION, "An isolated JPEG recompression residual was observed.", location(doc, page, box),
                    method="JPEG quality-90 residual with local peak threshold",
                    limits="Weak signal on recompressed images. Ordinary high-contrast edges can trigger it.",
                    confidence=.46, values={"local_peak": round(peak, 2)})]
