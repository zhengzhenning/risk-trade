"""HTTP 应用装配：只创建 FastAPI 实例并注册路由。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.tencent_kline import TencentKLineAdapter
from .api_aux import register_aux
from .api_board import register_board
from .api_index import register_index
from .api_routes import register_routes


def create_app(store_root: Optional[Path] = None) -> FastAPI:
    """创建 HTTP 应用。

    Args:
        store_root: 快照存储目录；缺省读环境变量 ``BRIEF_STORE``，再缺省 ``work/store``。

    Returns:
        FastAPI 应用实例。
    """
    root = Path(store_root or os.environ.get("BRIEF_STORE", "work/store"))
    app = FastAPI(title="A 股每日看板", version="0.1.0")
    klines = TencentKLineAdapter()
    repo = FileRepoAdapter(root)
    register_routes(app, root, repo, klines)
    register_index(app, klines)
    register_aux(app, root)
    register_board(app, Path(os.environ.get("BRIEF_ARCHIVES", "archives")), root)
    return app
