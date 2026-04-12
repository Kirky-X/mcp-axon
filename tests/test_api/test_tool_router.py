# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""工具路由测试 - 埋缩版（8个接口）"""

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


class TestManageProject:
    """项目管理接口测试"""

    def test_create_project(self, router):
        """测试: 创建项目"""
        result = router.route(
            "manage_project",
            {"action": "create", "name": "测试项目", "description": "描述"},
        )
        assert "project_id" in result
        assert "next_action" in result

    def test_get_project(self, router):
        """测试: 获取项目"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        result = router.route(
            "manage_project",
            {"action": "get", "project_id": project["project_id"]},
        )
        assert result["name"] == "测试项目"

    def test_update_project(self, router):
        """测试: 更新项目"""
        project = router.route("manage_project", {"action": "create", "name": "旧名称"})
        result = router.route(
            "manage_project",
            {"action": "update", "project_id": project["project_id"], "name": "新名称"},
        )
        assert result["name"] == "新名称"


class TestManageRequirement:
    """需求管理接口测试"""

    def test_create_requirement(self, router):
        """测试: 创建需求"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        result = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "测试需求",
            },
        )
        assert "requirement_id" in result
        assert "complexity_score" in result

    def test_list_requirements(self, router):
        """测试: 列出需求"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "需求1",
            },
        )
        result = router.route(
            "manage_requirement",
            {"action": "list", "project_id": project["project_id"]},
        )
        assert result["total"] >= 1

    def test_delete_requirement(self, router):
        """测试: 删除需求"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        req = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "待删除需求",
            },
        )
        result = router.route(
            "manage_requirement",
            {"action": "delete", "requirement_id": req["requirement_id"]},
        )
        assert result["deleted"] is True

    def test_mark_as_leaf(self, router):
        """测试: 标记叶子节点"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        req = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "短需求",
            },
        )
        result = router.route(
            "manage_requirement",
            {"action": "mark_leaf", "requirement_id": req["requirement_id"]},
        )
        assert "requirement_id" in result


class TestManageDependency:
    """依赖管理接口测试"""

    def test_add_single_dependency(self, router):
        """测试: 添加单个依赖"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        req1 = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "需求1",
            },
        )
        req2 = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "需求2",
                "parent_id": req1["requirement_id"],
            },
        )
        result = router.route(
            "manage_dependency",
            {
                "requirement_id": req2["requirement_id"],
                "dependency_id": req1["requirement_id"],
            },
        )
        assert "requirement_uuid" in result or "message" in result

    def test_transfer_dependencies(self, router):
        """测试: 批量传递依赖"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        parent = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "父需求",
            },
        )
        child1 = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "子需求1",
                "parent_id": parent["requirement_id"],
            },
        )
        child2 = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "子需求2",
                "parent_id": parent["requirement_id"],
            },
        )
        result = router.route(
            "manage_dependency",
            {
                "parent_id": parent["requirement_id"],
                "dependency_mapping": {
                    child1["requirement_id"]: [],
                    child2["requirement_id"]: [child1["requirement_id"]],
                },
            },
        )
        assert "parent_id" in result or "updated_children" in result


class TestManageValidation:
    """验证管理接口测试"""

    def test_add_validation(self, router):
        """测试: 添加验证"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        req = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "短需求",
            },
        )
        result = router.route(
            "manage_validation",
            {
                "requirement_id": req["requirement_id"],
                "test_cases": [{"name": "测试1", "steps": [], "expected_result": "OK"}],
                "acceptance_criteria": "标准",
            },
        )
        assert "validation_id" in result

    def test_run_validation(self, router):
        """测试: 执行验证"""
        project = router.route(
            "manage_project", {"action": "create", "name": "测试项目"}
        )
        req = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "短需求",
            },
        )
        router.route(
            "manage_validation",
            {"requirement_id": req["requirement_id"], "test_cases": [{"name": "测试"}]},
        )
        result = router.route(
            "manage_validation",
            {
                "requirement_id": req["requirement_id"],
                "execution_result": "任务完成输出",
            },
        )
        assert "requirement_id" in result or "validation_passed" in result


class TestManageExecution:
    """执行流程接口测试"""

    def test_get_project_state(self, router):
        """测试: 获取项目状态"""
        project = router.route(
            "manage_project", {"action": "create", "name": "状态项目"}
        )
        result = router.route(
            "manage_execution",
            {"action": "state", "project_id": project["project_id"]},
        )
        assert result["total_requirements"] == 0
        assert "chain_status" in result

    def test_trigger_chaining(self, router):
        """测试: 触发链化"""
        project = router.route(
            "manage_project", {"action": "create", "name": "链化项目"}
        )
        req = router.route(
            "manage_requirement",
            {
                "action": "create",
                "project_id": project["project_id"],
                "content": "需求",
            },
        )
        router.route(
            "manage_validation",
            {"requirement_id": req["requirement_id"], "test_cases": [{"name": "测试"}]},
        )
        result = router.route(
            "manage_execution",
            {"action": "trigger", "project_id": project["project_id"]},
        )
        assert "chained_count" in result or "status" in result


