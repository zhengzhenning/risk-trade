"""按业务拆分的采集循环：每个任务独立频率、独立失败退避。"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from ..application.collectors import alert as alert_usecase
from ..application.collectors import indexes as index_usecase
from ..application.collectors import pool as pool_usecase
from ..application.collectors import quotes as quotes_usecase
from ..application.collectors import theme as theme_usecase
from ..infrastructure.eastmoney_alert import EastmoneyAlertAdapter
from ..infrastructure.eastmoney_f10 import EastmoneyThemeAdapter
from ..infrastructure.eastmoney_index import EastmoneyIndexAdapter
from ..infrastructure.eastmoney_pool import EastmoneyPoolAdapter
from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.sections import save
from .composition import quotes_port

_LOG = logging.getLogger("a_share_brief.collector")
SECTIONS = Path("work/sections")


@dataclass
class Task:
    """一个采集任务。"""

    name: str
    interval: int
    run: Callable[[], list[dict]]


def _codes() -> list[str]:
    repo = FileRepoAdapter(Path("work/store"))
    days = sorted(repo.root.glob("briefing-*.json"))
    if not days:
        return []
    day = date.fromisoformat(days[-1].stem.removeprefix("briefing-"))
    snapshot = repo.load(day)
    return [stock.base.code for stock in (snapshot.stocks if snapshot else ())]


def collect_quotes() -> list[dict]:
    codes = _codes()
    if not codes:
        return []
    return quotes_usecase.collect(quotes_port(), codes)


def collect_pool() -> list[dict]:
    return pool_usecase.collect(EastmoneyPoolAdapter())


def collect_index() -> list[dict]:
    return index_usecase.collect(EastmoneyIndexAdapter())


def collect_alert() -> list[dict]:
    return alert_usecase.collect(EastmoneyAlertAdapter(), _codes())


def collect_theme() -> list[dict]:
    return theme_usecase.collect(EastmoneyThemeAdapter(), _codes())


def build_tasks() -> list[Task]:
    """任务清单：股池 30 秒，行情/指数 30 秒，预警 60 秒，题材 600 秒。"""
    return [
        Task("pool", 30, collect_pool),
        Task("quotes", 30, collect_quotes),
        Task("index", 30, collect_index),
        Task("alert", 60, collect_alert),
        Task("theme", 600, collect_theme),
    ]


def _trading_now() -> bool:
    now = datetime.now()
    return now.weekday() < 5 and (9, 15) <= (now.hour, now.minute) <= (15, 5)


def _loop(task: Task) -> None:
    backoff = task.interval
    while True:
        if not _trading_now():
            _LOG.info("market closed, skip name=%s", task.name)
            time.sleep(1800)
            continue
        try:
            rows = task.run()
            save(SECTIONS, task.name, rows)
            _LOG.info("section saved name=%s rows=%d", task.name, len(rows))
            backoff = task.interval
        except Exception as exc:  # 单个任务失败不影响其他任务
            _LOG.warning("section failed name=%s reason=%s", task.name, exc)
            backoff = min(backoff * 2, 600)
        time.sleep(backoff)


def main() -> None:
    """启动全部采集线程。"""
    logging.basicConfig(level=logging.INFO,
                        format="ts=%(asctime)s level=%(levelname)s msg=%(message)s")
    threads = []
    for task in build_tasks():
        thread = threading.Thread(target=_loop, args=(task,), daemon=True, name=task.name)
        thread.start()
        threads.append(thread)
    _LOG.info("scheduler started tasks=%d", len(threads))
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
