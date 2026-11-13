"""领域服务：纯函数，无 IO。

pool          股池差分与矩阵
theme_cluster 题材聚类（以点带面）
theme_switch  题材切换与校验
security      代码到交易所/板块映射
"""
from __future__ import annotations

from .pool import diff, matrix
from .security import board_of, exchange_of
from .theme_cluster import cluster_themes
from .theme_switch import ThemeConflict, active_theme, detect_switches, validate_segments

__all__ = [
    "ThemeConflict",
    "active_theme",
    "board_of",
    "cluster_themes",
    "detect_switches",
    "diff",
    "exchange_of",
    "matrix",
    "validate_segments",
]
