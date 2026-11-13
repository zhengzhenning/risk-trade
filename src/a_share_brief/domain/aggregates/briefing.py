"""看板快照。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .market import Index
from .pool import PoolDiff, PoolRanking
from .stock import Stock
from .theme import Theme


@dataclass(frozen=True)
class Phase:
    """威科夫阶段。"""

    start: str
    end: str
    kind: str                    # acc | wash | start | dist
    note: str = ""
    tentative: bool = False


@dataclass(frozen=True)
class Briefing:
    """当日看板快照。"""

    day: date
    rankings: tuple[PoolRanking, ...] = ()
    diffs: tuple[PoolDiff, ...] = ()
    indexes: tuple[Index, ...] = ()
    stocks: tuple[Stock, ...] = ()
    themes: tuple[Theme, ...] = ()
    phases: dict[str, tuple[Phase, ...]] = field(default_factory=dict)
    revision: int = 1

    def __post_init__(self) -> None:
        """校验快照版本号，避免非法历史写入。"""
        if self.revision < 1:
            raise ValueError(f"快照版本必须 ≥1: day={self.day} revision={self.revision}")
