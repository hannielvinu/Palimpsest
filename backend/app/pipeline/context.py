from collections import Counter
from datetime import date
import re

from ..detectors.arithmetic import check
from .evidence import INCONSISTENCY, OBSERVED, finding, location

REQUIRED = {"Salary slip": ["name", "gross", "deductions", "net"], "Bank statement": ["account"],
            "Address proof": ["address"], "ID proof": ["id_number"], "PAN-style card": ["id_number"]}


def by_key(doc):
    counts = Counter(f["key"] for f in doc["fields"])
    return {f["key"]: f for f in doc["fields"] if counts[f["key"]] == 1 and f["confidence"] >= .50}


def context(doc):
    fields = by_key(doc)
    results = []
    arithmetic = check(fields) if doc["type"] == "Salary slip" else None
    if arithmetic:
        results.append(arithmetic)

    def add(label, message, source, status=OBSERVED, values=None):
        results.append(finding(label, status, message, source, method="Label and normalized value rules",
                               limits="Template and OCR errors can create the same pattern.",
                               confidence=source.get("confidence", .65), values=values, layer="fields"))

    for key in REQUIRED.get(doc["type"], []):
        if not any(f["key"] == key for f in doc["fields"]):
            add("missing_field", f"Expected field could not be read ({key}).", location(doc))
    for key, count in Counter(f["key"] for f in doc["fields"]).items():
        if count > 1:
            add("duplicate_field", f"Repeated field label ({key}).", next(f for f in doc["fields"] if f["key"] == key))
    for key in ("account", "id_number", "address"):
        if key not in fields:
            continue
        field = fields[key]
        value = field["normalized"]
        invalid = ((key == "account" and not re.fullmatch(r"\d{8,18}", value))
                   or (key == "id_number" and not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]" if doc["type"] == "PAN-style card" else r"[A-Z0-9]{6,18}", value))
                   or (key == "address" and re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+)?", value) and not re.search(r"road|lane|street", value)))
        if invalid:
            add("field_format", f"The {key} value has an unexpected format.", field, INCONSISTENCY, {key: field["value"]})
    for start, end in (("start_date", "end_date"), ("dob", "issue_date")):
        if start in fields and end in fields and fields[start]["normalized"] and fields[end]["normalized"]:
            if fields[start]["normalized"] > fields[end]["normalized"]:
                add("date_order", f"{start} comes after {end}.", fields[start], INCONSISTENCY,
                    {key: fields[key]["value"] for key in (start, end)})
    if {"dob", "age", "issue_date"} <= fields.keys():
        try:
            born, issued = (date.fromisoformat(fields[k]["normalized"]) for k in ("dob", "issue_date"))
            actual = issued.year - born.year - ((issued.month, issued.day) < (born.month, born.day))
            if abs(actual - int(fields["age"]["normalized"])) > 1:
                add("age_check", "Stated age differs from age at issue date.", fields["age"], INCONSISTENCY, {"calculated": actual})
        except (ValueError, TypeError):
            pass
    return results
