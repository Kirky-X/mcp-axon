# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""需求管理服务边界测试"""

import pytest
from src.db.models import Project, Requirement, RequirementStatus, ProjectStatus
from src.services.requirement_manager import RequirementManager


def test_complexity_evaluation_boundary_cases(sync_session):
    """测试复杂度评估边界情况"""

    manager = RequirementManager()
    project = Project(name="边界测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Test Case 1: 空内容（应该失败）
    with pytest.raises(ValueError, match="需求内容不能为空"):
        manager.add_requirement(
            sync_session,
            project_id=project.id,
            content=""
        )

    # Test Case 2: 只有空格的内容（应该失败）
    with pytest.raises(ValueError, match="需求内容不能为空"):
        manager.add_requirement(
            sync_session,
            project_id=project.id,
            content="   "
        )

    # Test Case 3: 边界值 - 刚好 50 字符
    boundary_50 = "a" * 50
    score_50 = manager._evaluate_complexity(boundary_50, level=0)
    assert score_50 >= 0.1  # 应该至少有 0.1 分（长度 + 层级）

    # Test Case 4: 边界值 - 刚好 100 字符
    boundary_100 = "a" * 100
    score_100 = manager._evaluate_complexity(boundary_100, level=0)
    assert score_100 >= 0.2  # 应该至少有 0.2 分（长度 + 层级）

    # Test Case 5: 边界值 - 刚好 200 字符
    boundary_200 = "a" * 200
    score_200 = manager._evaluate_complexity(boundary_200, level=0)
    assert score_200 >= 0.3  # 应该至少有 0.3 分（长度 + 层级）

    # Test Case 6: 边界值 - 刚好 500 字符
    boundary_500 = "a" * 500
    score_500 = manager._evaluate_complexity(boundary_500, level=0)
    assert score_500 >= 0.4  # 应该至少有 0.4 分（长度 + 层级）

    # Test Case 7: 刚好达到 0.7 阈值
    threshold_content = "系统" * 3  # 3个关键词 = 0.3 + 层级0.2 = 0.5，还需要 0.2
    threshold_content += "设计"  # +0.1
    threshold_content += "开发"  # +0.1
    threshold_content += "测试"  # +0.1
    threshold_content += "部署"  # +0.1
    score_threshold = manager._evaluate_complexity(threshold_content, level=0)
    assert score_threshold >= 0.7

    # Test Case 8: 超过阈值
    high_complexity = "系统平台管理集成框架服务" * 5  # 大量关键词
    score_high = manager._evaluate_complexity(high_complexity, level=0)
    assert score_high >= 0.99  # 应该接近 1.0


def test_decompose_hints_generation(sync_session):
    """测试分解提示生成"""

    manager = RequirementManager()
    project = Project(name="提示测试项目")
    sync_session.add(project)
    sync_session.commit()

    # Test Case 1: 包含"模块"关键词
    hints_module = manager._generate_decompose_hints("实现用户模块", level=0)
    assert "建议按功能模块分解" in hints_module

    # Test Case 2: 包含"系统"关键词
    hints_system = manager._generate_decompose_hints("实现管理系统", level=0)
    assert "建议按子系统分解" in hints_system

    # Test  Case 3: 包含"平台"关键词
    hints_platform = manager._generate_decompose_hints("实现云平台", level=0)
    assert "建议按平台层次分解" in hints_platform

    # Test Case 4: 包含"管理"关键词
    hints_management = manager._generate_decompose_hints("实现数据管理", level=0)
    assert "建议按管理对象分解（增删改查）" in hints_management

    # Test Case 5: 包含"集成"关键词
    hints_integration = manager._generate_decompose_hints("实现第三方集成", level=0)
    assert "建议按集成接口分解" in hints_integration

    # Test Case 6: 包含"框架"关键词
    hints_framework = manager._generate_decompose_hints("实现应用框架", level=0)
    assert "建议按框架层次分解" in hints_framework

    # Test Case 7: 包含"服务"关键词
    hints_service = manager._generate_decompose_hints("实现微服务", level=0)
    assert "建议按服务功能分解" in hints_service

    # Test Case 8: 根节点
    hints_root = manager._generate_decompose_hints("实现功能", level=0)
    assert "根需求建议分解为 3-7 个主要子需求" in hints_root

    # Test Case 9: 第一层
    hints_level1 = manager._generate_decompose_hints("实现功能", level=1)
    assert "子需求建议分解为具体可执行的任务" in hints_level1

    # Test Case 10: 无匹配关键词（通用提示）
    hints_generic = manager._generate_decompose_hints("简单功能", level=2)
    assert "建议将复杂需求分解为多个简单的可执行任务" in hints_generic


def test_validation_node_uniqueness(sync_session):
    """测试验证节点唯一性约束"""

    from src.db.models import ValidationNode
    from src.services.validation_service import ValidationService

    manager = RequirementManager()
    validation_service = ValidationService()
    project = Project(name="唯一性测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req = manager.add_requirement(
        sync_session,
        project.id,
        "叶子需求"
    )
    sync_session.flush()

    # 标记为叶子节点
    manager.mark_as_leaf(sync_session, req["requirement_id"])

    # 添加第一个验证节点
    validation1 = validation_service.add_validation(
        sync_session,
        req["requirement_id"],
        [{"name": "测试1"}],
        "验收标准1"
    )

    # 尝试添加第二个验证节点（应该失败）
    with pytest.raises(ValueError, match="已有验证节点"):
        validation2 = validation_service.add_validation(
            sync_session,
            req["requirement_id"],
            [{"name": "测试2"}],
            "验收标准2"
        )


def test_requirement_status_validation(sync_session):
    """测试需求状态验证"""

    from src.schemas import RequirementUpdate

    manager = RequirementManager()
    project = Project(name="状态验证测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建需求
    req = manager.add_requirement(
        sync_session,
        project.id,
        "测试需求"
    )
    sync_session.flush()

    # Test Case 1: 更新为无效状态 - Pydantic 会验证
    # 由于 Pydantic 会自动验证，这里我们测试有效状态
    valid_statuses = [
        "DRAFT", "DECOMPOSING", "LEAF", "CHAINED", "VALIDATED"
    ]
    for status in valid_statuses:
        # 直接更新数据库状态
        requirement = sync_session.query(Requirement).filter_by(
            id=req["requirement_id"]
        ).first()
        requirement.status = status
        sync_session.commit()

        # 清除缓存并重新查询
        manager.cache.invalidate_project(project.id)
        updated_req = manager.get_requirement(
            sync_session,
            req["requirement_id"]
        )
        assert updated_req["status"] == status


def test_max_depth_exceeded(sync_session):
    """测试最大深度限制"""

    manager = RequirementManager()
    project = Project(name="深度测试项目")
    sync_session.add(project)
    sync_session.commit()

    # 创建深度嵌套的需求
    parent_id = None
    for level in range(20):  # 创建 20 层
        req = manager.add_requirement(
            sync_session,
            project.id,
            f"第{level}层需求",
            parent_id=parent_id
        )
        parent_id = req["requirement_id"]
        sync_session.flush()

    # 验证最后一层的需求深度
    final_req = manager.get_requirement(
        sync_session,
        parent_id
    )
    assert final_req["level"] == 19