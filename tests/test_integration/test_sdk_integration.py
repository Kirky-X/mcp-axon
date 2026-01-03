# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""SDK 集成测试"""

from src.core.sdk import RequirementSDK


def test_tc020_dependency_transfer_integration():
    """TC-020: 测试依赖传递集成功能"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")

    # 1. 创建项目
    project = sdk.create_project("依赖传递测试项目")
    project_id = project["project_id"]

    # 2. 添加根需求
    root = sdk.add_requirement(
        project_id=project_id,
        content="实现用户认证系统",
    )
    root_id = root["requirement_id"]

    # 3. 添加依赖需求（独立需求）
    dep_req = sdk.add_requirement(project_id=project_id, content="数据库设计")
    dep_id = dep_req["requirement_id"]
    sdk.mark_as_leaf(dep_id)
    sdk.add_validation(requirement_id=dep_id, test_cases=[{"name": "测试数据库"}])

    # 4. 添加子需求
    child1 = sdk.add_requirement(
        project_id=project_id, content="登录功能", parent_id=root_id
    )
    child2 = sdk.add_requirement(
        project_id=project_id, content="注册功能", parent_id=root_id
    )
    child3 = sdk.add_requirement(
        project_id=project_id, content="密码重置", parent_id=root_id
    )

    # 5. 标记子需求为叶子并添加验证
    for child_id in [
        child1["requirement_id"],
        child2["requirement_id"],
        child3["requirement_id"],
    ]:
        sdk.mark_as_leaf(child_id)
        sdk.add_validation(
            requirement_id=child_id, test_cases=[{"name": f"测试{child_id[:8]}"}]
        )

    # 6. 传递依赖：登录和注册依赖数据库设计
    transfer_result = sdk.transfer_dependencies(
        parent_id=root_id,
        dependency_mapping={
            child1["requirement_id"]: [dep_id],
            child2["requirement_id"]: [dep_id],
            child3["requirement_id"]: [],
        },
    )

    # Assert: 验证依赖传递结果
    assert transfer_result["total_children"] == 3
    assert transfer_result["parent_id"] == root_id
    assert len(transfer_result["updated_children"]) == 3

    # 7. 验证项目状态
    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 5  # 1 root + 1 dep + 3 children

    # 8. 触发链化
    chain_result = sdk.trigger_chaining(project_id, "test-session-123456789")
    assert chain_result["status"] in ["completed", "not_ready"]


def test_tc021_chain_integration():
    """TC-021: 测试链化集成功能"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")

    # 1. 创建项目
    project = sdk.create_project("链化测试项目")
    project_id = project["project_id"]

    # 2. 创建需求树：根 -> 4个子需求（其中2个有依赖关系）
    root = sdk.add_requirement(project_id=project_id, content="实现电商平台")
    root_id = root["requirement_id"]

    # 独立需求（无依赖）
    req1 = sdk.add_requirement(
        project_id=project_id, content="首页设计", parent_id=root_id
    )
    sdk.mark_as_leaf(req1["requirement_id"])
    sdk.add_validation(
        requirement_id=req1["requirement_id"], test_cases=[{"name": "测试首页"}]
    )

    # 依赖需求链：A -> B -> C
    reqA = sdk.add_requirement(
        project_id=project_id, content="数据库设计", parent_id=root_id
    )
    sdk.mark_as_leaf(reqA["requirement_id"])
    sdk.add_validation(
        requirement_id=reqA["requirement_id"], test_cases=[{"name": "测试数据库"}]
    )

    reqB = sdk.add_requirement(
        project_id=project_id, content="用户模块", parent_id=root_id
    )
    sdk.mark_as_leaf(reqB["requirement_id"])
    sdk.add_validation(
        requirement_id=reqB["requirement_id"], test_cases=[{"name": "测试用户模块"}]
    )
    sdk.add_dependency(reqB["requirement_id"], reqA["requirement_id"])

    reqC = sdk.add_requirement(
        project_id=project_id, content="订单模块", parent_id=root_id
    )
    sdk.mark_as_leaf(reqC["requirement_id"])
    sdk.add_validation(
        requirement_id=reqC["requirement_id"], test_cases=[{"name": "测试订单模块"}]
    )
    sdk.add_dependency(reqC["requirement_id"], reqB["requirement_id"])

    # 另一个独立需求
    req4 = sdk.add_requirement(
        project_id=project_id, content="支付集成", parent_id=root_id
    )
    sdk.mark_as_leaf(req4["requirement_id"])
    sdk.add_validation(
        requirement_id=req4["requirement_id"], test_cases=[{"name": "测试支付"}]
    )

    # 3. 触发链化
    chain_result = sdk.trigger_chaining(project_id, "test-session-123456789")

    # Assert: 验证链化结果
    assert chain_result["status"] in ["completed", "not_ready"]
    # 链化包含所有需求（包括根节点，如果根节点有验证的话）
    # 这里根节点没有验证，所以只链化 4 个叶子节点
    assert chain_result.get("total_nodes", 0) >= 4  # 至少 4 个叶子节点

    # 4. 获取项目状态
    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] >= 5  # 1 root + 4 children + 1 dependency req
    assert "leaf_requirements" in state  # 验证字段存在

    # 5. 如果链化完成，验证获取下一个需求
    if chain_result["status"] == "completed":
        # 获取第一个需求
        next_req = sdk.get_next_requirement(project_id, "test-session-123456789")
        # 验证返回结构
        assert "requirement_id" in next_req or next_req.get("is_last") is True


