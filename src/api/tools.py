# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 工具定义"""

from mcp.types import Tool

from src.constants import APIVersion

# API 版本信息
API_VERSION = APIVersion.CURRENT_VERSION

# 工具定义列表
TOOL_DEFINITIONS = [
    Tool(
        name="create_project",
        description="创建新的需求链项目。创建后可以开始添加需求节点。",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "项目名称（必填）"},
                "description": {"type": "string", "description": "项目描述（可选）"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="update_project",
        description="更新项目信息（名称或描述）。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"},
                "name": {"type": "string", "description": "新项目名称（可选）"},
                "description": {"type": "string", "description": "新项目描述（可选）"},
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="get_project",
        description="获取项目详细信息。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"}
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="list_requirements",
        description="获取项目的所有需求节点 ID 列表。可选过滤条件：status（状态）、is_leaf（是否叶子节点）、parent_id（父需求 ID）。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"},
                "status": {
                    "type": "string",
                    "description": "按状态过滤（可选）：DRAFT, DECOMPOSING, LEAF, VALIDATED, CHAINED, COMPLETED",
                },
                "is_leaf": {
                    "type": "boolean",
                    "description": "是否只返回叶子节点（可选）",
                },
                "parent_id": {
                    "type": "string",
                    "description": "父需求 ID（可选，只返回该需求的直接子需求）",
                },
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="add_requirement",
        description="添加需求节点。系统会自动评估需求复杂度，如果复杂度较高会建议分解。返回结果包含是否需要分解的提示。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"},
                "content": {"type": "string", "description": "需求内容（必填）"},
                "parent_id": {
                    "type": "string",
                    "description": "父需求 ID（可选，用于创建子需求）",
                },
                "order_in_parent": {
                    "type": "integer",
                    "description": "在父需求中的顺序（默认为 0）",
                },
            },
            "required": ["project_id", "content"],
        },
    ),
    Tool(
        name="update_requirement",
        description="更新需求内容或状态。",
        inputSchema={
            "type": "object",
            "properties": {
                "requirement_id": {"type": "string", "description": "需求 ID（必填）"},
                "content": {"type": "string", "description": "新需求内容（可选）"},
                "status": {"type": "string", "description": "新状态（可选）"},
            },
            "required": ["requirement_id"],
        },
    ),
    Tool(
        name="delete_requirement",
        description="删除需求节点（会级联删除所有子需求和验证节点）。",
        inputSchema={
            "type": "object",
            "properties": {
                "requirement_id": {"type": "string", "description": "需求 ID（必填）"}
            },
            "required": ["requirement_id"],
        },
    ),
    Tool(
        name="add_validation",
        description="为叶子节点添加验证。验证包含测试用例和验收标准。添加验证后，系统会检查是否可以触发链化。",
        inputSchema={
            "type": "object",
            "properties": {
                "requirement_id": {
                    "type": "string",
                    "description": "需求 ID（必填，必须是叶子节点）",
                },
                "test_cases": {
                    "type": "array",
                    "description": "测试用例列表（可选）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "测试用例名称"},
                            "steps": {
                                "type": "array",
                                "description": "测试步骤",
                                "items": {"type": "string"},
                            },
                            "expected_result": {
                                "type": "string",
                                "description": "预期结果",
                            },
                        },
                    },
                },
                "acceptance_criteria": {
                    "type": "string",
                    "description": "验收标准（可选）",
                },
            },
            "required": ["requirement_id"],
        },
    ),
    Tool(
        name="transfer_dependencies",
        description="应用依赖传递映射。当父需求分解为多个子需求时，使用此工具指定每个子需求的依赖关系。",
        inputSchema={
            "type": "object",
            "properties": {
                "parent_id": {"type": "string", "description": "父需求 ID（必填）"},
                "dependency_mapping": {
                    "type": "object",
                    "description": "依赖映射（必填），格式：{子需求ID: [依赖ID列表]}",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "required": ["parent_id", "dependency_mapping"],
        },
    ),
    Tool(
        name="add_dependency",
        description="为需求添加依赖关系。系统会自动检测循环依赖。",
        inputSchema={
            "type": "object",
            "properties": {
                "requirement_id": {"type": "string", "description": "需求 ID（必填）"},
                "dependency_id": {
                    "type": "string",
                    "description": "依赖的需求 ID（必填）",
                },
            },
            "required": ["requirement_id", "dependency_id"],
        },
    ),
    Tool(
        name="resolve_parallel_order",
        description="指定并行节点的执行顺序。当链化检测到并行节点时，使用此工具指定它们的执行顺序。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"},
                "parallel_nodes": {
                    "type": "array",
                    "description": "并行节点 ID 列表（必填）",
                    "items": {"type": "string"},
                },
                "sorted_order": {
                    "type": "array",
                    "description": "排序后的节点 ID 列表（必填，必须包含所有并行节点）",
                    "items": {"type": "string"},
                },
            },
            "required": ["project_id", "parallel_nodes", "sorted_order"],
        },
    ),
    Tool(
        name="get_next_requirement",
        description="获取下一个需要执行的需求。这是核心接口，用于按顺序获取链化后的需求。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"}
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="mark_requirement_completed",
        description="标记需求为已完成。完成后会自动移动到下一个需求。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"},
                "requirement_id": {"type": "string", "description": "需求 ID（必填）"},
            },
            "required": ["project_id", "requirement_id"],
        },
    ),
    Tool(
        name="get_project_state",
        description="查询项目当前状态，包括需求数量、链化进度等。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"}
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="trigger_chaining",
        description="手动触发链化。通常在所有叶子节点都添加验证后自动触发，但也可以手动触发。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"}
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="create_snapshot",
        description="创建项目状态快照。快照可用于后续回滚。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"}
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="restore_snapshot",
        description="从快照恢复项目状态。用于链化失败时回滚。",
        inputSchema={
            "type": "object",
            "properties": {
                "snapshot_id": {"type": "string", "description": "快照 ID（必填）"}
            },
            "required": ["snapshot_id"],
        },
    ),
    Tool(
        name="list_snapshots",
        description="列出项目的所有快照。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"},
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制（默认为 10）",
                },
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="acquire_lock",
        description="获取项目锁。用于防止并发修改冲突。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"},
                "session_id": {"type": "string", "description": "会话 ID（必填）"},
            },
            "required": ["project_id", "session_id"],
        },
    ),
    Tool(
        name="release_lock",
        description="释放项目锁。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"},
                "session_id": {"type": "string", "description": "会话 ID（必填）"},
            },
            "required": ["project_id", "session_id"],
        },
    ),
    Tool(
        name="is_locked",
        description="检查项目是否被锁定。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"}
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="get_lock_info",
        description="获取项目锁的详细信息。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID（必填）"}
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="mark_as_leaf",
        description="将需求标记为叶子节点。新需求默认为叶子节点，此方法用于将已存在的需求标记为叶子。",
        inputSchema={
            "type": "object",
            "properties": {
                "requirement_id": {"type": "string", "description": "需求 ID（必填）"}
            },
            "required": ["requirement_id"],
        },
    ),
]
