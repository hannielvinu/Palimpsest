"""Exercise the same API against a local container or deployed base URL."""
import argparse
import json
from time import monotonic, sleep
from urllib.request import Request, urlopen


def smoke(base):
    def request(path, method="GET", body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = Request(base.rstrip("/") + path, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=35) as response:
            return json.load(response) if response.headers.get_content_type()=="application/json" else response.read()

    for name, concern in {"meena":"LOW", "ravi":"HIGH", "injection":"MODERATE", "degraded":"CANNOT DETERMINE"}.items():
        case_id = request(f"/api/samples/{name}/load","POST")["id"]
        path = f"/api/cases/{case_id}"
        deadline = monotonic() + 75
        while monotonic() < deadline:
            status = request(path+"/status")["state"]
            if status=="ready":
                break
            assert status=="processing", (name,status)
            sleep(.4)
        else:
            raise TimeoutError(name)
        result = request(path+"/findings")
        assert result["summary"]["concern"] == concern, (name,result["summary"])
        if name=="ravi":
            slip = result["documents"][0]["id"]
            assert request(f"/api/documents/{slip}/render?page=1&revision=1").startswith(b"\x89PNG")
            assert any("48,000" in e["values"].get("before","") and "88,000" in e["values"].get("current","") for e in result["findings"])
            request(path+"/decision","POST",{"action":"Request more documents","reason":"Confirm the original payroll file."})
            assert request(path+"/dossier.pdf").startswith(b"%PDF-")
        audit = request(f"/api/audit/verify?case_id={case_id}")
        assert audit["valid"] and audit["count"] > 8
        request(path,"DELETE")
        print(f"{name}: {concern}, audit verified")
    assert b"/assets/" in request("/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    for _ in range(60):
        try:
            with urlopen(args.url.rstrip("/")+"/healthz", timeout=3) as response:
                if json.load(response).get("status") == "ok":
                    break
        except (ValueError, OSError):
            sleep(2)
    else:
        raise RuntimeError("Health endpoint did not become ready.")
    smoke(args.url)
