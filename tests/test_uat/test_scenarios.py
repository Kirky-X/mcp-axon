# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""端到端场景验收测试 (UAT-017 ~ UAT-019)"""

import pytest

from src.core.sdk import RequirementSDK


def test_uat017_microservices_scenario():
    """UAT-017: 微服务系统开发场景"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="微服务电商系统")
    project_id = project["project_id"]

    root = sdk.manage_requirement(project_id=project_id, content="开发电商微服务系统")

    user_service = sdk.manage_requirement(
        project_id=project_id, content="用户服务", parent_id=root["requirement_id"]
    )
    sdk.manage_requirement(
        project_id=project_id, content="订单服务", parent_id=root["requirement_id"]
    )
    sdk.manage_requirement(
        project_id=project_id, content="支付服务", parent_id=root["requirement_id"]
    )

    register_api = sdk.manage_requirement(
        project_id=project_id,
        content="用户注册 API",
        parent_id=user_service["requirement_id"],
    )
    login_api = sdk.manage_requirement(
        project_id=project_id,
        content="用户认证 API",
        parent_id=user_service["requirement_id"],
    )
    user_info_api = sdk.manage_requirement(
        project_id=project_id,
        content="用户信息管理 API",
        parent_id=user_service["requirement_id"],
    )

    for req_id in [register_api["requirement_id"], login_api["requirement_id"]]:
        sdk.add_validation(req_id, [{"name": "测试"}])

    sdk.transfer_dependencies(
        user_service["requirement_id"],
        {
            login_api["requirement_id"]: [register_api["requirement_id"]],
            user_info_api["requirement_id"]: [register_api["requirement_id"]],
        },
    )

    next_req = sdk.get_next_requirement(project_id, "test-session-123456789")
    assert next_req["status"] in ["ready", "needs_sorting", "CHAINED", "VALIDATED"]


def test_uat018_data_pipeline_scenario():
    """UAT-018: 数据分析系统开发场景"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="数据分析系统")
    project_id = project["project_id"]

    collect = sdk.manage_requirement(project_id=project_id, content="数据采集")
    sdk.add_validation(collect["requirement_id"], [{"name": "测试采集"}])

    clean = sdk.manage_requirement(project_id=project_id, content="数据清洗")
    sdk.add_validation(clean["requirement_id"], [{"name": "测试清洗"}])
    sdk.add_dependency(clean["requirement_id"], collect["requirement_id"])

    analyze = sdk.manage_requirement(project_id=project_id, content="数据分析")
    sdk.add_validation(analyze["requirement_id"], [{"name": "测试分析"}])
    sdk.add_dependency(analyze["requirement_id"], clean["requirement_id"])

    visualize = sdk.manage_requirement(project_id=project_id, content="数据可视化")
    sdk.add_validation(visualize["requirement_id"], [{"name": "测试可视化"}])
    sdk.add_dependency(visualize["requirement_id"], analyze["requirement_id"])

    next_req = sdk.get_next_requirement(project_id, "test-session-123456789")
    assert next_req["status"] in ["ready", "CHAINED"]
    if "requirement" in next_req:
        assert next_req["requirement"]["id"] == collect["requirement_id"]
    else:
        assert next_req["requirement_id"] == collect["requirement_id"]


def test_uat019_ai_assistant_scenario():
    """UAT-019: AI助手系统开发场景"""
    sdk = RequirementSDK(db_path=":memory:")
    project = sdk.manage_project(name="AI助手系统")
    project_id = project["project_id"]

    root = sdk.manage_requirement(project_id=project_id, content="AI助手")
    layer1 = sdk.manage_requirement(
        project_id=project_id, content="对话管理", parent_id=root["requirement_id"]
    )
    layer2 = sdk.manage_requirement(
        project_id=project_id, content="对话引擎", parent_id=layer1["requirement_id"]
    )
    layer3 = sdk.manage_requirement(
        project_id=project_id, content="意图识别", parent_id=layer2["requirement_id"]
    )
    layer4 = sdk.manage_requirement(
        project_id=project_id, content="NLP模型", parent_id=layer3["requirement_id"]
    )
    layer5 = sdk.manage_requirement(
        project_id=project_id, content="模型训练", parent_id=layer4["requirement_id"]
    )
    layer6 = sdk.manage_requirement(
        project_id=project_id, content="数据准备", parent_id=layer5["requirement_id"]
    )

    sdk.add_validation(layer6["requirement_id"], [{"name": "测试"}])

    leaf = sdk.get_requirement(layer6["requirement_id"])
    assert leaf["level"] == 6

    req_a = sdk.manage_requirement(project_id=project_id, content="需求A")
    req_b = sdk.manage_requirement(project_id=project_id, content="需求B")
    sdk.add_dependency(req_b["requirement_id"], req_a["requirement_id"])

    with pytest.raises(ValueError, match="循环依赖"):
        sdk.add_dependency(req_a["requirement_id"], req_b["requirement_id"])
