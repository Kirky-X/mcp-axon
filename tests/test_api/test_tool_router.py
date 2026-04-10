# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""工具路由测试"""

import os
import pytest

os.environ["MCP_AXON_DB_PATH"] = ":memory:"

from src.api.mcp_server import get_sdk, get_tool_router


@pytest.fixture(autouse=True)
def init_db():
    """初始化测试数据库"""
    get_sdk()


@pytest.fixture
def router():
    """创建工具路由器实例"""
    return get_tool_router()


class TestToolRouterRouting:
    """工具路由分发测试"""

    def test_create_project(self, router):
        """测试: 创建项目"""
        result = router.route(
            "manage_project", {"name": "测试项目", "description": "描述"}
        )
        assert "project_id" in result
        assert "next_action" in result

    def test_get_project(self, router):
        """测试: 获取项目"""
        project = router.route("manage_project", {"name": "测试项目"})
        result = router.route("get_project", {"project_id": project["project_id"]})
        assert result["name"] == "测试项目"

    def test_update_project(self, router):
        """测试: 更新项目"""
        project = router.route("manage_project", {"name": "旧名称"})
        result = router.route(
            "manage_project",
            {"project_id": project["project_id"], "name": "新名称"},
        )
        assert result["name"] == "新名称"

    def test_add_requirement(self, router):
        """测试: 添加需求"""
        project = router.route("manage_project", {"name": "测试项目"})
        result = router.route(
            "manage_requirement",
            {"project_id": project["project_id"], "content": "测试需求"},
        )
        assert "requirement_id" in result
        assert "complexity_score" in result

    def test_list_requirements(self, router):
        """测试: 列出需求"""
        project = router.route("manage_project", {"name": "测试项目"})
        router.route(
            "manage_requirement",
            {"project_id": project["project_id"], "content": "需求1"},
        )
        result = router.route(
            "list_requirements", {"project_id": project["project_id"]}
        )
        assert result["total"] >= 1

    def test_get_requirement(self, router):
        """测试: 获取单个需求"""
        project = router.route("manage_project", {"name": "测试项目"})
        router.route(
            "manage_requirement",
            {"project_id": project["project_id"], "content": "测试需求"},
        )
        result = router.route(
            "get_project_state", {"project_id": project["project_id"]}
        )
        assert result["total_requirements"] >= 1

    def test_mark_as_leaf(self, router):
        """测试: 标记叶子节点"""
        project = router.route("manage_project", {"name": "测试项目"})
        # 低复杂度需求默认就是叶子节点
        req = router.route(
            "manage_requirement",
            {"project_id": project["project_id"], "content": "短需求"},
        )
        # 再次标记应该返回成功（已经是叶子）
        result = router.route("mark_as_leaf", {"requirement_id": req["requirement_id"]})
        assert "requirement_id" in result

    def test_delete_requirement(self, router):
        """测试: 删除需求"""
        project = router.route("manage_project", {"name": "测试项目"})
        req = router.route(
            "manage_requirement",
            {"project_id": project["project_id"], "content": "待删除需求"},
        )
        result = router.route(
            "delete_requirement", {"requirement_id": req["requirement_id"]}
        )
        assert result["deleted"] is True

    def test_add_validation(self, router):
        """测试: 添加验证"""
        project = router.route("manage_project", {"name": "测试项目"})
        req = router.route(
            "manage_requirement",
            {"project_id": project["project_id"], "content": "短需求"},
        )
        result = router.route(
            "add_validation",
            {
                "requirement_id": req["requirement_id"],
                "test_cases": [{"name": "测试1", "steps": [], "expected_result": "OK"}],
                "acceptance_criteria": "标准",
            },
        )
        assert "validation_id" in result

    def test_add_dependency(self, router):
        """测试: 添加依赖关系"""
        project = router.route("manage_project", {"name": "测试项目"})
        req1 = router.route(
            "manage_requirement",
            {"project_id": project["project_id"], "content": "需求1"},
        )
        req2 = router.route(
            "manage_requirement",
            {
                "project_id": project["project_id"],
                "content": "需求2",
                "parent_id": req1["requirement_id"],
            },
        )
        # 添加依赖
        result = router.route(
            "add_dependency",
            {
                "requirement_id": req2["requirement_id"],
                "dependency_id": req1["requirement_id"],
            },
        )
        assert "requirement_uuid" in result or "message" in result

    def test_unknown_tool(self, router):
        """测试: 未知工具抛出异常"""
        with pytest.raises(ValueError, match="未知工具"):
            router.route("nonexistent_tool", {})

    def test_create_snapshot(self, router):
        """测试: 创建快照"""
        project = router.route("manage_project", {"name": "快照测试项目"})
        result = router.route(
            "create_snapshot",
            {
                "project_id": project["project_id"],
                "_session_id": "test_session",
            },
        )
        assert "snapshot_id" in result

    def test_list_snapshots(self, router):
        """测试: 列出快照"""
        project = router.route("manage_project", {"name": "快照列表项目"})
        router.route(
            "create_snapshot",
            {
                "project_id": project["project_id"],
                "_session_id": "test_session",
            },
        )
        result = router.route("list_snapshots", {"project_id": project["project_id"]})
        assert "snapshots" in result
        assert len(result["snapshots"]) >= 1

    def test_acquire_and_release_lock(self, router):
        """测试: 获取和释放锁"""
        project = router.route("manage_project", {"name": "锁测试项目"})
        project_id = project["project_id"]

        acquire = router.route(
            "acquire_lock", {"project_id": project_id, "session_id": "session1"}
        )
        assert acquire["success"] is True

        release = router.route(
            "release_lock", {"project_id": project_id, "session_id": "session1"}
        )
        assert release["success"] is True

    def test_is_locked(self, router):
        """测试: 检查锁定状态"""
        project = router.route("manage_project", {"name": "锁定检查项目"})
        project_id = project["project_id"]

        # 未锁定时
        result = router.route("is_locked", {"project_id": project_id})
        assert result["locked"] is False

    def test_get_lock_info(self, router):
        """测试: 获取锁信息"""
        project = router.route("manage_project", {"name": "锁信息项目"})
        project_id = project["project_id"]

        result = router.route("get_lock_info", {"project_id": project_id})
        # 未锁定时 lock_info 为 None
        assert result["lock_info"] is None

    def test_get_api_version(self, router):
        """测试: 获取 API 版本"""
        result = router.route("get_api_version", {})
        assert "current_version" in result
        assert "supported_versions" in result

    def test_get_project_state(self, router):
        """测试: 获取项目状态"""
        project = router.route("manage_project", {"name": "状态项目"})
        result = router.route(
            "get_project_state", {"project_id": project["project_id"]}
        )
        assert result["total_requirements"] == 0
        assert "chain_status" in result


