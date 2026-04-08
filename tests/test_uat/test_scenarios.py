# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""端到端场景验收测试 (UAT-017 ~ UAT-019)"""

import pytest

from src.core.sdk import RequirementSDK


def test_uat017_microservices_scenario():
    """UAT-017: 微服务系统开发场景"""

    sdk = RequirementSDK(db_path=":memory:")

    # 1. 创建项目
    project = sdk.create_project("微服务电商系统")
    project_id = project["project_id"]

    # 2. 添加根需求
    root = sdk.add_requirement(project_id, "开发电商微服务系统")

    # 3. 分解为服务模块
    user_service = sdk.add_requirement(
        project_id, "用户服务", parent_id=root["requirement_id"]
    )
    sdk.add_requirement(project_id, "订单服务", parent_id=root["requirement_id"])
    sdk.add_requirement(project_id, "支付服务", parent_id=root["requirement_id"])

    # 4. 分解用户服务
    register_api = sdk.add_requirement(
        project_id, "用户注册 API", parent_id=user_service["requirement_id"]
    )
    login_api = sdk.add_requirement(
        project_id, "用户认证 API", parent_id=user_service["requirement_id"]
    )
    user_info_api = sdk.add_requirement(
        project_id,
        "用户信息管理 API",
        parent_id=user_service["requirement_id"],
    )

    # 5. 标记叶子并添加验证
    for req_id in [register_api["requirement_id"], login_api["requirement_id"]]:
        sdk.add_validation(req_id, [{"name": "测试"}])

    # 6. 设置依赖
    sdk.transfer_dependencies(
        user_service["requirement_id"],
        {
            login_api["requirement_id"]: [register_api["requirement_id"]],
            user_info_api["requirement_id"]: [register_api["requirement_id"]],
        },
    )

    # 7. 触发链化
    next_req = sdk.get_next_requirement(project_id, "test-session-123456789")

    # Assert
    assert next_req["status"] in ["ready", "needs_sorting", "CHAINED", "VALIDATED"]


def test_uat018_data_pipeline_scenario():
    """UAT-018: 数据分析系统开发场景"""
    sdk = RequirementSDK(db_path=":memory:")

    # 创建项目
    project = sdk.create_project("数据分析系统")
    project_id = project["project_id"]

    # 创建线性依赖链
    collect = sdk.add_requirement(project_id, "数据采集")
    sdk.add_validation(collect["requirement_id"], [{"name": "测试采集"}])

    clean = sdk.add_requirement(project_id, "数据清洗")
    sdk.add_validation(clean["requirement_id"], [{"name": "测试清洗"}])
    sdk.add_dependency(clean["requirement_id"], collect["requirement_id"])

    analyze = sdk.add_requirement(project_id, "数据分析")
    sdk.add_validation(analyze["requirement_id"], [{"name": "测试分析"}])
    sdk.add_dependency(analyze["requirement_id"], clean["requirement_id"])

    visualize = sdk.add_requirement(project_id, "数据可视化")
    sdk.add_validation(visualize["requirement_id"], [{"name": "测试可视化"}])
    sdk.add_dependency(visualize["requirement_id"], analyze["requirement_id"])

    # 触发链化
    next_req = sdk.get_next_requirement(project_id, "test-session-123456789")

    # Assert: 线性依赖链，应该直接返回第一个需求
    assert next_req["status"] in ["ready", "CHAINED"]
    # 根据不同的返回格式检查
    if "requirement" in next_req:
        assert next_req["requirement"]["id"] == collect["requirement_id"]
    else:
        assert next_req["requirement_id"] == collect["requirement_id"]


def test_uat019_ai_assistant_scenario():
    """UAT-019: AI助手系统开发场景"""
    sdk = RequirementSDK(db_path=":memory:")

    # 创建项目
    project = sdk.create_project("AI助手系统")
    project_id = project["project_id"]

    # 创建深层嵌套需求（6层）
    root = sdk.add_requirement(project_id, "AI助手")
    layer1 = sdk.add_requirement(
        project_id, "对话管理", parent_id=root["requirement_id"]
    )
    layer2 = sdk.add_requirement(
        project_id, "对话引擎", parent_id=layer1["requirement_id"]
    )
    layer3 = sdk.add_requirement(
        project_id, "意图识别", parent_id=layer2["requirement_id"]
    )
    layer4 = sdk.add_requirement(
        project_id, "NLP模型", parent_id=layer3["requirement_id"]
    )
    layer5 = sdk.add_requirement(
        project_id, "模型训练", parent_id=layer4["requirement_id"]
    )
    layer6 = sdk.add_requirement(
        project_id, "数据准备", parent_id=layer5["requirement_id"]
    )

    # 标记叶子
    sdk.add_validation(layer6["requirement_id"], [{"name": "测试"}])

    # 验证深度
    leaf = sdk.get_requirement(layer6["requirement_id"])
    assert leaf["level"] == 6  # 0-based index，6 层深度

    # 测试循环依赖检测
    req_a = sdk.add_requirement(project_id, "需求A")
    req_b = sdk.add_requirement(project_id, "需求B")
    sdk.add_dependency(req_b["requirement_id"], req_a["requirement_id"])

    # 尝试创建循环
    with pytest.raises(ValueError, match="循环依赖"):
        sdk.add_dependency(req_a["requirement_id"], req_b["requirement_id"])