class TestManageSnapshot:
    """快照管理接口测试"""

    def test_create_snapshot(self, router):
        """测试: 创建快照"""
        project = router.route(
            "manage_project", {"action": "create", "name": "快照项目"}
        )
        result = router.route(
            "manage_snapshot",
            {
                "action": "create",
                "project_id": project["project_id"],
                "_session_id": "test",
            },
        )
        assert "snapshot_id" in result

    def test_list_snapshots(self, router):
        """测试: 列出快照"""
        project = router.route(
            "manage_project", {"action": "create", "name": "快照列表"}
        )
        router.route(
            "manage_snapshot",
            {
                "action": "create",
                "project_id": project["project_id"],
                "_session_id": "test",
            },
        )
        result = router.route(
            "manage_snapshot",
            {"action": "list", "project_id": project["project_id"]},
        )
        assert "snapshots" in result
        assert len(result["snapshots"]) >= 1


class TestManageLock:
    """锁管理接口测试"""

    def test_acquire_and_release_lock(self, router):
        """测试: 获取和释放锁"""
        project = router.route("manage_project", {"action": "create", "name": "锁项目"})
        project_id = project["project_id"]

        acquire = router.route(
            "manage_lock",
            {"action": "acquire", "project_id": project_id, "session_id": "session1"},
        )
        assert acquire["success"] is True

        release = router.route(
            "manage_lock",
            {"action": "release", "project_id": project_id, "session_id": "session1"},
        )
        assert release["success"] is True

    def test_check_lock(self, router):
        """测试: 检查锁定状态"""
        project = router.route("manage_project", {"action": "create", "name": "锁检查"})
        project_id = project["project_id"]

        result = router.route(
            "manage_lock", {"action": "check", "project_id": project_id}
        )
        assert result["locked"] is False

    def test_get_lock_info(self, router):
        """测试: 获取锁信息"""
        project = router.route("manage_project", {"action": "create", "name": "锁信息"})
        project_id = project["project_id"]

        result = router.route(
            "manage_lock", {"action": "info", "project_id": project_id}
        )
        assert result["lock_info"] is None


class TestGetApiVersion:
    """API版本接口测试"""

    def test_get_api_version(self, router):
        """测试: 获取 API 版本"""
        result = router.route("get_api_version", {})
        assert "current_version" in result
        assert "supported_versions" in result


class TestUnknownTool:
    """未知工具测试"""

    def test_unknown_tool(self, router):
        """测试: 未知工具抛出异常"""
        with pytest.raises(ValueError, match="未知工具"):
            router.route("nonexistent_tool", {})


class TestValidation:
    """输入验证测试"""

    def test_missing_action(self, router):
        """测试: 缺少 action"""
        with pytest.raises(ValueError, match="action"):
            router.validate_input("manage_project", {"name": "测试"})

    def test_invalid_action(self, router):
        """测试: 无效的 action"""
        with pytest.raises(ValueError, match="action"):
            router.validate_input(
                "manage_project",
                {"action": "invalid", "name": "测试"},
            )

    def test_missing_project_id_for_get(self, router):
        """测试: get 操作缺少 project_id"""
        with pytest.raises(ValueError, match="project_id"):
            router.validate_input("manage_project", {"action": "get"})

    def test_missing_project_id_for_create(self, router):
        """测试: create 操作缺少 name"""
        with pytest.raises(ValueError, match="name"):
            router.validate_input("manage_project", {"action": "create"})

    def test_invalid_project_id_format(self, router):
        """测试: project_id 格式错误"""
        with pytest.raises(ValueError, match="格式不正确|必填"):
            router.validate_input(
                "manage_project",
                {"action": "get", "project_id": "invalid"},
            )

    def test_missing_requirement_id_for_delete(self, router):
        """测试: delete 操作缺少 requirement_id"""
        with pytest.raises(ValueError, match="requirement_id"):
            router.validate_input("manage_requirement", {"action": "delete"})

    def test_empty_content_for_create(self, router):
        """测试: create 操作空内容"""
        with pytest.raises(ValueError, match="不能为空"):
            router.validate_input(
                "manage_requirement",
                {
                    "action": "create",
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "content": "  ",
                },
            )

    def test_content_too_long(self, router):
        """测试: 内容过长"""
        with pytest.raises(ValueError, match="长度不能超过"):
            router.validate_input(
                "manage_requirement",
                {
                    "action": "create",
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "content": "x" * 5001,
                },
            )

    def test_missing_params_for_dependency(self, router):
        """测试: manage_dependency 缺少必要参数"""
        with pytest.raises(ValueError, match="缺少必要参数"):
            router.validate_input("manage_dependency", {})

    def test_missing_session_id_for_acquire(self, router):
        """测试: acquire 操作缺少 session_id"""
        with pytest.raises(ValueError, match="session_id"):
            router.validate_input(
                "manage_lock",
                {
                    "action": "acquire",
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                },
            )

    def test_non_dict_arguments(self, router):
        """测试: 非字典参数"""
        with pytest.raises(ValueError, match="必须是字典"):
            router.validate_input("manage_project", "not_dict")

    def test_invalid_test_cases_format(self, router):
        """测试: 测试用例格式错误"""
        with pytest.raises(ValueError, match="必须是数组"):
            router.validate_input(
                "manage_validation",
                {
                    "requirement_id": "550e8400-e29b-41d4-a716-446655440000",
                    "test_cases": "not_array",
                },
            )

    def test_execution_result_too_long(self, router):
        """测试: execution_result 过长"""
        with pytest.raises(ValueError, match="不能超过"):
            router.validate_input(
                "manage_validation",
                {
                    "requirement_id": "550e8400-e29b-41d4-a716-446655440000",
                    "execution_result": "x" * 10001,
                },
            )
