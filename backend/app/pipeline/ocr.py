from collections import defaultdict
from io import BytesIO
import os
from pathlib import Path

import fitz
from PIL import Image
import pytesseract
from pytesseract import Output

from ..core.config import MAX_PAGES, MAX_PIXELS

windows_tesseract = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
if os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
elif windows_tesseract.exists():
    pytesseract.pytesseract.tesseract_cmd = str(windows_tesseract)


def normalized(rect, width, height):
    x0, y0, x1, y1 = rect
    return [round(v, 5) for v in (x0 / width, y0 / height, x1 / width, y1 / height)]


def pdf_open(raw):
    pdf = fitz.open(stream=raw, filetype="pdf")
    if pdf.needs_pass or not 1 <= len(pdf) <= MAX_PAGES:
        pdf.close()
        raise ValueError("Encrypted, empty, or longer than six pages.")
    return pdf


def raster(page, scale=1.7):
    area = page.rect.width * page.rect.height
    if not 0 < area <= MAX_PIXELS:
        raise ValueError("Page dimensions exceed the rendering limit.")
    scale = min(scale, (MAX_PIXELS / area) ** .5)
    pm = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False, annots=False)
    return Image.frombytes("RGB", (pm.width, pm.height), pm.samples)


def image_open(raw):
    with Image.open(BytesIO(raw)) as im:
        if im.width * im.height > MAX_PIXELS:
            raise ValueError("Image dimensions exceed the limit.")
        return im.convert("RGB")


def pdf_tokens(page):
    tokens = []
    for word in page.get_text("words", sort=True):
        x0, y0, x1, y1, text, *_ = word
        tokens.append({"text": text, "bbox": normalized((x0, y0, x1, y1), page.rect.width, page.rect.height),
                       "base": (y0 + y1) / 2 / page.rect.height, "confidence": 1.0})
    if page.rotation:
        for token in tokens:
            x0, y0, x1, y1 = token["bbox"]
            rect = fitz.Rect(x0 * page.rect.width, y0 * page.rect.height, x1 * page.rect.width, y1 * page.rect.height)
            token["bbox"] = normalized(rect * page.rotation_matrix, page.rect.width, page.rect.height)
    return tokens


def ocr_tokens(im):
    data = pytesseract.image_to_data(im, output_type=Output.DICT, config="--psm 6", timeout=9)
    tokens = []
    for i, text in enumerate(data["text"]):
        confidence = float(data["conf"][i])
        if not text.strip() or confidence < 20:
            continue
        x, y, w, h = (data[key][i] for key in ("left", "top", "width", "height"))
        tokens.append({"text": text, "bbox": normalized((x, y, x+w, y+h), im.width, im.height),
                       "base": (y+h/2) / im.height, "confidence": round(confidence / 100, 3)})
    return tokens


def lines(tokens, gap=.023):
    groups = defaultdict(list)
    centers = []
    for token in sorted(tokens, key=lambda item: item["base"]):
        if not centers or token["base"] - centers[-1] > gap:
            centers.append(token["base"])
        groups[len(centers)-1].append(token)
    return [sorted(group, key=lambda token: token["bbox"][0]) for group in groups.values()]


def joined(group):
    return " ".join(token["text"] for token in group)


def bounds(tokens):
    return [min(t["bbox"][0] for t in tokens), min(t["bbox"][1] for t in tokens),
            max(t["bbox"][2] for t in tokens), max(t["bbox"][3] for t in tokens)]
