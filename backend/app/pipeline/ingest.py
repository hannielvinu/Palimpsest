from io import BytesIO
from pathlib import PurePath
import re

from PIL import Image
from ..core.config import MAX_BYTES, MAX_PIXELS


def inspect_upload(name, raw):
    name = PurePath(name.replace("\\", "/")).name
    safe = re.sub(r"[^\w.() -]", "_", name)[:110]
    suffix = PurePath(name).suffix.lower()
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Cannot determine: each document must contain 1 byte to 8 MiB.")
    if suffix == ".pdf" and raw.startswith(b"%PDF-"):
        return safe, "application/pdf"
    if suffix in {".jpg", ".jpeg", ".png"}:
        try:
            with Image.open(BytesIO(raw)) as im:
                expected = "PNG" if suffix == ".png" else "JPEG"
                if im.format != expected or im.width * im.height > MAX_PIXELS:
                    raise ValueError
                im.verify()
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
            raise ValueError("Cannot determine: invalid or oversized image.") from exc
        return safe, "image/png" if suffix == ".png" else "image/jpeg"
    raise ValueError("Cannot determine: expected PDF, PNG or JPEG with matching file contents.")
