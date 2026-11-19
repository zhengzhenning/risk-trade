"""快照刷新循环：交易时段高频，收盘后只做一次确认，夜间静默。"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from datetime import time as clock
from pathlib import Path

from ..infrastructure.config import load_settings
from .composition import build_snapshot_usecase

_LOG = logging.getLogger("a_share_brief.live")

OPENING = clock(9, 15)
LUNCH = clock(11, 30)
AFTERNOON = clock(13, 0)
CLOSING = clock(15, 5)


def _trading(now: datetime) -> bool:
    """是否处于竞价时段；午休（11:30–13:00）不算交易时段。

    Args:
        now: 判定时刻。

    Returns:
        交易日的上午或下午时段返回 True。
    """
    if now.weekday() >= 5:
        return False
    stamp = now.time()
    return OPENING <= stamp <= LUNCH or AFTERNOON <= stamp <= CLOSING


def _in_lunch(now: datetime) -> bool:
    """是否处于午休，用于把休眠缩短到 1 分钟以便 13:00 准时恢复。

    Args:
        now: 判定时刻。

    Returns:
        工作日午休返回 True。
    """
    return now.weekday() < 5 and LUNCH < now.time() < AFTERNOON


def refresh_once(root: Path) -> None:
    """重建一次当日快照。"""
    briefing = build_snapshot_usecase(root)(date.today())
    _LOG.info("snapshot refreshed day=%s rev=%d stocks=%d",
              briefing.day, briefing.revision, len(briefing.stocks))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(load_settings().store_root))
    parser.add_argument("--interval", type=int, default=120, help="交易时段间隔（秒）")
    parser.add_argument("--closed-interval", type=int, default=1800, help="收盘后静默间隔（秒）")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="ts=%(asctime)s level=%(levelname)s msg=%(message)s")
    root = Path(args.root)
    last_close_day: date | None = None

    while True:
        now = datetime.now()
        today = now.date()
        trading = _trading(now)

        if trading:
            try:
                refresh_once(root)
            except Exception as exc:  # 单次失败不中断循环
                _LOG.warning("refresh failed reason=%s", exc)
            if args.once:
                return
            _sleep = args.interval
        else:
            # 收盘后只补一次收盘快照，之后不再重复抓取（K 线另有按天缓存）
            after_close = now.weekday() < 5 and now.time() > CLOSING
            if after_close and last_close_day != today:
                try:
                    refresh_once(root)
                    last_close_day = today
                    _LOG.info("closed snapshot captured day=%s", today)
                except Exception as exc:
                    _LOG.warning("closed refresh failed reason=%s", exc)
            if args.once:
                return
            # 午休只睡 1 分钟，保证 13:00 准时恢复；其余时段按收盘间隔静默
            _sleep = 60 if _in_lunch(now) else args.closed_interval

        import time as _time

        _time.sleep(_sleep)


if __name__ == "__main__":
    main()
