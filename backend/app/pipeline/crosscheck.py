from datetime import date
from decimal import Decimal
from itertools import combinations
import re

from rapidfuzz import fuzz

from .context import by_key
from .evidence import OBSERVED, INCONSISTENCY, finding


def name_match(left, right):
    def words(value):
        return [w for w in re.findall(r"[^\W\d_]+", value.casefold()) if w not in {"mr", "mrs", "ms", "dr", "shri"}]

    a, b = words(left), words(right)
    if a == b and left.casefold().strip() == right.casefold().strip():
        return "exact"
    if a and b and (sorted(a) == sorted(b) or (
        len(a) == len(b) and any(x == y and len(x) > 1 for x, y in zip(a, b))
        and all(x == y or (min(len(x), len(y)) == 1 and x[0] == y[0]) for x, y in zip(a, b))
    ) or fuzz.token_sort_ratio(" ".join(a), " ".join(b)) >= 92):
        return "variant"
    return "conflict"


def compare(docs):
    results = []
    matrix = [{"key": key, "cells": [by_key(doc).get(key) for doc in docs], "status": "—"}
              for key in ("name", "dob", "id_number", "address", "employer", "net", "salary_credit", "pay_date", "credit_date")]

    def mark(key, status):
        ranks = {"—": 0, "Aligned": 1, "Benign variant": 2, "Cycle unverified": 3, "Mismatch": 4}
        row = next(row for row in matrix if row["key"] == key)
        if ranks[status] > ranks[row["status"]]:
            row["status"] = status

    def emit(detector, status, title, first, second, method, limits):
        results.append(finding(detector, status, title, first, method=method, limits=limits,
                               confidence=min(first["confidence"], second["confidence"]), related=[second],
                               values={"source": first["value"], "related": second["value"]}, layer="fields"))

    for left, right in combinations(docs, 2):
        a, b = by_key(left), by_key(right)
        for key in ("name", "dob", "id_number", "address", "employer"):
            if key not in a or key not in b or not a[key]["normalized"] or not b[key]["normalized"]:
                continue
            x, y = a[key], b[key]
            if key == "id_number" and left["type"] != right["type"]:
                continue
            if x["normalized"] == y["normalized"]:
                mark(key, "Aligned")
                if key == "dob" and x["value"] != y["value"]:
                    mark(key, "Benign variant")
                continue
            variant = (name_match(x["value"], y["value"]) != "conflict" if key == "name"
                       else key in {"address", "employer"} and fuzz.token_sort_ratio(x["normalized"], y["normalized"]) >= 90)
            mark(key, "Benign variant" if variant else "Mismatch")
            label = {"dob": "Date of birth", "id_number": "ID number"}.get(key, key.capitalize())
            emit("name_variant" if variant and key == "name" else "cross_identity", OBSERVED if variant else INCONSISTENCY,
                 f"{label} is a likely benign variant." if variant else f"{label} differs across documents.",
                 x, y, "Normalized field comparison with fuzzy matching for text",
                 "Similar names or addresses can identify different people. Confirm with a primary source.")
        for slip, bank in ((a, b), (b, a)):
            if not slip.get("net", {}).get("normalized") or not bank.get("salary_credit", {}).get("normalized"):
                continue
            pay, credit = slip.get("pay_date", {}), bank.get("credit_date", {})
            if not pay.get("normalized") or not credit.get("normalized"):
                mark("net", "Cycle unverified")
                continue
            delta = (date.fromisoformat(credit["normalized"]) - date.fromisoformat(pay["normalized"])).days
            if not -3 <= delta <= 10:
                mark("net", "Cycle unverified")
                continue
            x, y = slip["net"], bank["salary_credit"]
            expected, credited = Decimal(x["normalized"]), Decimal(y["normalized"])
            mismatch = abs(expected - credited) > max(Decimal("100"), abs(expected) * Decimal(".01"))
            for key in ("net", "salary_credit"):
                mark(key, "Mismatch" if mismatch else "Aligned")
            if mismatch:
                emit("salary_credit", INCONSISTENCY, "Net pay conflicts with the bank salary credit.", x, y,
                     "Pay window −3 to +10 days and tolerance max(INR 100, 1%)",
                     "Split credits, bonuses, arrears and settlement delays can explain discrepancies.")
            elif pay["value"] != credit["value"] and delta:
                emit("pay_cycle", OBSERVED, "Salary credit is within the expected pay window.", pay, credit,
                     "Dates normalized day-first; pay window −3 to +10 days",
                     "Settlement can shift over weekends or bank holidays.")
    return results, matrix
