"""任务注册表与执行器：只负责何时跑、跑哪个用例、如何记账。"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Job:
    """任务定义。

    Attributes:
        name: 任务名，全局唯一。
        cron: 触发时间（分 时 日 月 周），当前支持「每日 HH:MM」的简化形式。
        usecase: 用例名，便于排查。
        action: 可调用对象，由组合根注入。
        timeout_seconds: 超时上限。
        retries: 失败重试次数。
    """

    name: str
    cron: str
    usecase: str
    action: Callable[[date], object]
    timeout_seconds: int = 300
    retries: int = 2


@dataclass
class JobRun:
    """一次执行记录。

    Attributes:
        job: 任务名。
        day: 业务日期。
        started_at: 开始时间。
        finished_at: 结束时间。
        status: running / ok / failed。
        detail: 结果摘要或错误信息。
    """

    job: str
    day: date
    started_at: str
    finished_at: str = ""
    status: str = "running"
    detail: dict = field(default_factory=dict)


class Scheduler:
    """按注册表执行任务并记录审计。

    Args:
        jobs: 任务列表。
        audit_path: 审计文件路径，追加写入 JSONL。
    """

    def __init__(self, jobs: list[Job], audit_path: Path) -> None:
        self._jobs = {job.name: job for job in jobs}
        self._audit = Path(audit_path)
        self._audit.parent.mkdir(parents=True, exist_ok=True)

    def jobs(self) -> list[Job]:
        """返回全部任务定义。"""
        return list(self._jobs.values())

    def run(self, name: str, day: date) -> JobRun:
        """执行单个任务并记账。

        Args:
            name: 任务名。
            day: 业务日期。

        Returns:
            执行记录。

        Raises:
            KeyError: 任务未注册。
        """
        job = self._jobs[name]
        run = JobRun(job=job.name, day=day, started_at=datetime.now().isoformat(timespec="seconds"))
        last_error: Exception | None = None
        for attempt in range(1, job.retries + 2):
            try:
                result = job.action(day)
                run.status = "ok"
                run.detail = {"attempt": attempt, "result": str(result)[:200]}
                last_error = None
                break
            except Exception as exc:  # 任务边界：记录后重试或标记失败
                last_error = exc
                _LOG.warning("job failed job=%s day=%s attempt=%d reason=%s",
                             name, day, attempt, exc)
        if last_error is not None:
            run.status = "failed"
            run.detail = {"error": f"{type(last_error).__name__}: {last_error}"}
        run.finished_at = datetime.now().isoformat(timespec="seconds")
        self._write(run)
        return run

    def _write(self, run: JobRun) -> None:
        payload = {
            "job": run.job,
            "day": run.day.isoformat(),
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "status": run.status,
            "detail": run.detail,
        }
        with self._audit.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
