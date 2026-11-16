"""配置加载：启动时读取 config/settings.json，不在运行时注入环境变量。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path("config/settings.json")


@dataclass
class ProxySettings:
    """代理配置。"""

    enabled: bool = False
    provider: str = "qingguo"
    key: str = ""
    password: str = ""
    session_ttl_seconds: int = 120


@dataclass
class Settings:
    """全局配置。"""

    store_root: Path = Path("work/store")
    archives: Path = Path("archives")
    proxy: ProxySettings = field(default_factory=ProxySettings)


def load_settings(path: Path | None = None) -> Settings:
    """读取配置文件。

    Args:
        path: 配置文件路径，默认 ``config/settings.json``。

    Returns:
        配置对象；文件不存在时使用默认值（直连）。
    """
    target = Path(path or DEFAULT_PATH)
    if not target.exists():
        return Settings()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return Settings()
    proxy = raw.get("proxy") or {}
    return Settings(
        store_root=Path(raw.get("store_root") or "work/store"),
        archives=Path(raw.get("archives") or "archives"),
        proxy=ProxySettings(
            enabled=bool(proxy.get("enabled", False)),
            provider=str(proxy.get("provider") or "qingguo"),
            key=str(proxy.get("key") or ""),
            password=str(proxy.get("password") or ""),
            session_ttl_seconds=int(proxy.get("session_ttl_seconds") or 120),
        ),
    )
