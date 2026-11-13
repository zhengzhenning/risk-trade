"""威科夫阶段判定：从日 K 归纳吸筹/启动/洗盘/派发四段。

规则简化自项目既有口径，只看价格与涨幅，不预测：
    1. 窗口内首个涨停日作为「启动」起点；
    2. 启动前 20 日为「吸筹」；
    3. 启动后到最后一个强势日；
    4. 之后出现 ≤-3% 大阴判「派发」，否则「洗盘」。
"""
from __future__ import annotations

from ..aggregates import Bar, Phase

LIMIT_UP = 9.7
STRONG = 4.0
LOOKBACK = 45


def judge(bars: tuple[Bar, ...]) -> tuple[Phase, ...]:
    """判定阶段序列。

    Args:
        bars: 按时间升序的日 K。

    Returns:
        阶段元组；数据不足 10 根时返回空。
    """
    if len(bars) < 10:
        return ()
    rows = bars[-LOOKBACK:]
    start_index = next((i for i, bar in enumerate(rows) if bar.pct >= LIMIT_UP), None)
    if start_index is None:
        return _flat(rows)

    phases = [
        Phase(start=rows[max(0, start_index - 20)].day,
              end=rows[max(0, start_index - 1)].day,
              kind="acc",
              note=f"启动前 {min(20, start_index)} 日横盘蓄势"),
    ]

    last_strong = start_index
    for i in range(start_index, len(rows)):
        if rows[i].pct >= LIMIT_UP or (rows[i].pct >= STRONG and rows[i].volume > 0):
            last_strong = i
    phases.append(Phase(
        start=rows[start_index].day,
        end=rows[last_strong].day,
        kind="start",
        note=f"{last_strong - start_index + 1} 个交易日强势拉升",
    ))

    tail = rows[last_strong + 1:]
    if tail:
        falling = any(bar.pct <= -3 for bar in tail)
        phases.append(Phase(
            start=tail[0].day,
            end=tail[-1].day,
            kind="dist" if falling else "wash",
            note="断板后大阴，派发观察" if falling else "断板后缩量整理",
            tentative=falling,
        ))
    return tuple(phases)


def _flat(rows: list[Bar]) -> tuple[Phase, ...]:
    """无涨停时的横盘判定。"""
    window = rows[-20:]
    return (Phase(start=window[0].day, end=window[-1].day, kind="acc",
                  note="近 20 日无涨停，箱体震荡"),)
