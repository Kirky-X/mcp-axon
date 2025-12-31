# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""验证节点管理服务测试"""

import pytest
from src.db.models import Project, Requirement, RequirementStatus, ValidationStatus
from src.services.validation_service import ValidationService


def test_tc010_add_validation(sync_session):
    """TC-010: 测试添加验证节点"""

    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="叶子需求",
        status=RequirementStatus.LEAF.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    test_cases = [
        {
            "name": "测试用户注册",
            "steps": ["打开页面", "输入信息", "提交"],
            "expected": "注册成功"
        }
    ]

    # Act
    result = service.add_validation(
        sync_session,
        requirement_id=requirement.id,
        test_cases=test_cases,
        acceptance_criteria="用户能成功注册"
    )

    # Assert
    assert result["validation_id"] is not None
    assert result["requirement_id"] == requirement.id
    assert len(result["test_cases"]) == 1
    assert result["acceptance_criteria"] == "用户能成功注册"

    # 验证需求状态更新为 VALIDATED
    sync_session.refresh(requirement)
    assert requirement.status == RequirementStatus.VALIDATED.value


def test_add_validation_non_leaf_requirement(sync_session):
    """测试为非叶子节点添加验证（应失败）"""
    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="非叶子需求",
        status=RequirementStatus.DRAFT.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    # Act & Assert
    with pytest.raises(ValueError, match="只能为叶子节点添加验证"):
        service.add_validation(
            sync_session,
            requirement_id=requirement.id,
            test_cases=[{"name": "测试"}]
        )


def test_add_validation_duplicate(sync_session):
    """测试添加重复的验证节点（应失败）"""
    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="叶子需求",
        status=RequirementStatus.LEAF.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    # 添加第一个验证节点
    service.add_validation(
        sync_session,
        requirement_id=requirement.id,
        test_cases=[{"name": "测试1"}]
    )

    # Act & Assert: 尝试添加第二个验证节点
    with pytest.raises(ValueError, match="已有验证节点"):
        service.add_validation(
            sync_session,
            requirement_id=requirement.id,
            test_cases=[{"name": "测试2"}]
        )


def test_get_validation(sync_session):
    """测试获取验证节点"""
    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="叶子需求",
        status=RequirementStatus.LEAF.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    validation_result = service.add_validation(
        sync_session,
        requirement_id=requirement.id,
        test_cases=[{"name": "测试"}]
    )

    # Act
    result = service.get_validation(sync_session, validation_result["validation_id"])

    # Assert
    assert result["validation_id"] == validation_result["validation_id"]
    assert result["requirement_id"] == requirement.id
    assert len(result["test_cases"]) == 1


def test_get_validation_by_requirement(sync_session):
    """测试根据需求 ID 获取验证节点"""
    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="叶子需求",
        status=RequirementStatus.LEAF.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    service.add_validation(
        sync_session,
        requirement_id=requirement.id,
        test_cases=[{"name": "测试"}]
    )

    # Act
    result = service.get_validation_by_requirement(sync_session, requirement.id)

    # Assert
    assert result is not None
    assert result["requirement_id"] == requirement.id


def test_get_validation_by_requirement_not_found(sync_session):
    """测试获取不存在的验证节点"""
    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="叶子需求",
        status=RequirementStatus.LEAF.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    # Act
    result = service.get_validation_by_requirement(sync_session, requirement.id)

    # Assert
    assert result is None


def test_update_validation(sync_session):
    """测试更新验证节点"""
    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="叶子需求",
        status=RequirementStatus.LEAF.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    validation_result = service.add_validation(
        sync_session,
        requirement_id=requirement.id,
        test_cases=[{"name": "测试1"}]
    )

    from src.schemas import ValidationUpdate

    # Act
    result = service.update_validation(
        sync_session,
        validation_result["validation_id"],
        ValidationUpdate(
            test_cases=[{"name": "测试2"}, {"name": "测试3"}],
            status=ValidationStatus.PASSED.value
        )
    )

    # Assert
    assert len(result["test_cases"]) == 2
    assert result["status"] == "passed"
    assert result["validated_at"] is not None


def test_delete_validation(sync_session):
    """测试删除验证节点"""
    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="叶子需求",
        status=RequirementStatus.LEAF.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    validation_result = service.add_validation(
        sync_session,
        requirement_id=requirement.id,
        test_cases=[{"name": "测试"}]
    )

    # Act
    result = service.delete_validation(
        sync_session,
        validation_result["validation_id"]
    )

    # Assert
    assert result["deleted"] is True

    # 验证数据库中已删除
    from src.db.models import ValidationNode
    validation = sync_session.query(ValidationNode).filter_by(
        id=validation_result["validation_id"]
    ).first()
    assert validation is None


def test_add_validation_multiple_test_cases(sync_session):
    """测试添加多个测试用例"""
    # Arrange
    service = ValidationService()
    project = Project(name="测试项目")
    sync_session.add(project)
    sync_session.commit()

    requirement = Requirement(
        project_id=project.id,
        content="叶子需求",
        status=RequirementStatus.LEAF.value
    )
    sync_session.add(requirement)
    sync_session.commit()

    test_cases = [
        {
            "name": "测试1",
            "steps": ["步骤1", "步骤2"],
            "expected": "结果1"
        },
        {
            "name": "测试2",
            "steps": ["步骤A", "步骤B"],
            "expected": "结果2"
        },
        {
            "name": "测试3",
            "steps": ["步骤X", "步骤Y"],
            "expected": "结果3"
        }
    ]

    # Act
    result = service.add_validation(
        sync_session,
        requirement_id=requirement.id,
        test_cases=test_cases
    )

    # Assert
    assert len(result["test_cases"]) == 3