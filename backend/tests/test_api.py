from fastapi.testclient import TestClient
import fitz

from backend.app.core import storage
from backend.app.main import app
from backend.app.api import routes

from .test_detectors import SAMPLES


def test_review_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA", tmp_path)
    original_worker = routes.run_worker

    def isolated_worker(*args, timeout):
        monkeypatch.setenv("PALIMPSEST_DATA", str(tmp_path))
        return original_worker(*args, timeout=timeout)

    monkeypatch.setattr(routes, "run_worker", isolated_worker)
    with TestClient(app) as client:
        assert client.get("/healthz").json()["status"] == "ok"
        draft = client.post("/api/cases", json={}).json()["id"]
        base = f"/api/cases/{draft}"
        assert client.post(base+"/documents", files={"files":("bad.pdf",b"invalid","application/pdf")}).status_code == 422
        slip = SAMPLES/"ravi_case"/"01-salary-slip.pdf"
        assert client.post(base+"/documents", files={"files":(slip.name,slip.read_bytes(),"application/pdf")}).status_code == 201
        assert client.post(base+"/analyze").status_code == 202
        assert client.get(base+"/status").json()["state"] == "ready"
        case = client.get(base+"/findings").json()
        doc_id = case["documents"][0]["id"]
        assert client.get(f"/api/documents/{doc_id}/render?page=1&revision=1").content.startswith(b"\x89PNG")
        assert client.get(base+"/crossmatrix").status_code == 200
        assert client.post(base+"/decision", json={"action":"Escalate"}).status_code == 422
        assert client.post(base+"/decision", json={"action":"Request more documents","reason":"Confirm original payroll record."}).status_code == 200
        audit = client.get(f"/api/audit/verify?case_id={draft}").json()
        assert audit["valid"] and audit["entries"][-1]["event"]["action"] == "reviewer_decision"
        report = client.get(base+"/dossier.pdf")
        with fitz.open(stream=report.content, filetype="pdf") as pdf:
            assert "Human decision" in "".join(page.get_text() for page in pdf)
        assert client.delete(base).status_code == 204
        assert client.get(base+"/status").status_code == 404
        sample = client.post("/api/samples/injection/load")
        assert sample.status_code == 202
        assert client.get(f"/api/cases/{sample.json()['id']}/status").json()["state"] == "ready"
        degraded = client.post("/api/samples/degraded/load").json()["id"]
        doc = client.get(f"/api/cases/{degraded}/findings").json()["documents"][0]["id"]
        source = client.get(f"/api/documents/{doc}/render").content
        heatmap = client.get(f"/api/documents/{doc}/render?layer=ela").content
        assert source.startswith(b"\x89PNG") and heatmap.startswith(b"\x89PNG")
        assert heatmap != source
