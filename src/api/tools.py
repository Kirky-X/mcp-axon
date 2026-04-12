# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""MCP 工具定义 - 压缩版（8个接口）"""

from mcp.types import Tool

from src.constants import APIVersion

# API 版本信息
API_VERSION = APIVersion.CURRENT_VERSION

# 工具定义列表（压缩后8个接口）
TOOL_DEFINITIONS = [
    # 1. 项目管理（合并：manage_project, get_project）
    Tool(
        name="manage_project",
        description="项目管理：创建、更新、查询项目。通过 action 参数区分操作类型。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目 ID（查询/更新时必填，创建时可选）",
                },
                "action": {
                    "type": "string",
                    "enum": ["get", "create", "update"],
                    "description": "操作类型：get=查询, create=创建, update=更新",
                },
                "name": {
                    "type": "string",
                    "description": "项目名称（创建时必填）",
                },
                "description": {
                    "type": "string",
                    "description": "项目描述",
                },
            },
            "required": ["action"],
        },
    ),
    # 2. 需求管理（合并：manage_requirement, delete_requirement, mark_as_leaf, list_requirements）
    Tool(
        name="manage_requirement",
        description="需求管理：创建、更新、删除、标记叶子、查询、列表。通过 action 参数区分操作。",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "create", "update", "delete", "mark_leaf", "list"],
                    "description": "操作类型：get=查询, create=创建, update=更新, delete=删除, mark_leaf=标记叶子, list=列表",
                },
                "project_id": {
                    "type": "string",
                    "description": "项目 ID（create/list 时必填）",
                },
                "requirement_id": {
                    "type": "string",
                    "description": "需求 ID（get/update/delete/mark_leaf 时必填）",
                },
                "content": {
                    "type": "string",
                    "description": "需求内容（create 时必填）",
                },
                "parent_id": {
                    "type": "string",
                    "description": "父需求 ID（create 时可选）",
                },
                "order_in_parent": {
                    "type": "integer",
                    "description": "在父需求中的顺序（create 时）",
                },
                "status": {
                    "type": "string",
                    "description": "状态（update 时可选）",
                },
                "is_leaf": {
                    "type": "boolean",
                    "description": "过滤条件：只返回叶子节点（list 时可选）",
                },
            },
            "required": ["action"],
        },
    ),
    # 3. 依赖管理（合并：add_dependency, transfer_dependencies）
    Tool(
        name="manage_dependency",
        description="依赖管理：添加单个依赖或批量传递依赖。通过参数类型自动区分操作。",
        inputSchema={
            "type": "object",
            "properties": {
                "requirement_id": {
                    "type": "string",
                    "description": "需求 ID（添加单个依赖时必填）",
                },
                "dependency_id": {
                    "type": "string",
                    "description": "依赖的需求 ID（添加单个依赖时必填）",
                },
                "parent_id": {
                    "type": "string",
                    "description": "父需求 ID（批量传递依赖时必填）",
                },
                "dependency_mapping": {
                    "type": "object",
                    "description": "依赖映射（批量传递时使用），格式：{子需求ID: [依赖ID列表]}",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    ),
    # 4. 验证管理（合并：add_validation, run_validation）
    Tool(
        name="manage_validation",
        description="验证管理：添加验证或执行验证。有 execution_result 表示执行验证，否则为添加验证。",
        inputSchema={
            "type": "object",
            "properties": {
                "requirement_id": {
                    "type": "string",
                    "description": "需求 ID（必填）",
                },
                "test_cases": {
                    "type": "array",
                    "description": "测试用例列表（添加验证时可选）",
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
                    "description": "验收标准（添加验证时可选）",
                },
                "execution_result": {
                    "type": "string",
                    "description": "执行结果（执行验证时必填），有此参数表示执行验证",
                },
            },
            "required": ["requirement_id"],
        },
    ),
    # 5. 执行流程管理（合并：get_next_requirement, mark_requirement_completed, get_project_state, trigger_chaining）
    Tool(
        name="manage_execution",
        description="执行流程管理：获取下一个需求、标记完成、查询状态、触发链化。通过 action 参数区分。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目 ID（必填）",
                },
                "action": {
                    "type": "string",
                    "enum": ["next", "complete", "state", "trigger"],
                    "description": "操作类型：next=获取下一个, complete=标记完成, state=查询状态, trigger=触发链化",
                },
                "requirement_id": {
                    "type": "string",
                    "description": "需求 ID（complete 时必填）",
                },
            },
            "required": ["project_id", "action"],
        },
    ),
    # 6. 快照管理（合并：create_snapshot, restore_snapshot, list_snapshots）
    Tool(
        name="manage_snapshot",
        description="快照管理：创建、恢复、列出快照。通过 action 参数区分操作。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目 ID（create/list 时必填）",
                },
                "snapshot_id": {
                    "type": "string",
                    "description": "快照 ID（restore 时必填）",
                },
                "action": {
                    "type": "string",
                    "enum": ["create", "restore", "list"],
                    "description": "操作类型：create=创建, restore=恢复, list=列出",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制（list 时可选，默认10）",
                },
            },
            "required": ["action"],
        },
    ),
    # 7. 锁管理（合并：acquire_lock, release_lock, is_locked, get_lock_info）
    Tool(
        name="manage_lock",
        description="锁管理：获取、释放、检查、查询锁信息。通过 action 参数区分操作。",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目 ID（必填）",
                },
                "action": {
                    "type": "string",
                    "enum": ["acquire", "release", "check", "info"],
                    "description": "操作类型：acquire=获取锁, release=释放锁, check=检查锁定, info=查询信息",
                },
                "session_id": {
                    "type": "string",
                    "description": "会话 ID（acquire/release 时必填）",
                },
            },
            "required": ["project_id", "action"],
        },
    ),
    # 8. API版本查询（保留独立接口）
    Tool(
        name="get_api_version",
        description="获取 API 版本信息。",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]
