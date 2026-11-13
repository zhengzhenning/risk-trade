"""用例：渲染某交易日看板（读路径）。

只依赖快照仓库与渲染器两个端口，不关心 HTTP、数据库与缓存。
"""
from __future__ import annotations

from datetime import date

from ...domain.errors import SnapshotNotFound
from ..ports import BoardRenderer, SnapshotRepo


class BuildView:
    """读取当日快照并渲染 HTML。

    Args:
        repo: 快照仓库端口，只读。
        renderer: 渲染端口，把领域对象转成页面字符串。

    Raises:
        SnapshotNotFound: 快照不存在，由驱动层映射为 404。
    """

    def __init__(self, repo: SnapshotRepo, renderer: BoardRenderer) -> None:
        self._repo = repo
        self._renderer = renderer

    def __call__(self, day: date) -> str:
        """渲染指定交易日。

        Args:
            day: 交易日。

        Returns:
            HTML 字符串；内容只由库中快照决定，可重复生成。

        Raises:
            SnapshotNotFound: 库中没有该日快照。
        """
        briefing = self._repo.load(day)
        if briefing is None:
            raise SnapshotNotFound(day.isoformat())
        return self._renderer.render(briefing)
