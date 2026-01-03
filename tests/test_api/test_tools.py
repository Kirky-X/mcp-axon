# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 工具定义测试"""

from src.api.tools import TOOL_DEFINITIONS


def test_tool_definitions_not_empty():
    """测试工具定义列表不为空"""
    # Arrange & Act & Assert
    assert len(TOOL_DEFINITIONS) > 0
    assert len(TOOL_DEFINITIONS) == 22


def test_tool_definitions_structure():
    """测试所有工具定义都有正确的结构"""
    # Arrange
    required_attributes = ["name", "description", "inputSchema"]

    # Act & Assert
    for tool in TOOL_DEFINITIONS:
        for attr in required_attributes:
            assert hasattr(tool, attr), (
                f"工具 {getattr(tool, 'name', '未知')} 缺少属性 {attr}"
            )


def test_tool_names_are_unique():
    """测试工具名称是唯一的"""
    # Arrange
    tool_names = [tool.name for tool in TOOL_DEFINITIONS]

    # Act & Assert
    assert len(tool_names) == len(set(tool_names)), "工具名称必须唯一"


def test_tool_descriptions_not_empty():
    """测试所有工具都有描述"""
    # Act & Assert
    for tool in TOOL_DEFINITIONS:
        assert tool.description, f"工具 {tool.name} 缺少描述"
        assert len(tool.description) > 0, f"工具 {tool.name} 的描述不能为空"


def test_tool_input_schema_type():
    """测试所有工具的 inputSchema 都是对象类型"""
    # Act & Assert
    for tool in TOOL_DEFINITIONS:
        assert tool.inputSchema["type"] == "object", (
            f"工具 {tool.name} 的 inputSchema 必须是对象类型"
        )


def test_tool_input_schema_has_properties():
    """测试所有工具的 inputSchema 都有 properties 字段"""
    # Act & Assert
    for tool in TOOL_DEFINITIONS:
        assert "properties" in tool.inputSchema, (
            f"工具 {tool.name} 的 inputSchema 缺少 properties 字段"
        )


def test_tool_required_fields_are_valid():
    """测试所有工具的 required 字段都是有效的"""
    # Act & Assert
    for tool in TOOL_DEFINITIONS:
        required = tool.inputSchema.get("required", [])
        properties = tool.inputSchema.get("properties", {})

        # 验证所有 required 字段都在 properties 中
        for field in required:
            assert field in properties, (
                f"工具 {tool.name} 的 required 字段 {field} 不在 properties 中"
            )


def test_create_project_tool_schema():
    """测试 create_project 工具的 schema"""
    # Arrange
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "create_project")

    # Assert
    assert tool.name == "create_project"
    assert "name" in tool.inputSchema["required"]
    assert "description" not in tool.inputSchema["required"]
    assert "name" in tool.inputSchema["properties"]
    assert "description" in tool.inputSchema["properties"]
    assert tool.inputSchema["properties"]["name"]["type"] == "string"
    assert tool.inputSchema["properties"]["description"]["type"] == "string"


def test_add_requirement_tool_schema():
    """测试 add_requirement 工具的 schema"""
    # Arrange
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "add_requirement")

    # Assert
    assert tool.name == "add_requirement"
    assert "project_id" in tool.inputSchema["required"]
    assert "content" in tool.inputSchema["required"]
    assert "parent_id" not in tool.inputSchema["required"]
    assert "order_in_parent" not in tool.inputSchema["required"]


def test_add_validation_tool_schema():
    """测试 add_validation 工具的 schema"""
    # Arrange
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "add_validation")

    # Assert
    assert tool.name == "add_validation"
    assert "requirement_id" in tool.inputSchema["required"]
    assert "test_cases" not in tool.inputSchema["required"]
    assert "acceptance_criteria" not in tool.inputSchema["required"]

    # 验证 test_cases 是数组类型
    if "test_cases" in tool.inputSchema["properties"]:
        test_cases_schema = tool.inputSchema["properties"]["test_cases"]
        assert test_cases_schema["type"] == "array"


def test_transfer_dependencies_tool_schema():
    """测试 transfer_dependencies 工具的 schema"""
    # Arrange
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "transfer_dependencies")

    # Assert
    assert tool.name == "transfer_dependencies"
    assert "parent_id" in tool.inputSchema["required"]
    assert "dependency_mapping" in tool.inputSchema["required"]

    # 验证 dependency_mapping 是对象类型
    dependency_mapping_schema = tool.inputSchema["properties"]["dependency_mapping"]
    assert dependency_mapping_schema["type"] == "object"


