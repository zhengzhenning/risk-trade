"""驱动：定时任务注册表。任务=用例，cron 只决定何时跑。"""
from __future__ import annotations

JOBS = {
    "refresh_live": {"cron": "*/1 9-11,13-15 * * 1-5", "usecase": "RefreshLive"},
    "build_snapshot": {"cron": "8 15 * * 1-5", "usecase": "BuildSnapshot"},
}


def list_jobs() -> dict:
    return JOBS
