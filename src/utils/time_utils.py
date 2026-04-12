# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""时间处理工具"""

from datetime import UTC, datetime


def parse_datetime(dt_str: str | None) -> datetime | None:
    """
    解析 ISO 格式日期时间字符串

    如果字符串不含时区信息，默认视为 UTC。

    Args:
        dt_str: 日期时间字符串（ISO 格式）

    Returns:
        datetime 对象，解析失败返回 None
    """
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None
