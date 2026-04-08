# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""Repository 基类 - 提供通用的数据库访问方法"""

from typing import Any, Dict, List, Optional

import real_ladybug as lb


class BaseRepository:
    """Repository 基类

    提供通用的数据库查询方法，子类继承后实现具体的实体操作。
    """

    def __init__(self, connection: lb.Connection):
        """初始化 Repository

        Args:
            connection: 数据库连接对象
        """
        self.conn = connection

    def execute_query(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行 Cypher 查询并返回结果列表

        Args:
            query: Cypher 查询语句
            params: 查询参数

        Returns:
            查询结果列表，每个元素是一个字典
        """
        result = self.conn.execute(query, params)
        return [row for row in result]

    def execute_single(
        self, query: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """执行查询并返回单条结果

        Args:
            query: Cypher 查询语句
            params: 查询参数

        Returns:
            单条查询结果，如果没有结果则返回 None
        """
        results = self.execute_query(query, params)
        return results[0] if results else None

    def execute_write(self, query: str, params: Dict[str, Any]) -> bool:
        """执行写入操作（CREATE、UPDATE、DELETE）

        Args:
            query: Cypher 查询语句
            params: 查询参数

        Returns:
            操作是否成功
        """
        try:
            self.conn.execute(query, params)
            return True
        except Exception:
            return False

    def row_to_dict(self, row: Any, columns: List[str]) -> Dict[str, Any]:
        """将查询结果的行转换为字典

        Args:
            row: 查询结果行（元组）
            columns: 列名列表

        Returns:
            字典形式的数据
        """
        if len(row) != len(columns):
            raise ValueError(
                f"Row length {len(row)} does not match columns length {len(columns)}"
            )
        return {col: row[i] for i, col in enumerate(columns)}
