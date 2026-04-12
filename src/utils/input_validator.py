# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""输入验证和安全检查"""

import html
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class InputValidator:
    """
    输入验证器

    用于验证和清理用户输入，防止注入攻击和恶意输入
    """

    # 最大长度限制
    MAX_PROJECT_NAME_LENGTH = 200
    MAX_REQUIREMENT_CONTENT_LENGTH = 5000
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_TEST_CASE_NAME_LENGTH = 200

    # 危险模式（用于检测潜在的注入攻击）
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # XSS
        r"javascript:",  # JavaScript 伪协议
        r"on\w+\s*=",  # 事件处理器
        r"eval\s*\(",  # eval 函数
        r"document\.",  # DOM 访问
        r"window\.",  # Window 对象
        r"alert\s*\(",  # alert 函数
        r"prompt\s*\(",  # prompt 函数
        r"confirm\s*\(",  # confirm 函数
    ]

    # SQL 注入模式
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(\-\-)",  # SQL 注释
        r";\s*\b(SELECT|INSERT|UPDATE|DELETE)",  # 多语句注入
        r"(\bor\b\s+\d+\s*=\s*\d+)",  # 布尔盲注
        r"(\bxor\b\s+\d+\s*=\s*\d+)",  # XOR 盲注
    ]

    @classmethod
    def validate_project_name(cls, name: str) -> str:
        """
        验证项目名称

        Args:
            name: 项目名称

        Returns:
            清理后的项目名称

        Raises:
            ValueError: 验证失败
        """
        if not name or not isinstance(name, str):
            raise ValueError("项目名称不能为空")

        name = name.strip()

        if len(name) == 0:
            raise ValueError("项目名称不能为空")

        if len(name) > cls.MAX_PROJECT_NAME_LENGTH:
            raise ValueError(f"项目名称长度不能超过 {cls.MAX_PROJECT_NAME_LENGTH} 字符")

        # 检查危险模式
        if cls._contains_dangerous_patterns(name):
            logger.warning("检测到项目名称包含潜在危险内容")
            raise ValueError("项目名称包含不安全的内容")

        return name

    @classmethod
    def validate_requirement_content(cls, content: str) -> str:
        """
        验证需求内容

        Args:
            content: 需求内容

        Returns:
            清理后的需求内容

        Raises:
            ValueError: 验证失败
        """
        if not content or not isinstance(content, str):
            raise ValueError("需求内容不能为空")

        content = content.strip()

        if len(content) == 0:
            raise ValueError("需求内容不能为空")

        if len(content) > cls.MAX_REQUIREMENT_CONTENT_LENGTH:
            raise ValueError(
                f"需求内容长度不能超过 {cls.MAX_REQUIREMENT_CONTENT_LENGTH} 字符"
            )

        # 先检查 SQL 注入（在转义之前）
        if cls._contains_sql_injection(content):
            logger.warning("检测到潜在 SQL 注入尝试")
            raise ValueError("需求内容包含不安全的内容")

        # 检查危险模式（XSS等）
        if cls._contains_dangerous_patterns(content):
            logger.warning("检测到潜在危险内容")
            raise ValueError("需求内容包含不安全的内容")

        # 清洗 HTML/XSS 标签（转义特殊字符）
        content = html.escape(content, quote=True)

        return content

    @classmethod
    def validate_description(cls, description: str | None) -> str | None:
        """
        验证描述

        Args:
            description: 描述

        Returns:
            清理后的描述

        Raises:
            ValueError: 验证失败
        """
        if description is None:
            return None

        if not isinstance(description, str):
            raise ValueError("描述必须是字符串")

        description = description.strip()

        if len(description) == 0:
            return None

        if len(description) > cls.MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"描述长度不能超过 {cls.MAX_DESCRIPTION_LENGTH} 字符")

        return description

    @classmethod
    def validate_test_cases(
        cls, test_cases: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        验证测试用例

        Args:
            test_cases: 测试用例列表

        Returns:
            验证后的测试用例列表

        Raises:
            ValueError: 验证失败
        """
        if not isinstance(test_cases, list):
            raise ValueError("测试用例必须是数组")

        validated_cases = []

        for i, test_case in enumerate(test_cases):
            if not isinstance(test_case, dict):
                raise ValueError(f"测试用例 {i} 必须是字典")

            validated_case = {}

            # 验证名称
            name = test_case.get("name", "")
            if not isinstance(name, str):
                raise ValueError(f"测试用例 {i} 的 name 必须是字符串")

            name = name.strip()
            if len(name) == 0:
                raise ValueError(f"测试用例 {i} 的 name 不能为空")

            if len(name) > cls.MAX_TEST_CASE_NAME_LENGTH:
                raise ValueError(
                    f"测试用例 {i} 的 name 长度不能超过 {cls.MAX_TEST_CASE_NAME_LENGTH} 字符"
                )

            validated_case["name"] = name

            # 复制其他字段
            for key, value in test_case.items():
                if key != "name":
                    validated_case[key] = value

            validated_cases.append(validated_case)

        return validated_cases

    @classmethod
    def validate_uuid(cls, uuid_str: str, field_name: str = "ID") -> str:
        """
        验证 UUID 格式

        Args:
            uuid_str: UUID 字符串
            field_name: 字段名称（用于错误消息）

        Returns:
            验证后的 UUID

        Raises:
            ValueError: 验证失败
        """
        if not uuid_str or not isinstance(uuid_str, str):
            raise ValueError(f"{field_name} 不能为空")

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )

        if not uuid_pattern.match(uuid_str):
            raise ValueError(f"{field_name} 格式不正确，必须是有效的 UUID")

        return uuid_str

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """
        清理 HTML 内容（转义特殊字符）

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        # 转义 HTML 特殊字符
        html_escape_map = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
        }

        result = text
        for char, escaped in html_escape_map.items():
            result = result.replace(char, escaped)

        return result

    @classmethod
    def _contains_dangerous_patterns(cls, text: str) -> bool:
        """
        检查文本是否包含危险模式

        Args:
            text: 待检查的文本

        Returns:
            是否包含危险模式
        """
        text_lower = text.lower()

        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    @classmethod
    def _contains_sql_injection(cls, text: str) -> bool:
        """
        检查文本是否包含 SQL 注入模式

        Args:
            text: 待检查的文本

        Returns:
            是否包含 SQL 注入模式
        """
        text_upper = text.upper()

        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True

        return False

    @classmethod
    def validate_dependency_mapping(
        cls, mapping: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """
        验证依赖映射

        Args:
            mapping: 依赖映射字典

        Returns:
            验证后的依赖映射

        Raises:
            ValueError: 验证失败
        """
        if not isinstance(mapping, dict):
            raise ValueError("依赖映射必须是字典")

        validated_mapping = {}

        for req_id, deps in mapping.items():
            # 验证需求 ID
            validated_req_id = cls.validate_uuid(req_id, "需求 ID")

            # 验证依赖列表
            if not isinstance(deps, list):
                raise ValueError(f"需求 {req_id} 的依赖必须是数组")

            validated_deps = []
            for dep_id in deps:
                validated_dep_id = cls.validate_uuid(dep_id, "依赖 ID")
                validated_deps.append(validated_dep_id)

            validated_mapping[validated_req_id] = validated_deps

        return validated_mapping


class SecurityChecker:
    """
    安全检查器

    用于执行各种安全检查
    """

    @staticmethod
    def check_for_malicious_input(input_data: Any) -> bool:
        """
        检查输入是否包含恶意内容

        Args:
            input_data: 输入数据

        Returns:
            是否安全
        """
        if isinstance(input_data, str):
            return not InputValidator._contains_dangerous_patterns(
                input_data
            ) and not InputValidator._contains_sql_injection(input_data)

        elif isinstance(input_data, dict):
            for value in input_data.values():
                if isinstance(
                    value, str
                ) and not SecurityChecker.check_for_malicious_input(value):
                    return False

        elif isinstance(input_data, list):
            for item in input_data:
                if not SecurityChecker.check_for_malicious_input(item):
                    return False

        return True

    @staticmethod
    def check_depth_limit(depth: int, max_depth: int = 10) -> None:
        """
        检查深度限制

        Args:
            depth: 当前深度
            max_depth: 最大深度

        Raises:
            ValueError: 超过深度限制
        """
        if depth > max_depth:
            raise ValueError(f"深度 ({depth}) 超过最大限制 ({max_depth})")

    @staticmethod
    def check_node_count(count: int, max_count: int = 10000) -> None:
        """
        检查节点数量限制

        Args:
            count: 节点数量
            max_count: 最大节点数

        Raises:
            ValueError: 超过节点数量限制
        """
        if count > max_count:
            raise ValueError(f"节点数量 ({count}) 超过最大限制 ({max_count})")
