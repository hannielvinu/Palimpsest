from collections import Counter
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.core.hashing import sha256
from backend.app.pipeline.ingest import inspect_upload
from backend.app.pipeline.run import analyze
from data.generator.documents import document, make_pair

BASE = ROOT / "data" / "benchmark"
LABEL = "Synthetic, self-generated; a blind human-tampered set is planned."
KINDS = ("clean",)*10 + ("revision",)*3 + ("arithmetic",)*2 + ("credit",)*2 + ("signature", "injection", "flattened")
DETECTORS = {"revision": ["font_baseline","layer_peel","arithmetic","salary_credit"],
             "arithmetic": ["arithmetic","salary_credit"], "credit":["salary_credit"],
             "signature":["signature_reuse"], "injection":["hidden_text"], "flattened":["layer_peel"]}


def fixtures(folder):
    rng = random.Random(8714)
    kinds = list(KINDS)
    rng.shuffle(kinds)
    truth = {}
    for index, kind in enumerate(kinds, 1):
        case = f"case-{index:02d}"
        path = folder / case
        seed = rng.randrange(100, 8000)
        net = rng.randrange(33, 121) * 1000
        delta = rng.randrange(5, 30) * 1000
        alias = f"Anika {chr(65+index)}."
        name = f"Anika {chr(65+index)}aran"
        if kind == "injection":
            path.mkdir(parents=True, exist_ok=True)
            document(path/"01-proof.pdf", "Address Proof",
                     [("Name", name), ("Address", f"{index} Example Road, Fictional City")], seed, hidden=True)
        else:
            make_pair(path, name=name, alias=alias, seed=seed, net=net,
                      edit=net+delta if kind=="revision" else None,
                      slip_net=net+delta if kind=="arithmetic" else None,
                      bank_net=net+delta if kind=="credit" else None, repeated_signature=kind=="signature",
                      blur=(1 if index % 3 == 0 else 0) if kind=="clean" else 0)
            if kind == "flattened":
                # A plausible revised slip with no retained history, consistent arithmetic and matching credit.
                make_pair(path, name=name, alias=alias, seed=seed, net=net+delta)
        truth[case] = {"positive": kind!="clean", "kind":kind, "expected": DETECTORS.get(kind, [])}
    return truth


def run_case(paths):
    records = []
    for i, path in enumerate(paths, 1):
        raw = path.read_bytes()
        name,mime = inspect_upload(path.name,raw)
        records.append({"id":f"d{i}","name":name,"mime":mime,"sha256":sha256(raw),"original":raw})
    return analyze(records)


def save(name, result, md):
    out = BASE / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    (out / f"{name}.md").write_text(md + "\n", encoding="utf8")
    print(md)


def main():
    blind = BASE / "blind"
    if (blind / "truth.json").is_file():
        folder = blind / "inputs"
        truth = json.loads((blind/"truth.json").read_text(encoding="utf8"))
        label = "Owner-supplied blind-set inputs and separate labels."
    else:
        folder = BASE/"inputs"
        truth = fixtures(folder)
        (BASE/"truth.json").write_text(json.dumps(truth, indent=2) + "\n", encoding="utf8")
        label = LABEL
    counts = Counter()
    hits, expected = Counter(), Counter()
    details = []
    for case, target in sorted(truth.items()):
        result = run_case(sorted(p for p in (folder/case).iterdir() if p.suffix.lower() in {".pdf",".png",".jpg",".jpeg"}))
        active = {e["detector"] for e in result["findings"] if e["points"]}
        flagged = bool(active)
        counts["caught" if flagged else "missed" if target["positive"] else "clear"] += int(target["positive"] or not flagged)
        counts["genuine"] += int(not target["positive"])
        counts["false_alarms"] += int(flagged and not target["positive"])
        counts["cannot_determine"] += int(result["summary"]["concern"] == "CANNOT DETERMINE")
        expected.update(target["expected"])
        hits.update(active.intersection(target["expected"]))
        details.append({"case":case, "kind":target["kind"], "positive":target["positive"], "flagged":flagged,
                        "concern":result["summary"]["concern"], "observed_detectors":sorted(active)})
    detector_rows = {key:{"hits":hits[key],"expected":count,"rate":round(hits[key]/count, 4)} for key,count in sorted(expected.items())}
    summary = {"label":label, "total":len(truth), "caught":counts["caught"], "missed":counts["missed"],
               "genuine":counts["genuine"], "false_alarms":counts["false_alarms"], "cannot_determine":counts["cannot_determine"],
               "per_detector":detector_rows, "cases":details}
    md = [f"# Benchmark\n\n{label}", "A flag means at least one positive-point finding. Per-detector denominators use separate ground truth.",
          "| Cases | Changed caught | Changed missed | Genuine flagged | Cannot determine |",
          "|---:|---:|---:|---:|---:|",
          f"| {len(truth)} | {counts['caught']} | {counts['missed']} | {counts['false_alarms']} / {counts['genuine']} | {counts['cannot_determine']} |",
          "", "| Detector | Expected hits | Hit rate |", "|---|---:|---:|"]
    md += [f"| {key} | {row['hits']} / {row['expected']} | {row['rate']:.0%} |" for key,row in detector_rows.items()]
    save("benchmark", summary, "\n".join(md[:2]) + "\n\n" + "\n".join(md[2:]))


if __name__ == "__main__":
    main()
