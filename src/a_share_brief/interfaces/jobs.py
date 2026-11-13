"""任务清单：把用例包装成可执行任务，供调度器或 cron 调用。"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from ..application.usecases.build_snapshot import BuildSnapshot
from .composition import build_snapshot_usecase
from .scheduler import Job


def build_jobs(store_root: Path) -> list[Job]:
    """构建当日快照的全部任务。

    Args:
        store_root: 快照存储目录。

    Returns:
        任务列表；当前只有收盘后的快照构建。
    """

    def snapshot_action(day: date) -> str:
        usecase: BuildSnapshot = build_snapshot_usecase(store_root)
        briefing = usecase(day)
        return f"day={briefing.day} rev={briefing.revision} stocks={len(briefing.stocks)}"

    return [
        Job(name="build_snapshot", cron="08 15 * * 1-5", usecase="BuildSnapshot",
            action=snapshot_action, timeout_seconds=300, retries=2),
    ]
