"""异动预警采集用例。"""
from __future__ import annotations

from collections.abc import Sequence


def collect(alerts, codes: Sequence[str]) -> list[dict]:
    """采集异动预警。

    Args:
        alerts: 预警端口。
        codes: 标的代码。

    Returns:
        代码与级别列表。
    """
    rows = alerts.unusual(codes)
    return [{"code": code, "level": alert.level.value if alert and alert.level else None}
            for code, alert in rows.items()]
