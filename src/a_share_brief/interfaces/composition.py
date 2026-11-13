"""组合根：唯一装配依赖的地方，用例不感知具体实现。"""
from __future__ import annotations

from pathlib import Path

from ..application.usecases.build_snapshot import BuildSnapshot
from ..application.usecases.build_view import BuildView
from ..infrastructure.eastmoney import EastmoneyAdapter
from ..infrastructure.eastmoney_alert import EastmoneyAlertAdapter
from ..infrastructure.eastmoney_f10 import EastmoneyThemeAdapter
from ..infrastructure.eastmoney_index import EastmoneyIndexAdapter
from ..infrastructure.eastmoney_pool import EastmoneyPoolAdapter
from ..infrastructure.fallback import FallbackQuotes
from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.html_renderer import HtmlRendererAdapter
from ..infrastructure.tencent import TencentAdapter
from ..infrastructure.tencent_kline import TencentKLineAdapter


def snapshot_store(root: Path) -> FileRepoAdapter:
    """创建快照仓库。

    Args:
        root: 存储目录。

    Returns:
        文件快照仓库。
    """
    return FileRepoAdapter(root)


def quotes_port() -> FallbackQuotes:
    """行情端口：东财为主、腾讯兜底。

    Returns:
        主备组合行情端口。
    """
    return FallbackQuotes(EastmoneyAdapter(), TencentAdapter())


def build_snapshot_usecase(root: Path) -> BuildSnapshot:
    """装配写路径用例。

    Args:
        root: 快照存储目录。

    Returns:
        已注入真实适配器的用例。
    """
    return BuildSnapshot(
        pools=EastmoneyPoolAdapter(),
        quotes=quotes_port(),
        repo=snapshot_store(root),
        alerts=EastmoneyAlertAdapter(),
        themes=EastmoneyThemeAdapter(),
        indexes=EastmoneyIndexAdapter(),
    )


def build_view_usecase(root: Path) -> BuildView:
    """装配读路径用例。

    Args:
        root: 快照存储目录。

    Returns:
        已注入仓库与渲染器的用例。
    """
    return BuildView(snapshot_store(root), HtmlRendererAdapter())


def kline_port() -> TencentKLineAdapter:
    """K 线端口。

    Returns:
        腾讯前复权日 K 适配器。
    """
    return TencentKLineAdapter()
