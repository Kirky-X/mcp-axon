# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""核心功能验收测试 (UAT-001 ~ UAT-010)"""

import pytest
from src.core.sdk import RequirementSDK


def test_uat001_project_creation():
    """UAT-001: 项目创建与管理"""

    sdk = RequirementSDK(db_path=":memory:")

    # 创建项目
    result = sdk.create_project("我的第一个项目", "这是一个测试项目")

    assert result["project_id"] is not None
    assert result["status"] == "CREATED"
    assert "next_action" in result

    # 查询项目状态
    state = sdk.get_project_state(result["project_id"])
    assert state["status"] == "CREATED"


def test_uat002_requirement_complexity_evaluation():
    """UAT-002: 需求添加与复杂度评估"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 复杂需求
    complex_req = sdk.add_requirement(
        project["project_id"],
        "实现完整的用户管理系统，包括用户注册、登录、权限控制、角色管理等功能"
    )
    assert complex_req["needs_decomposition"] is True
    assert complex_req["complexity_score"] > 0.7

    # 简单需求
    simple_req = sdk.add_requirement(
        project["project_id"],
        "修改用户头像"
    )
    assert simple_req["needs_decomposition"] is False


def test_uat003_requirement_decomposition():
    """UAT-003: 需求分解与层级管理"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 添加根需求
    root = sdk.add_requirement(project["project_id"], "用户管理系统")

    # 分解为子需求
    child1 = sdk.add_requirement(
        project["project_id"],
        "用户注册功能",
        parent_id=root["requirement_id"]
    )
    child2 = sdk.add_requirement(
        project["project_id"],
        "用户登录功能",
        parent_id=root["requirement_id"]
    )

    assert child1["level"] == 1
    assert child2["level"] == 1


def test_uat004_dependency_management():
    """UAT-004: 依赖关系管理"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建需求
    dep1 = sdk.add_requirement(project["project_id"], "依赖1")
    sdk.mark_as_leaf(dep1["requirement_id"])

    parent = sdk.add_requirement(project["project_id"], "父需求")
    child = sdk.add_requirement(
        project["project_id"],
        "子需求",
        parent_id=parent["requirement_id"]
    )

    # 传递依赖
    sdk.transfer_dependencies(
        parent["requirement_id"],
        {child["requirement_id"]: [dep1["requirement_id"]]}
    )

    # 验证依赖传递成功
    with sdk._get_session() as session:
        from src.db.models import Requirement
        saved_child = session.get(Requirement, child["requirement_id"])
        assert dep1["requirement_id"] in saved_child.dependencies


def test_uat005_mark_as_leaf():
    """UAT-005: 叶子节点标记"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    req = sdk.add_requirement(project["project_id"], "叶子需求")
    result = sdk.mark_as_leaf(req["requirement_id"])

    assert result["status"] == "LEAF"
    assert "next_action" in result


def test_uat006_validation_configuration():
    """UAT-006: 验证节点配置"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    req = sdk.add_requirement(project["project_id"], "叶子需求")
    sdk.mark_as_leaf(req["requirement_id"])

    test_cases = [
        {
            "name": "测试用户注册",
            "steps": ["打开页面", "输入信息", "提交"],
            "expected": "注册成功"
        }
    ]

    result = sdk.add_validation(
        req["requirement_id"],
        test_cases,
        "用户能成功注册"
    )

    assert result["validation_id"] is not None
    assert len(result["test_cases"]) == 1


def test_uat007_auto_chaining_trigger():
    """UAT-007: 自动链化触发"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建多个叶子需求并配置验证
    for i in range(5):
        req = sdk.add_requirement(project["project_id"], f"需求{i}")
        sdk.mark_as_leaf(req["requirement_id"])
        sdk.add_validation(req["requirement_id"], [{"name": f"测试{i}"}])

    # 触发链化
    result = sdk.get_next_requirement(project["project_id"])

    assert result["status"] in ["CHAINED", "VALIDATED"]
    assert result["requirement_id"] is not None


def test_uat008_parallel_order_resolution():
    """UAT-008: 并行节点排序决策"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 创建并行节点
    req1 = sdk.add_requirement(project["project_id"], "需求1")
    sdk.mark_as_leaf(req1["requirement_id"])
    sdk.add_validation(req1["requirement_id"], [{"name": "测试1"}])

    req2 = sdk.add_requirement(project["project_id"], "需求2")
    sdk.mark_as_leaf(req2["requirement_id"])
    sdk.add_validation(req2["requirement_id"], [{"name": "测试2"}])

    # 触发链化
    result = sdk.get_next_requirement(project["project_id"])

    if result["status"] == "needs_sorting":
        # 应用排序
        sorted_order = result["parallel_nodes"]
        sdk.resolve_parallel_order(
            project["project_id"],
            result["parallel_nodes"],
            sorted_order
        )


def test_uat009_get_next_requirement():
    """UAT-009: 获取下一个需求"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    req = sdk.add_requirement(project["project_id"], "需求")
    sdk.mark_as_leaf(req["requirement_id"])
    sdk.add_validation(req["requirement_id"], [{"name": "测试"}])

    # 获取下一个需求
    result = sdk.get_next_requirement(project["project_id"])

    assert result["status"] in ["CHAINED", "VALIDATED"]
    assert result["requirement_id"] == req["requirement_id"]


def test_uat010_project_status_query():
    """UAT-010: 项目状态查询"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # 添加一些需求
    for i in range(3):
        req = sdk.add_requirement(project["project_id"], f"需求{i}")
        sdk.mark_as_leaf(req["requirement_id"])

    # 查询项目状态
    state = sdk.get_project_state(project["project_id"])

    assert state["project_id"] == project["project_id"]
    assert state["total_requirements"] == 3
    assert state["leaf_requirements"] == 3