# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 工具定义测试 - 埋缩版（8个接口）"""

from src.api.tools import TOOL_DEFINITIONS


def test_tool_definitions_count():
    """测试工具定义数量为8个"""
    assert len(TOOL_DEFINITIONS) == 8


def test_tool_definitions_structure():
    """测试所有工具定义都有正确的结构"""
    required_attributes = ["name", "description", "inputSchema"]

    for tool in TOOL_DEFINITIONS:
        for attr in required_attributes:
            assert hasattr(tool, attr), (
                f"工具 {getattr(tool, 'name', '未知')} 缺少属性 {attr}"
            )


def test_tool_names_are_unique():
    """测试工具名称是唯一的"""
    tool_names = [tool.name for tool in TOOL_DEFINITIONS]
    assert len(tool_names) == len(set(tool_names)), "工具名称必须唯一"


def test_tool_descriptions_not_empty():
    """测试所有工具都有描述"""
    for tool in TOOL_DEFINITIONS:
        assert tool.description, f"工具 {tool.name} 缺少描述"
        assert len(tool.description) > 0, f"工具 {tool.name} 的描述不能为空"


def test_tool_input_schema_type():
    """测试所有工具的 inputSchema 都是对象类型"""
    for tool in TOOL_DEFINITIONS:
        assert tool.inputSchema["type"] == "object", (
            f"工具 {tool.name} 的 inputSchema 必须是对象类型"
        )


def test_tool_input_schema_has_properties():
    """测试所有工具的 inputSchema 都有 properties 字段"""
    for tool in TOOL_DEFINITIONS:
        assert "properties" in tool.inputSchema, (
            f"工具 {tool.name} 的 inputSchema 缺少 properties 字段"
        )


def test_tool_required_fields_are_valid():
    """测试所有工具的 required 字段都是有效的"""
    for tool in TOOL_DEFINITIONS:
        required = tool.inputSchema.get("required", [])
        properties = tool.inputSchema.get("properties", {})

        for field in required:
            assert field in properties, (
                f"工具 {tool.name} 的 required 字段 {field} 不在 properties 中"
            )


def test_all_consolidated_tools_exist():
    """测试所有合并后的接口都已定义"""
    expected_tools = [
        "manage_project",
        "manage_requirement",
        "manage_dependency",
        "manage_validation",
        "manage_execution",
        "manage_snapshot",
        "manage_lock",
    ]

    tool_names = [tool.name for tool in TOOL_DEFINITIONS]

    for expected in expected_tools:
        assert expected in tool_names, f"合并接口 {expected} 未定义"


def test_manage_project_has_action():
    """测试 manage_project 有 action 参数"""
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "manage_project")
    assert "action" in tool.inputSchema["properties"]
    assert "action" in tool.inputSchema.get("required", [])
    action_schema = tool.inputSchema["properties"]["action"]
    assert action_schema["type"] == "string"
    assert "enum" in action_schema
    assert set(action_schema["enum"]) == {"get", "create", "update"}


def test_manage_requirement_has_action():
    """测试 manage_requirement 有 action 参数"""
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "manage_requirement")
    assert "action" in tool.inputSchema["properties"]
    assert "action" in tool.inputSchema.get("required", [])
    action_schema = tool.inputSchema["properties"]["action"]
    assert action_schema["type"] == "string"
    assert "enum" in action_schema
    expected_actions = {"get", "create", "update", "delete", "mark_leaf", "list"}
    assert set(action_schema["enum"]) == expected_actions


def test_manage_validation_has_execution_result():
    """测试 manage_validation 有 execution_result 参数（用于区分执行/添加）"""
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "manage_validation")
    assert "execution_result" in tool.inputSchema["properties"]
    assert tool.inputSchema["properties"]["execution_result"]["type"] == "string"


def test_manage_execution_has_action():
    """测试 manage_execution 有 action 参数"""
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "manage_execution")
    assert "action" in tool.inputSchema["properties"]
    assert "action" in tool.inputSchema.get("required", [])
    action_schema = tool.inputSchema["properties"]["action"]
    assert action_schema["type"] == "string"
    assert "enum" in action_schema
    assert set(action_schema["enum"]) == {"next", "complete", "state", "trigger"}


def test_manage_snapshot_has_action():
    """测试 manage_snapshot 有 action 参数"""
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "manage_snapshot")
    assert "action" in tool.inputSchema["properties"]
    assert "action" in tool.inputSchema.get("required", [])
    action_schema = tool.inputSchema["properties"]["action"]
    assert action_schema["type"] == "string"
    assert "enum" in action_schema
    assert set(action_schema["enum"]) == {"create", "restore", "list"}


def test_manage_lock_has_action():
    """测试 manage_lock 有 action 参数"""
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "manage_lock")
    assert "action" in tool.inputSchema["properties"]
    assert "action" in tool.inputSchema.get("required", [])
    action_schema = tool.inputSchema["properties"]["action"]
    assert action_schema["type"] == "string"
    assert "enum" in action_schema
    assert set(action_schema["enum"]) == {"acquire", "release", "check", "info"}


def test_tool_input_schema_properties_have_types():
    """测试所有工具的 properties 都有类型定义"""
    for tool in TOOL_DEFINITIONS:
        properties = tool.inputSchema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            assert "type" in prop_schema, (
                f"工具 {tool.name} 的属性 {prop_name} 缺少类型定义"
            )


def test_tool_names_are_snake_case():
    """测试工具名称使用 snake_case 格式"""
    for tool in TOOL_DEFINITIONS:
        tool_name = tool.name
        # 验证名称只包含小写字母、数字和下划线
        assert tool_name.islower() or tool_name.replace("_", "").isalnum(), (
            f"工具名称应该使用 snake_case 格式: {tool_name}"
        )


def test_tool_descriptions_are_meaningful():
    """测试工具描述都是有意义的"""
    for tool in TOOL_DEFINITIONS:
        description = tool.description
        assert len(description) >= 5, f"工具 {tool.name} 的描述太短: {description}"


def test_manage_dependency_has_both_modes():
    """测试 manage_dependency 支持单个添加和批量传递两种模式"""
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "manage_dependency")

    # 单个添加参数
    assert "requirement_id" in tool.inputSchema["properties"]
    assert "dependency_id" in tool.inputSchema["properties"]

    # 批量传递参数
    assert "parent_id" in tool.inputSchema["properties"]
    assert "dependency_mapping" in tool.inputSchema["properties"]

    # dependency_mapping 应该是对象类型
    dep_mapping = tool.inputSchema["properties"]["dependency_mapping"]
    assert dep_mapping["type"] == "object"


def test_get_api_version_tool_exists():
    """测试 get_api_version 工具存在"""
    tool_names = [tool.name for tool in TOOL_DEFINITIONS]
    assert "get_api_version" in tool_names, "get_api_version 工具未定义"
