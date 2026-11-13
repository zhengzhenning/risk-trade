.PHONY: install test lint demo api api-test import clean serve live stop board

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

# 常驻服务（后台，日志在 /tmp）
serve:
	PYTHONPATH=src nohup .venv/bin/uvicorn a_share_brief.interfaces.api:create_app --factory --port 8000 > /tmp/brief_api.log 2>&1 & disown
	@echo "http://127.0.0.1:8000/board"

live:
	PYTHONPATH=src nohup .venv/bin/python -m a_share_brief.interfaces.live_loop --root work/store --interval 120 > /tmp/brief_live.log 2>&1 & disown

stop:
	-pkill -f "uvicorn a_share_brief.interfaces.api"
	-pkill -f "live_loop"

board:
	@curl -s -o /dev/null -w "board %{http_code}\n" http://127.0.0.1:8000/board