def test_resolve_parallel_order_tool_schema():
    """测试 resolve_parallel_order 工具的 schema"""
    # Arrange
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "resolve_parallel_order")

    # Assert
    assert tool.name == "resolve_parallel_order"
    assert "project_id" in tool.inputSchema["required"]
    assert "parallel_nodes" in tool.inputSchema["required"]
    assert "sorted_order" in tool.inputSchema["required"]

    # 验证 parallel_nodes 和 sorted_order 都是数组类型
    parallel_nodes_schema = tool.inputSchema["properties"]["parallel_nodes"]
    sorted_order_schema = tool.inputSchema["properties"]["sorted_order"]
    assert parallel_nodes_schema["type"] == "array"
    assert sorted_order_schema["type"] == "array"


def test_lock_related_tools_schema():
    """测试锁相关工具的 schema"""
    # Arrange
    lock_tools = ["acquire_lock", "release_lock"]

    # Act & Assert
    for tool_name in lock_tools:
        tool = next(t for t in TOOL_DEFINITIONS if t.name == tool_name)
        assert tool.name == tool_name
        assert "project_id" in tool.inputSchema["required"]
        assert "session_id" in tool.inputSchema["required"]


def test_get_lock_info_tool_schema():
    """测试 get_lock_info 工具的 schema"""
    # Arrange
    tool = next(t for t in TOOL_DEFINITIONS if t.name == "get_lock_info")

    # Assert
    assert tool.name == "get_lock_info"
    assert "project_id" in tool.inputSchema["required"]
    assert len(tool.inputSchema["required"]) == 1


def test_snapshot_related_tools_schema():
    """测试快照相关工具的 schema"""
    # Arrange
    snapshot_tools = ["create_snapshot", "restore_snapshot", "list_snapshots"]

    # Act & Assert
    for tool_name in snapshot_tools:
        tool = next(t for t in TOOL_DEFINITIONS if t.name == tool_name)
        assert tool.name == tool_name

        if tool_name == "restore_snapshot":
            assert "snapshot_id" in tool.inputSchema["required"]
        else:
            assert "project_id" in tool.inputSchema["required"]


def test_tool_descriptions_are_meaningful():
    """测试工具描述都是有意义的"""
    # Act & Assert
    for tool in TOOL_DEFINITIONS:
        description = tool.description
        assert len(description) >= 5, f"工具 {tool.name} 的描述太短: {description}"


def test_tool_names_are_snake_case():
    """测试工具名称使用 snake_case 格式"""
    # Act & Assert
    for tool in TOOL_DEFINITIONS:
        tool_name = tool.name
        # 验证名称只包含小写字母、数字和下划线
        assert tool_name.islower() or tool_name.replace("_", "").isalnum(), (
            f"工具名称应该使用 snake_case 格式: {tool_name}"
        )


def test_all_core_tools_exist():
    """测试所有核心工具都已定义"""
    # Arrange
    core_tools = [
        "create_project",
        "add_requirement",
        "mark_as_leaf",
        "add_validation",
        "get_next_requirement",
        "mark_requirement_completed",
        "get_project_state",
    ]

    # Act
    tool_names = [tool.name for tool in TOOL_DEFINITIONS]

    # Assert
    for core_tool in core_tools:
        assert core_tool in tool_names, f"核心工具 {core_tool} 未定义"


def test_all_lock_tools_exist():
    """测试所有锁相关工具都已定义"""
    # Arrange
    lock_tools = ["acquire_lock", "release_lock", "is_locked", "get_lock_info"]

    # Act
    tool_names = [tool.name for tool in TOOL_DEFINITIONS]

    # Assert
    for lock_tool in lock_tools:
        assert lock_tool in tool_names, f"锁工具 {lock_tool} 未定义"


def test_all_snapshot_tools_exist():
    """测试所有快照相关工具都已定义"""
    # Arrange
    snapshot_tools = ["create_snapshot", "restore_snapshot", "list_snapshots"]

    # Act
    tool_names = [tool.name for tool in TOOL_DEFINITIONS]

    # Assert
    for snapshot_tool in snapshot_tools:
        assert snapshot_tool in tool_names, f"快照工具 {snapshot_tool} 未定义"


def test_tool_input_schema_properties_have_types():
    """测试所有工具的 properties 都有类型定义"""
    # Act & Assert
    for tool in TOOL_DEFINITIONS:
        properties = tool.inputSchema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            assert "type" in prop_schema, (
                f"工具 {tool.name} 的属性 {prop_name} 缺少类型定义"
            )
