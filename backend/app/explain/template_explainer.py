from .innocent_explanations import explain

WEIGHTS = {"OBSERVED": 0, "INCONSISTENCY": 2, "POSSIBLE_MANIPULATION": 2}
WEAK = {"ela", "copy_move", "signature_reuse"}


def summarize(items, unreadable):
    for index, item in enumerate(items, 1):
        item["id"] = f"E-{index:03d}"
        item["explanation"] = explain(item)
        item["points"] = 1 if item["detector"] in WEAK else WEIGHTS[item["status"]]
    items.sort(key=lambda item: -item["points"])
    total = sum(item["points"] for item in items)
    concern = "CANNOT DETERMINE" if unreadable else "HIGH" if total >= 6 else "MODERATE" if total >= 2 else "LOW"
    requests = list(dict.fromkeys(item["explanation"]["settle"] for item in items if item["points"] or item["detector"] == "quality"))
    letter = "Dear applicant,\n\nThank you for sharing your documents. "
    if requests:
        letter += "To complete our review, could you help us confirm the following?\n\n" + "\n".join("- " + s for s in requests)
    else:
        letter += "We have no additional document requests at this stage."
    return {"concern": concern, "score": total, "formula": "Observed 0 · inconsistency 2 · possible manipulation 2 · weak visual signals 1. Low 0–1, moderate 2–5, high 6+. Cannot determine if any input cannot be read.",
            "letter": letter + "\n\nThank you for your help.\nThe review team",
            "narrative": [f"{item['summary']} [{item['id']}]" for item in items]}
