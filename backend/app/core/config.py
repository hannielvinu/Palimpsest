import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(os.getenv("PALIMPSEST_DATA", ROOT / "runtime")).resolve()
DEMO_ONLY = os.getenv("PALIMPSEST_DEMO_ONLY", "0") == "1"
MAX_FILES = 8
MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 6
MAX_PIXELS = 18_000_000
STEPS = ["Ingest", "Classify", "Extract", "Visual forensics", "Context", "Cross-document", "Evidence", "Dossier"]
