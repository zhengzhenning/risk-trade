.PHONY: install test demo lint clean

install:
	python3 -m pip install -e ".[dev]"

test:
	PYTHONPATH=src python3 -m pytest -q tests

demo:
	PYTHONPATH=src python3 -m a_share_brief.interfaces.cli build --day 2026-11-12 --root work/store
	PYTHONPATH=src python3 -m a_share_brief.interfaces.cli view  --day 2026-11-12 --root work/store

lint:
	python3 -m ruff check src tests

clean:
	rm -rf work/store .pytest_cache
