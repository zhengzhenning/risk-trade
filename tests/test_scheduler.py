"""调度器测试：成功、重试、失败记账。"""
import json
from datetime import date

from a_share_brief.interfaces.scheduler import Job, Scheduler

DAY = date(2026, 11, 13)


def _scheduler(tmp_path, action, retries=2):
    job = Job(name="build_snapshot", cron="08 15 * * 1-5", usecase="BuildSnapshot",
              action=action, retries=retries)
    return Scheduler([job], tmp_path / "audit.jsonl")


def _audit_lines(tmp_path):
    return [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()]


def test_job_success_is_recorded(tmp_path):
    scheduler = _scheduler(tmp_path, lambda day: f"day={day} rev=1")
    run = scheduler.run("build_snapshot", DAY)

    assert run.status == "ok"
    assert run.detail["attempt"] == 1
    rows = _audit_lines(tmp_path)
    assert rows[0]["job"] == "build_snapshot"
    assert rows[0]["day"] == "2026-11-13"
    assert rows[0]["status"] == "ok"


def test_job_retries_then_fails(tmp_path):
    calls = {"n": 0}

    def boom(day):
        calls["n"] += 1
        raise RuntimeError("接口失败")

    scheduler = _scheduler(tmp_path, boom, retries=2)
    run = scheduler.run("build_snapshot", DAY)

    assert calls["n"] == 3            # 首次 + 2 次重试
    assert run.status == "failed"
    assert "RuntimeError" in run.detail["error"]


def test_unknown_job_raises(tmp_path):
    scheduler = _scheduler(tmp_path, lambda day: "ok")
    try:
        scheduler.run("nope", DAY)
    except KeyError:
        return
    raise AssertionError("未注册任务应抛 KeyError")
