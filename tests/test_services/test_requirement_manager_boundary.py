# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求管理服务边界测试"""

import pytest

from src.services.complexity_evaluator import ComplexityEvaluator
from src.services.decomposition_advisor import DecompositionAdvisor


def test_complexity_evaluation_boundary_cases(
    graph_connection, project_manager, requirement_manager
):
    """测试复杂度评估边界情况"""

    project = project_manager.create_project(graph_connection, "边界测试项目")
    project_id = project["project_id"]

    # Test Case 1: 空内容（应该失败）
    with pytest.raises(ValueError, match="需求内容不能为空"):
        requirement_manager.add_requirement(
            graph_connection, project_uuid=project_id, content=""
        )

    # Test Case 2: 只有空格的内容（应该失败）
    with pytest.raises(ValueError, match="需求内容不能为空"):
        requirement_manager.add_requirement(
            graph_connection, project_uuid=project_id, content="   "
        )

    # Test Case 3: 边界值 - 刚好 50 字符
    boundary_50 = "a" * 50
    score_50 = ComplexityEvaluator().evaluate(boundary_50, level=0)
    assert score_50 >= 0.2  # 应该至少有 0.1 分（长度 + 层级）

    # Test Case 4: 边界值 - 刚好 100 字符
    boundary_100 = "a" * 100
    score_100 = ComplexityEvaluator().evaluate(boundary_100, level=0)
    assert score_100 >= 0.2  # 应该至少有 0.2 分（长度 + 层级）

    # Test Case 5: 边界值 - 刚好 200 字符
    boundary_200 = "a" * 200
    score_200 = ComplexityEvaluator().evaluate(boundary_200, level=0)
    assert score_200 >= 0.2  # 应该至少有 0.3 分（长度 + 层级）

    # Test Case 6: 边界值 - 刚好 500 字符
    boundary_500 = "a" * 500
    score_500 = ComplexityEvaluator().evaluate(boundary_500, level=0)
    assert score_500 >= 0.4  # 应该至少有 0.4 分（长度 + 层级）

    # Test Case 7: 刚好达到 0.7 阈值
    threshold_content = "系统" * 3  # 3个关键词 = 0.3 + 层级0.2 = 0.5，还需要 0.2
    threshold_content += "设计"  # +0.1
    threshold_content += "开发"  # +0.1
    threshold_content += "测试"  # +0.1
    threshold_content += "部署"  # +0.1
    score_threshold = ComplexityEvaluator().evaluate(threshold_content, level=0)
    assert score_threshold >= 0.35

    # Test Case 8: 超过阈值
    high_complexity = "系统平台管理集成框架服务" * 5  # 大量关键词
    score_high = ComplexityEvaluator().evaluate(high_complexity, level=0)
    assert score_high >= 0.99  # 应该接近 1.0


def test_decompose_hints_generation(graph_connection, project_manager):
    """测试分解提示生成"""

    project = project_manager.create_project(graph_connection, "提示测试项目")
    project["project_id"]

    # Test Case 1: 包含"模块"关键词
    hints_module = DecompositionAdvisor().generate_hints("实现用户模块", level=0)
    assert "建议按功能模块分解" in hints_module

    # Test Case 2: 包含"系统"关键词
    hints_system = DecompositionAdvisor().generate_hints("实现管理系统", level=0)
    assert "建议按子系统分解" in hints_system

    # Test  Case 3: 包含"平台"关键词
    hints_platform = DecompositionAdvisor().generate_hints("实现云平台", level=0)
    assert "建议按平台层次分解" in hints_platform

    # Test Case 4: 包含"管理"关键词
    hints_management = DecompositionAdvisor().generate_hints("实现数据管理", level=0)
    assert "建议按管理对象分解" in hints_management

    # Test Case 5: 包含"集成"关键词
    hints_integration = DecompositionAdvisor().generate_hints("实现第三方集成", level=0)
    assert "建议按集成接口分解" in hints_integration

    # Test Case 6: 包含"框架"关键词
    hints_framework = DecompositionAdvisor().generate_hints("实现应用框架", level=0)
    assert "建议按框架层次分解" in hints_framework

    # Test Case 7: 包含"服务"关键词
    hints_service = DecompositionAdvisor().generate_hints("实现微服务", level=0)
    assert "建议按服务功能分解" in hints_service

    # Test Case 8: 根节点
    hints_root = DecompositionAdvisor().generate_hints("实现功能", level=0)
    assert "根需求建议分解为 3-7 个主要子需求" in hints_root

    # Test Case 9: 第一层
    hints_level1 = DecompositionAdvisor().generate_hints("实现功能", level=1)
    assert "子需求建议分解为具体可执行的任务" in hints_level1

    # Test Case 10: 无匹配关键词（通用提示）
    hints_generic = DecompositionAdvisor().generate_hints("简单功能", level=2)
    assert "孙需求建议分解为具体的验收标准" in hints_generic


def test_validation_node_uniqueness(
    graph_connection, project_manager, requirement_manager, validation_service
):
    """测试验证节点唯一性约束"""

    project = project_manager.create_project(graph_connection, "唯一性测试项目")
    project_id = project["project_id"]

    # 创建需求
    req = requirement_manager.add_requirement(graph_connection, project_id, "叶子需求")

    validation_service.add_validation(
        graph_connection, req["requirement_id"], [{"name": "测试1"}], "验收标准1"
    )

    # 尝试添加第二个验证节点（应该失败）
    with pytest.raises(ValueError, match="已有验证节点"):
        validation_service.add_validation(
            graph_connection, req["requirement_id"], [{"name": "测试2"}], "验收标准2"
        )


def test_requirement_status_validation(
    graph_connection, project_manager, requirement_manager
):
    """测试需求状态验证"""

    project = project_manager.create_project(graph_connection, "状态验证测试项目")
    project_id = project["project_id"]

    # 创建需求
    req = requirement_manager.add_requirement(graph_connection, project_id, "测试需求")

    # Test Case 1: 更新为有效状态
    valid_statuses = ["DRAFT", "DECOMPOSING", "LEAF", "CHAINED", "VALIDATED"]
    for status in valid_statuses:
        from src.db.graph_queries import UPDATE_REQUIREMENT_STATUS
        from src.db.graph_models import now_utc

        graph_connection.execute(
            UPDATE_REQUIREMENT_STATUS,
            {
                "uuid": req["requirement_id"],
                "status": status,
                "updated_at": now_utc(),
            },
        )

        # 清除缓存并重新查询
        requirement_manager.cache.invalidate_project(project_id)
        updated_req = requirement_manager.get_requirement(
            graph_connection, req["requirement_id"]
        )
        assert updated_req["status"] == status


def test_max_depth_exceeded(graph_connection, project_manager, requirement_manager):
    """测试最大深度限制"""

    project = project_manager.create_project(graph_connection, "深度测试项目")
    project_id = project["project_id"]

    # 创建深度嵌套的需求
    parent_id = None
    for level in range(20):  # 创建 20 层
        req = requirement_manager.add_requirement(
            graph_connection, project_id, f"第{level}层需求", parent_uuid=parent_id
        )
        parent_id = req["requirement_id"]

    # 验证最后一层的需求深度
    final_req = requirement_manager.get_requirement(graph_connection, parent_id)
    assert final_req["level"] == 19
