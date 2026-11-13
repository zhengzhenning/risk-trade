.PHONY: install test lint demo api api-test import clean

install:
	python3 -m pip install -e ".[dev]"

test:
	PYTHONPATH=src python3 -m pytest -q tests

api-test:
	PYTHONPATH=src .venv/bin/python -m pytest -q tests

lint:
	python3 -m ruff check src tests

demo:
	PYTHONPATH=src python3 -m a_share_brief.interfaces.cli build --day 2026-11-13 --root work/store
	PYTHONPATH=src python3 -m a_share_brief.interfaces.cli view  --day 2026-11-13 --root work/store

import:
	PYTHONPATH=src python3 scripts/import_archives.py --archives archives --out work/store

api:
	PYTHONPATH=src .venv/bin/uvicorn a_share_brief.interfaces.api:create_app --factory --port 8000

clean:
	rm -rf work/store .pytest_cache
