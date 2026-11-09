from pathlib import Path
from collections import defaultdict

import pytest

from backend.app.core.audit import append, verify
from backend.app.core.hashing import sha256
from backend.app.core import storage
from backend.app.detectors.arithmetic import check
from backend.app.detectors.layer_peel import revisions
from backend.app.pipeline.crosscheck import name_match
from backend.app.pipeline.extract import amount
from backend.app.pipeline.ingest import inspect_upload
from backend.app.pipeline.run import analyze

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"


def record(path):
    raw = path.read_bytes()
    name, mime = inspect_upload(path.name, raw)
    return {"id": path.stem, "name": name, "mime": mime, "sha256": sha256(raw), "original": raw}


@pytest.fixture(scope="module")
def samples():
    return {folder.name: analyze([record(path) for path in sorted(folder.iterdir())]) for folder in SAMPLES.iterdir()}


@pytest.mark.parametrize("value,expected", [("INR 1,00,000.50", "100000.50"), ("100,000", "100000.00"),
                                            ("₹ 9,876", "9876.00"), ("1,0,00", None), ("unknown", None)])
def test_amount(value, expected):
    assert amount(value) == expected


def test_name_matching():
    assert name_match("Meena Krishnan", "Meena K.") == "variant"
    assert name_match("Dr. Ravi Narayanan", "Narayanan Ravi") == "variant"
    assert name_match("Meena Krishnan", "Kiran Krishnan") == "conflict"


def test_arithmetic_tolerance():
    base = {"document_id": "d", "page": 1, "bbox": [.1,.2,.3,.4], "confidence": 1}
    fields = {key: base | {"normalized": value} for key, value in {"gross":"52500", "deductions":"4500", "net":"48000.90"}.items()}
    assert check(fields) is None
    fields["net"]["normalized"] = "88000"
    assert check(fields)["values"] == {"expected":"48000", "reported":"88000"}


def test_ravi_findings(samples):
    result = samples["ravi_case"]
    by_detector = defaultdict(list)
    for item in result["findings"]:
        by_detector[item["detector"]].append(item)
    assert result["summary"]["concern"] == "HIGH"
    assert {"font_baseline", "arithmetic", "salary_credit", "signature_reuse", "layer_peel"} <= set(by_detector)
    change = by_detector["layer_peel"][0]["values"]
    assert "48,000" in change["before"] and "88,000" in change["current"]
    assert by_detector["layer_peel"][0]["bbox"] is not None
    assert by_detector["signature_reuse"][0]["related"]
    assert len(revisions((SAMPLES / "ravi_case" / "01-salary-slip.pdf").read_bytes())) == 1


def test_meena_injection_degraded(samples):
    meena = samples["meena_case"]
    assert meena["summary"]["concern"] == "LOW"
    assert "name_variant" in {item["detector"] for item in meena["findings"]}
    assert all(item["points"] == 0 for item in meena["findings"])
    injection = samples["injection_case"]
    assert any(item["detector"] == "hidden_text" and item["bbox"] and item["points"] > 0 for item in injection["findings"])
    assert not any("approve" in field["value"] for doc in injection["documents"] for field in doc["fields"])
    assert samples["degraded_case"]["summary"]["concern"] == "CANNOT DETERMINE"


def test_chain_tamper(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA", tmp_path)
    storage.init()
    with storage.db(write=True) as conn:
        conn.execute("INSERT INTO cases(id,title,state,created) VALUES('case','test','draft','now')")
        append(conn, "case", "upload", {"sha256": "example"})
        head = append(conn, "case", "finding", {"id": "E-001"})
        assert verify(conn.execute("SELECT * FROM audit ORDER BY seq").fetchall())["head"] == head
        conn.execute("UPDATE audit SET payload='{}' WHERE seq=1")
        assert not verify(conn.execute("SELECT * FROM audit ORDER BY seq").fetchall())["valid"]
