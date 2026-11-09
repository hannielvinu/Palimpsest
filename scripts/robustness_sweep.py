from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
import numpy as np
from PIL import Image, ImageFilter

from run_benchmark import run_case, save
from data.generator.documents import make_pair


def main():
    conditions = ["clean", "blur", "rotation", "JPEG compression", "noise"]
    rows = [{"condition":name,"total":0,"flagged":0,"cannot_determine":0} for name in conditions]
    rng = np.random.default_rng(751)
    with TemporaryDirectory() as folder:
        root = Path(folder)
        for index in range(5):
            case = root / str(index)
            make_pair(case, name=f"Mira Example{chr(65+index)}", seed=400+index, net=47000+index*1100)
            with fitz.open(case/"01-salary-slip.pdf") as pdf:
                pixmap = pdf[0].get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
                original = Image.frombytes("RGB", (pixmap.width,pixmap.height), pixmap.samples)
            noise = rng.normal(0, 12+index*3, (original.height, original.width, 3))
            variants = [original, original.filter(ImageFilter.GaussianBlur(1.5 + index*.55)),
                        original.rotate(1.5+index*.85,fillcolor="white"),
                        original, Image.fromarray(np.clip(np.asarray(original)+noise,0,255).astype(np.uint8))]
            for i, (row,image) in enumerate(zip(rows,variants)):
                path = case / ("variant.jpg" if i==3 else "variant.png")
                image.save(path, **({"quality":36-index*5} if i==3 else {}))
                result = run_case([path,case/"02-bank-statement.pdf"])
                row["total"] += 1
                row["flagged"] += int(any(e["points"] for e in result["findings"]))
                row["cannot_determine"] += int(result["summary"]["concern"]=="CANNOT DETERMINE")
                path.unlink()
    md = ["# Robustness sweep", "", "Five genuine synthetic inputs per condition. A false alarm is any positive-point finding.",
          "", "| Condition | False alarms | Rate | Cannot determine |", "|---|---:|---:|---:|"]
    for row in rows:
        row["rate"] = row["flagged"]/row["total"]
        md.append(f"| {row['condition']} | {row['flagged']} / {row['total']} | {row['rate']:.0%} | {row['cannot_determine']} |")
    save("robustness", {"conditions":rows}, "\n".join(md))


if __name__ == "__main__":
    main()