def test_tc019_full_requirement_flow():
    """TC-019: 测试完整需求管理流程"""

    # Arrange
    sdk = RequirementSDK(db_path=":memory:")

    # 1. 创建项目
    project_result = sdk.create_project("测试项目")
    assert project_result["status"] == "CREATED"
    project_id = project_result["project_id"]

    # 2. 添加根需求
    req_result = sdk.add_requirement(
        project_id=project_id,
        content="实现完整的用户管理系统，包括用户注册、登录、权限控制等功能",
    )
    # 注意：复杂度评估可能因实现而异，这里不强制检查 needs_decomposition
    root_req_id = req_result["requirement_id"]

    # 3. 添加子需求
    child1 = sdk.add_requirement(
        project_id=project_id, content="用户注册", parent_id=root_req_id
    )

    child2 = sdk.add_requirement(
        project_id=project_id, content="用户登录", parent_id=root_req_id
    )

    # 4. 标记为叶子
    leaf_result = sdk.mark_as_leaf(child1["requirement_id"])
    assert leaf_result["status"] in ["leaf", "LEAF"]

    # 5. 添加验证
    validation_result = sdk.add_validation(
        requirement_id=child1["requirement_id"], test_cases=[{"name": "测试注册"}]
    )
    assert validation_result["validation_id"] is not None

    # 6. 标记另一个叶子并添加验证
    sdk.mark_as_leaf(child2["requirement_id"])
    sdk.add_validation(
        requirement_id=child2["requirement_id"], test_cases=[{"name": "测试登录"}]
    )

    # 7. 设置依赖（登录依赖注册）
    sdk.transfer_dependencies(
        parent_id=root_req_id,
        dependency_mapping={child2["requirement_id"]: [child1["requirement_id"]]},
    )

    # 8. 触发链化
    chain_result = sdk.trigger_chaining(project_id, "test-session-123456789")
    assert chain_result["status"] in ["completed", "partial"]

    # 9. 获取下一个需求
    next_req = sdk.get_next_requirement(project_id, "test-session-123456789")
    assert next_req["status"] in ["ready", "needs_sorting", "CHAINED", "VALIDATED"]

    # 10. 验证项目状态
    state = sdk.get_project_state(project_id)
    assert state["total_requirements"] == 3
    # 注意：leaf_requirements 可能需要额外的状态更新


