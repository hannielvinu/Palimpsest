.PHONY: setup build run test samples benchmark

setup:
	python -m pip install -r requirements-dev.txt
	npm --prefix frontend ci

build:
	npm --prefix frontend run build

run:
	python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 7860

test:
	python -m pytest -q

samples:
	python scripts/make_samples.py

benchmark:
	python scripts/run_benchmark.py
	python scripts/robustness_sweep.py
