"""组合根：唯一装配依赖的地方，用例不感知具体实现。"""
from __future__ import annotations

from pathlib import Path

from ..application.usecases.build_snapshot import BuildSnapshot
from ..application.usecases.build_view import BuildView
from ..infrastructure.eastmoney import EastmoneyAdapter
from ..infrastructure.eastmoney_alert import EastmoneyAlertAdapter
from ..infrastructure.eastmoney_f10 import EastmoneyThemeAdapter
from ..infrastructure.eastmoney_index import EastmoneyIndexAdapter
from ..infrastructure.eastmoney_kline import EastmoneyKLineAdapter
from ..infrastructure.eastmoney_pool import EastmoneyPoolAdapter
from ..infrastructure.eastmoney_sector import EastmoneySectorAdapter
from ..infrastructure.fallback import FallbackQuotes
from ..infrastructure.fallback_kline import FallbackKLine
from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.html_renderer import HtmlRendererAdapter
from ..infrastructure.proxy_client import ProxyHttpClient
from ..infrastructure.qingguo_proxy import QingguoProxyPool
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


def proxy_client() -> ProxyHttpClient | None:
    """按环境变量决定是否走代理。

    Returns:
        配了 ``QG_KEY`` 与 ``QG_PASSWORD`` 时返回代理客户端，否则 None（直连）。
    """
    from ..infrastructure.config import load_settings

    settings = load_settings()
    proxy = settings.proxy
    if not proxy.enabled or not proxy.key or not proxy.password:
        return None
    return ProxyHttpClient(QingguoProxyPool(key=proxy.key, password=proxy.password,
                                            ttl=float(proxy.session_ttl_seconds)))


def quotes_port() -> FallbackQuotes:
    """行情端口：东财为主、腾讯兜底。

    Returns:
        主备组合行情端口。
    """
    client = proxy_client()
    primary = EastmoneyAdapter(fetch=client.get) if client else EastmoneyAdapter()
    return FallbackQuotes(primary, TencentAdapter())


def build_snapshot_usecase(root: Path) -> BuildSnapshot:
    """装配写路径用例。

    Args:
        root: 快照存储目录。

    Returns:
        已注入真实适配器的用例。
    """
    theme_adapter = EastmoneyThemeAdapter()
    sectors_adapter = EastmoneySectorAdapter()
    return BuildSnapshot(
        pools=EastmoneyPoolAdapter(),
        quotes=quotes_port(),
        repo=snapshot_store(root),
        alerts=EastmoneyAlertAdapter(),
        themes=theme_adapter,
        sectors=sectors_adapter,
        klines=TencentKLineAdapter(),
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


def kline_port():
    """K 线端口。

    Returns:
        腾讯前复权日 K 适配器。
    """
    client = proxy_client()
    primary = EastmoneyKLineAdapter(fetch=client.get) if client else EastmoneyKLineAdapter()
    return FallbackKLine(primary, TencentKLineAdapter())
