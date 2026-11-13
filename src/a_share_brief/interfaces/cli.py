"""驱动：命令行入口。

只负责参数解析与依赖装配；业务流程在 use cases，异常在此映射为退出码。
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from ..application.usecases.build_snapshot import BuildSnapshot
from ..domain.errors import SnapshotNotFound
from .composition import build_snapshot_usecase, build_view_usecase, snapshot_store

_LOG = logging.getLogger("a_share_brief")


class _EmptyPools:
    """P1 占位股池：真实实现待接入选股器适配器。"""

    def month_top(self, n: int = 10) -> list:
        return []

    def d60_top(self, n: int = 7) -> list:
        return []


class _EmptyQuotes:
    """P1 占位行情：真实实现待接入行情适配器。"""

    def snapshot(self, codes):
        return {}


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="ts=%(asctime)s level=%(levelname)s module=%(name)s msg=%(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    """命令行主入口。

    Args:
        argv: 参数列表，默认取 ``sys.argv[1:]``。

    Returns:
        进程退出码：0 成功，1 业务错误，2 参数错误。

    Raises:
        SystemExit: argparse 在参数非法时抛出。
    """
    parser = argparse.ArgumentParser(prog="a-share-brief")
    parser.add_argument("cmd", choices=["build", "view"])
    parser.add_argument("--day", default=date.today().isoformat())
    parser.add_argument("--root", default="work/store")
    parser.add_argument("--demo", action="store_true", help="用空适配器离线演示")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    day = date.fromisoformat(args.day)

    if args.cmd == "build":
        if args.demo:
            BuildSnapshot(_EmptyPools(), _EmptyQuotes(), snapshot_store(Path(args.root)))(day)
        else:
            build_snapshot_usecase(Path(args.root))(day)
        print(f"snapshot saved: {day}")
        return 0

    try:
        print(build_view_usecase(Path(args.root))(day)[:200])
    except SnapshotNotFound as exc:
        _LOG.error("view failed day=%s reason=%s", day, exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