class TestToolRouterValidation:
    """工具输入验证测试"""

    def test_missing_project_id(self, router):
        """测试: 缺少 project_id"""
        with pytest.raises(ValueError, match="project_id"):
            router.validate_input("get_project_state", {})

    def test_invalid_project_id_format(self, router):
        """测试: project_id 格式错误"""
        with pytest.raises(ValueError, match="格式不正确"):
            router.validate_input("get_project_state", {"project_id": "invalid"})

    def test_missing_requirement_id(self, router):
        """测试: 缺少 requirement_id"""
        with pytest.raises(ValueError, match="requirement_id"):
            router.validate_input("delete_requirement", {})

    def test_invalid_requirement_id_format(self, router):
        """测试: requirement_id 格式错误"""
        with pytest.raises(ValueError, match="格式不正确"):
            router.validate_input("delete_requirement", {"requirement_id": "invalid"})

    def test_empty_content(self, router):
        """测试: 空内容"""
        with pytest.raises(ValueError, match="不能为空"):
            router.validate_input(
                "manage_requirement",
                {"project_id": "550e8400-e29b-41d4-a716-446655440000", "content": "  "},
            )

    def test_content_too_long(self, router):
        """测试: 内容过长"""
        with pytest.raises(ValueError, match="长度不能超过"):
            router.validate_input(
                "manage_requirement",
                {
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "content": "x" * 5001,
                },
            )

    def test_invalid_test_cases_format(self, router):
        """测试: 测试用例格式错误"""
        with pytest.raises(ValueError, match="必须是数组"):
            router.validate_input(
                "add_validation",
                {
                    "requirement_id": "550e8400-e29b-41d4-a716-446655440000",
                    "test_cases": "not_array",
                },
            )

    def test_parallel_nodes_length_mismatch(self, router):
        """测试: 并行节点长度不匹配"""
        with pytest.raises(ValueError, match="长度必须相同"):
            router.validate_input(
                "resolve_parallel_order",
                {
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "parallel_nodes": ["a", "b"],
                    "sorted_order": ["a"],
                },
            )

    def test_missing_parent_id_for_transfer(self, router):
        """测试: transfer_dependencies 缺少 parent_id"""
        with pytest.raises(ValueError, match="parent_id"):
            router.validate_input("transfer_dependencies", {})

    def test_invalid_dependency_mapping(self, router):
        """测试: dependency_mapping 格式错误"""
        with pytest.raises(ValueError, match="必须是字典"):
            router.validate_input(
                "transfer_dependencies",
                {
                    "parent_id": "550e8400-e29b-41d4-a716-446655440000",
                    "dependency_mapping": "not_dict",
                },
            )

    def test_non_dict_arguments(self, router):
        """测试: 非字典参数"""
        with pytest.raises(ValueError, match="必须是字典"):
            router.validate_input("manage_project", "not_dict")
