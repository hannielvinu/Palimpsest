from decimal import Decimal, InvalidOperation
import re

import dateparser

from .ocr import bounds, joined

FIELDS = {
    "name": r"(?:employee |full |account holder )?name",
    "dob": r"(?:dob|date of birth|birth date)",
    "id_number": r"(?:id number|pan(?: number)?|permanent account number)",
    "employer": r"(?:employer|company)",
    "gross": r"gross(?: pay| salary)?",
    "deductions": r"(?:total )?deductions?",
    "net": r"net(?: pay| salary)?",
    "account": r"(?:bank )?account(?: number| no\.?)",
    "address": r"(?:service |residential )?address",
    "pay_date": r"(?:pay|salary) date",
    "credit_date": r"credit date",
    "issue_date": r"issue date",
    "start_date": r"(?:period start|start date)",
    "end_date": r"(?:period end|end date)",
    "salary_credit": r"salary credit",
    "age": r"age"
}
PATTERNS = {key: re.compile(r"^\s*" + value + r"\s*[:;]\s*(.+)$", re.I) for key, value in FIELDS.items()}
MONEY = {"gross", "deductions", "net", "salary_credit"}


def amount(text):
    compact = re.sub(r"(?:INR|Rs\.?|₹|\s)", "", text, flags=re.I)
    if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d{1,2})?", compact):
        return None
    try:
        return str(Decimal(compact.replace(",", "")).quantize(Decimal(".01")))
    except InvalidOperation:
        return None


def normalize(key, value):
    if key in MONEY:
        return amount(value)
    if key == "dob" or key.endswith("_date"):
        date = dateparser.parse(value, settings={"DATE_ORDER": "DMY", "PREFER_LOCALE_DATE_ORDER": False,
                                                  "STRICT_PARSING": True}, languages=["en"])
        return date.date().isoformat() if date else None
    if key in {"account", "id_number"}:
        return re.sub(r"[\s-]", "", value).upper()
    return " ".join(value.casefold().split())


def extract(groups, doc_id, page, method):
    result = []
    for group in groups:
        line = joined(group)
        for key, pattern in PATTERNS.items():
            match = pattern.match(line)
            if not match:
                continue
            value = match[1].strip()
            count = len(value.split())
            value_tokens = group[-count:]
            confidence = sum(t["confidence"] for t in value_tokens) / len(value_tokens)
            result.append({"key": key, "value": value, "normalized": normalize(key, value),
                           "confidence": round(confidence, 3), "page": page, "bbox": bounds(value_tokens),
                           "document_id": doc_id, "method": method, "verified": False})
            break
    return result
