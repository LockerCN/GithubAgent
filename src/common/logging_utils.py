"""控制台日志初始化工具。"""

from __future__ import annotations

import logging


def configure_logging(level: int | str = logging.INFO) -> None:
    """初始化统一的控制台日志格式。"""

    normalized_level = _normalize_level(level)
    logging.basicConfig(
        level=normalized_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def _normalize_level(level: int | str) -> int:
    """将字符串或整数日志级别转换为 logging 可识别的值。"""

    if isinstance(level, int):
        return level

    candidate = getattr(logging, level.upper(), None)
    if isinstance(candidate, int):
        return candidate

    raise ValueError(f"不支持的日志级别: {level}")