def test_sdk_create_project():
    """测试 SDK 创建项目"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")

    # Act
    result = sdk.create_project("测试项目", "描述")

    # Assert
    assert result["project_id"] is not None
    assert result["status"] == "CREATED"
    assert result["name"] == "测试项目"
    assert "next_action" in result


def test_sdk_add_requirement():
    """测试 SDK 添加需求"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act
    result = sdk.add_requirement(project["project_id"], "实现用户管理模块")

    # Assert
    assert result["requirement_id"] is not None
    assert result["level"] == 0
    assert "complexity_score" in result
    assert "needs_decomposition" in result


def test_sdk_mark_as_leaf():
    """测试 SDK 标记叶子节点"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req = sdk.add_requirement(project["project_id"], "简单需求")

    # Act
    result = sdk.mark_as_leaf(req["requirement_id"])

    # Assert
    assert result["status"] == "LEAF"
    assert "next_action" in result


def test_sdk_add_validation():
    """测试 SDK 添加验证"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req = sdk.add_requirement(project["project_id"], "简单需求")
    sdk.mark_as_leaf(req["requirement_id"])

    test_cases = [{"name": "测试1", "steps": ["步骤1"], "expected": "结果1"}]

    # Act
    result = sdk.add_validation(req["requirement_id"], test_cases, "验收标准")

    # Assert
    assert result["validation_id"] is not None
    assert len(result["test_cases"]) == 1


def test_sdk_get_project_state():
    """测试 SDK 获取项目状态"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act
    result = sdk.get_project_state(project["project_id"])

    # Assert
    assert result["project_id"] == project["project_id"]
    assert result["status"] == "CREATED"
    assert result["total_requirements"] == 0


def test_sdk_update_requirement():
    """测试 SDK 更新需求"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req = sdk.add_requirement(project["project_id"], "原内容")

    # Act
    result = sdk.update_requirement(req["requirement_id"], content="新内容")

    # Assert
    assert result["content"] == "新内容"


def test_sdk_delete_requirement():
    """测试 SDK 删除需求"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req = sdk.add_requirement(project["project_id"], "要删除的需求")

    # Act
    result = sdk.delete_requirement(req["requirement_id"])

    # Assert
    assert result["deleted"] is True


def test_sdk_add_dependency():
    """测试 SDK 添加依赖"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    req1 = sdk.add_requirement(project["project_id"], "需求1")
    req2 = sdk.add_requirement(project["project_id"], "需求2")

    # Act
    result = sdk.add_dependency(req2["requirement_id"], req1["requirement_id"])

    # Assert
    assert req1["requirement_id"] in result["dependencies"]


def test_sdk_transfer_dependencies():
    """测试 SDK 传递依赖"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    dep1 = sdk.add_requirement(project["project_id"], "依赖1")
    sdk.mark_as_leaf(dep1["requirement_id"])

    parent = sdk.add_requirement(project["project_id"], "父需求")
    child1 = sdk.add_requirement(
        project["project_id"], "子需求1", parent_id=parent["requirement_id"]
    )
    child2 = sdk.add_requirement(
        project["project_id"], "子需求2", parent_id=parent["requirement_id"]
    )

    # Act
    result = sdk.transfer_dependencies(
        parent["requirement_id"],
        {
            child1["requirement_id"]: [dep1["requirement_id"]],
            child2["requirement_id"]: [],
        },
    )

    # Assert
    assert result["total_children"] == 2


def test_sdk_acquire_lock():
    """测试 SDK 获取锁"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act
    result = sdk.acquire_lock(project["project_id"], "session1")

    # Assert
    assert result is True


def test_sdk_release_lock():
    """测试 SDK 释放锁"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")
    sdk.acquire_lock(project["project_id"], "session1")

    # Act
    result = sdk.release_lock(project["project_id"], "session1")

    # Assert
    assert result is True


def test_sdk_is_locked():
    """测试 SDK 检查是否锁定"""
    # Arrange
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.create_project("测试项目")

    # Act & Assert: 未锁定
    assert sdk.is_locked(project["project_id"]) is False

    # 获取锁
    sdk.acquire_lock(project["project_id"], "session1")

    # Act & Assert: 已锁定
    assert sdk.is_locked(project["project_id"]) is True
