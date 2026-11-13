"""HTTP 应用装配：只创建 FastAPI 实例并注册路由。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from ..infrastructure.file_repo import FileRepoAdapter
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
    register_routes(app, root, FileRepoAdapter(root))
    return app
