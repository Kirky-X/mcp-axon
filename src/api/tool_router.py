# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""工具路由 - 基于注册表的工具分发器"""

import re
from typing import Any, Callable, Dict

from src.constants import APIVersion, Messages


# Helper functions for lock-related handlers
def _lock_result(success: bool, ok_msg: str, fail_msg: str) -> Dict[str, Any]:
    return {"success": success, "message": ok_msg if success else fail_msg}


def _bool_result(value: bool, true_msg: str, false_msg: str) -> Dict[str, Any]:
    return {"locked": value, "message": true_msg if value else false_msg}


def _info_result(info: Any, locked_msg: str, unlocked_msg: str) -> Dict[str, Any]:
    return {
        "lock_info": info,
        "message": locked_msg if info else unlocked_msg,
    }


class ToolRouter:
    """基于注册表的工具分发器

    替代原有的 if-elif 链式工具路由，使用字典注册表模式。
    每个工具注册一个处理函数，调用时根据名称查找并执行。
    """

    def __init__(self, sdk_getter: Callable):
        """
        初始化工具路由

        Args:
            sdk_getter: 获取 SDK 实例的函数
        """
        self._sdk = sdk_getter
        self._handlers: Dict[str, Callable] = {}
        self._uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        self._register_handlers()

    def _register_handlers(self) -> None:
        """注册所有工具处理函数"""
        sdk = self._sdk

        self._handlers = {
            "manage_project": lambda args: sdk().manage_project(
                project_id=args.get("project_id"),
                name=args.get("name", ""),
                description=args.get("description", ""),
            ),
            "get_project": lambda args: sdk().get_project(
                project_id=args["project_id"]
            ),
            "list_requirements": lambda args: sdk().list_requirements(
                project_id=args["project_id"],
                status=args.get("status"),
                is_leaf=args.get("is_leaf"),
                parent_id=args.get("parent_id"),
            ),
            "manage_requirement": lambda args: sdk().manage_requirement(
                requirement_id=args.get("requirement_id"),
                project_id=args.get("project_id"),
                content=args.get("content", ""),
                parent_id=args.get("parent_id"),
                order_in_parent=args.get("order_in_parent", 0),
                status=args.get("status"),
            ),
            "delete_requirement": lambda args: sdk().delete_requirement(
                requirement_id=args["requirement_id"]
            ),
            "add_validation": lambda args: sdk().add_validation(
                requirement_id=args["requirement_id"],
                test_cases=args.get("test_cases", []),
                acceptance_criteria=args.get("acceptance_criteria", ""),
            ),
            "transfer_dependencies": lambda args: sdk().transfer_dependencies(
                parent_id=args["parent_id"],
                dependency_mapping=args["dependency_mapping"],
            ),
            "add_dependency": lambda args: sdk().add_dependency(
                requirement_id=args["requirement_id"],
                dependency_id=args["dependency_id"],
            ),
            "resolve_parallel_order": lambda args: sdk().resolve_parallel_order(
                project_id=args["project_id"],
                parallel_nodes=args["parallel_nodes"],
                sorted_order=args["sorted_order"],
            ),
            "get_next_requirement": lambda args: sdk().get_next_requirement(
                project_id=args["project_id"],
                session_id=args.get("_session_id", ""),
            ),
            "mark_requirement_completed": lambda args: sdk().mark_requirement_completed(
                project_id=args["project_id"],
                requirement_id=args["requirement_id"],
            ),
            "get_project_state": lambda args: sdk().get_project_state(
                project_id=args["project_id"]
            ),
            "trigger_chaining": lambda args: sdk().trigger_chaining(
                project_id=args["project_id"],
                session_id=args.get("_session_id", ""),
            ),
            "create_snapshot": lambda args: {
                "snapshot_id": sdk().create_snapshot(
                    project_id=args["project_id"],
                    session_id=args.get("_session_id", ""),
                ),
                "message": Messages.SNAPSHOT_CREATED,
            },
            "restore_snapshot": lambda args: sdk().restore_snapshot(
                snapshot_id=args["snapshot_id"],
                session_id=args.get("_session_id", ""),
            ),
            "list_snapshots": lambda args: {
                "snapshots": sdk().list_snapshots(
                    project_id=args["project_id"], limit=args.get("limit", 10)
                )
            },
            "acquire_lock": lambda args: _lock_result(
                sdk().acquire_lock(
                    project_id=args["project_id"], session_id=args["session_id"]
                ),
                Messages.LOCK_ACQUIRED,
                Messages.LOCK_IN_USE,
            ),
            "release_lock": lambda args: _lock_result(
                sdk().release_lock(
                    project_id=args["project_id"], session_id=args["session_id"]
                ),
                Messages.LOCK_RELEASED,
                Messages.LOCK_NOT_OWNER,
            ),
            "is_locked": lambda args: _bool_result(
                sdk().is_locked(project_id=args["project_id"]),
                Messages.PROJECT_LOCKED,
                Messages.PROJECT_NOT_LOCKED,
            ),
            "get_lock_info": lambda args: _info_result(
                sdk().get_lock_info(project_id=args["project_id"]),
                Messages.PROJECT_LOCKED,
                Messages.PROJECT_NOT_LOCKED,
            ),
            "mark_as_leaf": lambda args: sdk().mark_as_leaf(
                requirement_id=args["requirement_id"]
            ),
            "get_api_version": lambda args: {
                "current_version": APIVersion.CURRENT_VERSION,
                "supported_versions": APIVersion.SUPPORTED_VERSIONS,
                "min_supported_version": APIVersion.MIN_SUPPORTED_VERSION,
                "version_history": APIVersion.VERSION_HISTORY,
            },
        }

    def route(self, name: str, arguments: dict) -> dict:
        """
        路由到对应的工具处理函数

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果

        Raises:
            ValueError: 工具未注册
        """
        if name not in self._handlers:
            raise ValueError(f"未知工具: {name}")

        return self._handlers[name](arguments)

    def validate_input(self, name: str, arguments: dict) -> None:
        """
        验证工具输入参数

        Args:
            name: 工具名称
            arguments: 工具参数

        Raises:
            ValueError: 参数验证失败
        """
        if not isinstance(arguments, dict):
            raise ValueError("参数必须是字典格式")

        # 项目 ID 验证
        project_id_tools = {
            "manage_project",
            "get_project",
            "manage_requirement",
            "get_project_state",
            "trigger_chaining",
            "create_snapshot",
            "list_snapshots",
            "acquire_lock",
            "release_lock",
            "is_locked",
            "get_lock_info",
            "resolve_parallel_order",
            "get_next_requirement",
            "mark_requirement_completed",
        }
        if name in project_id_tools:
            project_id = arguments.get("project_id")
            if name == "manage_project":
                # manage_project 创建时不需要 project_id
                if project_id and not isinstance(project_id, str):
                    raise ValueError("project_id 参数必须是字符串")
                if project_id and not self._uuid_pattern.match(project_id):
                    raise ValueError("project_id 格式不正确")
            else:
                if not project_id or not isinstance(project_id, str):
                    raise ValueError("project_id 参数是必填的字符串")
                if not self._uuid_pattern.match(project_id):
                    raise ValueError("project_id 格式不正确，必须是有效的 UUID")

        # 需求 ID 验证
        requirement_id_tools = {
            "manage_requirement",
            "delete_requirement",
            "add_validation",
            "add_dependency",
            "mark_as_leaf",
        }
        if name in requirement_id_tools:
            requirement_id = arguments.get("requirement_id")
            if name == "manage_requirement":
                # manage_requirement 创建时不需要 requirement_id
                if requirement_id and not isinstance(requirement_id, str):
                    raise ValueError("requirement_id 参数必须是字符串")
                if requirement_id and not self._uuid_pattern.match(requirement_id):
                    raise ValueError("requirement_id 格式不正确")
            else:
                if not requirement_id or not isinstance(requirement_id, str):
                    raise ValueError("requirement_id 参数是必填的字符串")
                if not self._uuid_pattern.match(requirement_id):
                    raise ValueError("requirement_id 格式不正确，必须是有效的 UUID")

        # transfer_dependencies 使用 parent_id
        if name == "transfer_dependencies":
            parent_id = arguments.get("parent_id")
            if not parent_id or not isinstance(parent_id, str):
                raise ValueError("parent_id 参数是必填的字符串")
            if not self._uuid_pattern.match(parent_id):
                raise ValueError("parent_id 格式不正确，必须是有效的 UUID")
            dependency_mapping = arguments.get("dependency_mapping")
            if not isinstance(dependency_mapping, dict):
                raise ValueError("dependency_mapping 必须是字典格式")

        # 字符串内容验证
        if name == "manage_project":
            name_val = arguments.get("name", "")
            project_id = arguments.get("project_id")
            # 创建时 name 必填
            if not project_id and (not name_val or not name_val.strip()):
                raise ValueError("创建项目时 name 不能为空")
            if len(name_val) > 5000:
                raise ValueError("name 长度不能超过 5000 字符")
        elif name == "manage_requirement":
            content = arguments.get("content", "")
            requirement_id = arguments.get("requirement_id")
            # 创建时 content 必填
            if not requirement_id and (not content or not content.strip()):
                raise ValueError("创建需求时 content 不能为空")
            if len(content) > 5000:
                raise ValueError("content 长度不能超过 5000 字符")
            # status 验证
            status = arguments.get("status")
            if status is not None:
                from src.db.graph_models import RequirementStatus

                valid_statuses = {s.value for s in RequirementStatus}
                if status not in valid_statuses:
                    raise ValueError(
                        f"status 必须是以下值之一: {', '.join(sorted(valid_statuses))}"
                    )
            # parent_id 验证
            parent_id = arguments.get("parent_id")
            if parent_id is not None:
                if not isinstance(parent_id, str) or not self._uuid_pattern.match(
                    parent_id
                ):
                    raise ValueError("parent_id 格式不正确，必须是有效的 UUID")

        # 数组参数验证
        if name == "add_validation":
            test_cases = arguments.get("test_cases", [])
            if not isinstance(test_cases, list):
                raise ValueError("test_cases 必须是数组格式")
            for i, test_case in enumerate(test_cases):
                if not isinstance(test_case, dict):
                    raise ValueError(f"test_cases[{i}] 必须是字典格式")

        # 并行节点排序验证
        if name == "resolve_parallel_order":
            parallel_nodes = arguments.get("parallel_nodes", [])
            sorted_order = arguments.get("sorted_order", [])
            if not isinstance(parallel_nodes, list) or not isinstance(
                sorted_order, list
            ):
                raise ValueError("parallel_nodes 和 sorted_order 必须是数组格式")
            if len(parallel_nodes) != len(sorted_order):
                raise ValueError("parallel_nodes 和 sorted_order 长度必须相同")
            if set(parallel_nodes) != set(sorted_order):
                raise ValueError("sorted_order 必须包含所有 parallel_nodes 中的节点")
            all_nodes = parallel_nodes + sorted_order
            for node in all_nodes:
                if not isinstance(node, str) or not self._uuid_pattern.match(node):
                    raise ValueError(f"节点ID格式不正确: {node}")
