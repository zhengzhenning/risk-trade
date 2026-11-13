"""盘中循环：每 N 秒重建当日快照，供 /board 与 API 读取。"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date, datetime
from datetime import time as clock
from pathlib import Path

from .composition import build_snapshot_usecase

_LOG = logging.getLogger("a_share_brief.live")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="work/store")
    parser.add_argument("--interval", type=int, default=120)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="ts=%(asctime)s level=%(levelname)s msg=%(message)s")
    root = Path(args.root)
    opening, closing = clock(9, 15), clock(15, 5)
    while True:
        now = datetime.now()
        trading = now.weekday() < 5 and opening <= now.time() <= closing
        try:
            briefing = build_snapshot_usecase(root)(date.today())
            _LOG.info("snapshot refreshed day=%s rev=%d stocks=%d",
                      briefing.day, briefing.revision, len(briefing.stocks))
        except Exception as exc:  # 单次失败不影响循环
            _LOG.warning("snapshot refresh failed reason=%s", exc)
        if args.once:
            return
        # 非交易时段只做一次收盘确认，随后放慢到 10 分钟
        time.sleep(args.interval if trading else 600)


if __name__ == "__main__":
    main()
