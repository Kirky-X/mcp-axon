# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""用户场景端到端测试"""

from src.core.sdk import RequirementSDK


def test_tc034_ecommerce_scenario():
    """TC-034: 测试电商系统场景"""

    sdk = RequirementSDK(db_path=":memory:")

    # 1. 创建项目
    project = sdk.manage_project(name="电商系统")

    # 2. 添加根需求
    root = sdk.manage_requirement(
        project_id=project["project_id"], content="电商系统开发"
    )

    # 3. 分解为模块
    user_module = sdk.manage_requirement(
        project_id=project["project_id"],
        content="用户模块",
        parent_id=root["requirement_id"],
    )
    sdk.manage_requirement(
        project_id=project["project_id"],
        content="订单模块",
        parent_id=root["requirement_id"],
    )

    # 4. 用户模块进一步分解
    register = sdk.manage_requirement(
        project_id=project["project_id"],
        content="用户注册",
        parent_id=user_module["requirement_id"],
    )
    login = sdk.manage_requirement(
        project_id=project["project_id"],
        content="用户登录",
        parent_id=user_module["requirement_id"],
    )

    # 5. 标记叶子并添加验证
    # 需求默认是叶子节点(register["requirement_id"])
    sdk.add_validation(register["requirement_id"], [{"name": "测试注册"}])

    # 需求默认是叶子节点(login["requirement_id"])
    sdk.add_validation(login["requirement_id"], [{"name": "测试登录"}])

    # 6. 设置依赖（登录依赖注册）
    sdk.transfer_dependencies(
        user_module["requirement_id"],
        {login["requirement_id"]: [register["requirement_id"]]},
    )

    # 7. 触发链化
    sdk.trigger_chaining(project["project_id"], "test-session-123456789")
    next_req = sdk.get_next_requirement(project["project_id"], "test-session-123456789")

    # Assert
    assert next_req["status"] in ["ready", "needs_sorting", "CHAINED"]


def test_data_pipeline_scenario():
    """测试数据 pipeline 场景"""
    sdk = RequirementSDK(db_path=":memory:")

    # 创建项目
    project = sdk.manage_project(name="数据分析系统")

    # 创建线性依赖链
    collect = sdk.manage_requirement(
        project_id=project["project_id"], content="数据采集"
    )
    # 需求默认是叶子节点(collect["requirement_id"])
    sdk.add_validation(collect["requirement_id"], [{"name": "测试采集"}])

    clean = sdk.manage_requirement(project_id=project["project_id"], content="数据清洗")
    # 需求默认是叶子节点(clean["requirement_id"])
    sdk.add_validation(clean["requirement_id"], [{"name": "测试清洗"}])
    sdk.add_dependency(clean["requirement_id"], collect["requirement_id"])

    analyze = sdk.manage_requirement(
        project_id=project["project_id"], content="数据分析"
    )
    # 需求默认是叶子节点(analyze["requirement_id"])
    sdk.add_validation(analyze["requirement_id"], [{"name": "测试分析"}])
    sdk.add_dependency(analyze["requirement_id"], clean["requirement_id"])

    # 触发链化
    sdk.trigger_chaining(project["project_id"], "test-session-123456789")
    next_req = sdk.get_next_requirement(project["project_id"], "test-session-123456789")

    # Assert
    assert next_req["status"] in ["ready", "CHAINED"]
    # 根据不同的返回格式检查
    if "requirement" in next_req:
        assert next_req["requirement"]["id"] == collect["requirement_id"]
    else:
        assert next_req["requirement_id"] == collect["requirement_id"]
