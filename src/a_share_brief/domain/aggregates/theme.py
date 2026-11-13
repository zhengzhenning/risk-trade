"""题材：锚定龙头、成员、主升逻辑与切换。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .pool import PoolWindow


class ThemeCategory(str, Enum):
    """题材类别，决定炒作逻辑的主判定路径。"""

    NAME_FAMILY = "NAME_FAMILY"   # 名字系/玄学：东方、龙、羊洋阳
    INDUSTRY = "INDUSTRY"         # 产业题材
    POLICY = "POLICY"             # 政策题材
    REGION = "REGION"             # 地域题材
    EVENT = "EVENT"               # 事件驱动


class LogicLayer(str, Enum):
    """炒作逻辑层级，由强到弱。"""

    L1_NAME = "L1_NAME"           # 名字/玄学系
    L2_POSITION = "L2_POSITION"   # 题材卡位
    L3_NARRATIVE = "L3_NARRATIVE" # 个股叙事
    L4_CAPITAL = "L4_CAPITAL"     # 资金博弈
    L5_MACRO = "L5_MACRO"         # 宏观


class ThemeStatus(str, Enum):
    """题材所处阶段。"""

    BREWING = "BREWING"           # 发酵初期
    FERMENTING = "FERMENTING"     # 持续发酵
    DIVERGING = "DIVERGING"       # 高位分歧
    FADING = "FADING"             # 退潮


class StockRole(str, Enum):
    """个股在题材中的角色。"""

    DRAGON = "DRAGON"             # 龙头
    ANCHOR = "ANCHOR"             # 锚定（高度/连板最高）
    FOLLOW = "FOLLOW"             # 跟风
    INDEPENDENT = "INDEPENDENT"   # 独立逻辑


@dataclass(frozen=True)
class Theme:
    """题材：一轮行情的炒作主题与逻辑。

    Attributes:
        id: 稳定标识，如 ``east-family``。
        name: 题材名，如 ``东方系``。
        category: 类别（名字系/产业/政策/地域/事件）。
        layer: 主要炒作逻辑层级。
        narrative: 一句话炒作逻辑，说明为什么涨。
        keywords: 触发关键词，用于涨停池与新闻扫描。
        anchor_code: 锚定龙头代码，题材由涨幅榜龙头定义。
        anchor_name: 锚定龙头简称。
        window: 锚点来源窗口（月度前十 / 近 60 日前七）。
        rank: 锚点在窗口中的名次。
        sector: 所属东财行业（板块效应载体）。
        members: 带出的成员（梯队/跟风）。
        logic: 主升逻辑三段式。
        status: 当前阶段。
        start_day: 本轮启动日。
        end_day: 退潮日，未结束为 None。
        evidence: 证据列表（涨停池系内标的、新闻链接）。
    """

    id: str
    name: str
    category: ThemeCategory = ThemeCategory.INDUSTRY
    layer: LogicLayer = LogicLayer.L2_POSITION
    narrative: str = ""
    keywords: tuple[str, ...] = ()
    anchor_code: str = ""
    anchor_name: str = ""
    window: PoolWindow = PoolWindow.MONTH
    rank: int = 99
    sector: str = ""
    members: tuple[ThemeMember, ...] = ()
    logic: MainUpLogic | None = None
    status: ThemeStatus = ThemeStatus.BREWING
    start_day: date | None = None
    end_day: date | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ThemeMember:
    """题材成员：由龙头带出的跟风/梯队标的。

    Attributes:
        code: 标的代码。
        name: 简称。
        role: 在题材中的角色。
        is_anchor: 是否为锚定龙头（涨幅榜排名最高）。
        rank_in_pool: 在窗口排名中的名次，非池内为 None。
        range_pct: 窗口区间涨跌幅（%）。
        limit_up_days: 连板数，非涨停为 0。
        via: 归属依据，如「同 F10 三级行业」「涨停池同系」。
    """

    code: str
    name: str
    role: StockRole = StockRole.FOLLOW
    is_anchor: bool = False
    rank_in_pool: int | None = None
    range_pct: float = 0.0
    limit_up_days: int = 0
    via: str = ""


@dataclass(frozen=True)
class MainUpLogic:
    """主升逻辑：从点到面的三段式。

    Attributes:
        trigger: 触发：龙头为什么先涨。
        diffusion: 扩散：题材如何带出板块。
        positioning: 卡位：龙头在题材中的位置与稀缺性。
        evidence: 可核对证据（涨停池、连板、资讯链接）。
    """

    trigger: str = ""
    diffusion: str = ""
    positioning: str = ""
    evidence: tuple[str, ...] = ()
