OBSERVED = "OBSERVED"
INCONSISTENCY = "INCONSISTENCY"
MANIPULATION = "POSSIBLE_MANIPULATION"


def finding(detector, status, summary, source, *, method, limits, confidence=.85, values=None, related=None, layer="visual"):
    return {"detector": detector, "status": status, "summary": summary,
            "document_id": source["document_id"], "page": source["page"], "bbox": source.get("bbox"),
            "method": method, "limits": limits, "confidence": confidence,
            "values": values or {}, "related": related or [], "layer": layer}


def location(doc, page=1, box=None):
    return {"document_id": doc["id"], "page": page, "bbox": box}
