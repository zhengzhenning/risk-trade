"""领域异常。

异常只在内核定义；适配器负责把外部错误翻译为这里的类型，驱动层决定出口。
"""


class DomainError(Exception):
    """领域异常基类。"""


class SnapshotNotFound(DomainError, LookupError):
    """指定交易日的快照不存在。

    Attributes:
        day: 缺失的交易日，ISO 格式字符串。
    """

    def __init__(self, day: str) -> None:
        self.day = day
        super().__init__(f"no snapshot for {day}")
