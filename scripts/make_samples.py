from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.generator.documents import make_samples

if __name__ == "__main__":
    make_samples(ROOT / "data" / "samples")
    print("Generated Meena, Ravi, hidden instruction and degraded cases.")
