# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""数据模型单元测试"""

import pytest
from datetime import datetime
from sqlalchemy import select

from src.db.models import (
    Project, Requirement, ValidationNode, ChainState, Event,
    ProjectStatus, RequirementStatus, ValidationStatus, ChainStatus
)


@pytest.mark.asyncio
async def test_create_project(async_session):
    """测试创建项目"""

    project = Project(
        name="测试项目",
        description="这是一个测试项目"
    )

    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    assert project.id is not None
    assert project.status == ProjectStatus.CREATED.value
    assert project.locked_by is None
    assert project.created_at is not None


@pytest.mark.asyncio
async def test_requirement_hierarchy(async_session):
    """测试需求层级关系"""
    # 创建项目
    project = Project(name="测试项目")
    async_session.add(project)
    await async_session.commit()

    # 创建父需求
    parent = Requirement(
        project_id=project.id,
        content="父需求",
        level=0
    )

    async_session.add(parent)
    await async_session.flush()  # Flush to get parent ID

    # 创建子需求
    child = Requirement(
        project_id=project.id,
        parent_id=parent.id,
        content="子需求",
        level=1
    )

    async_session.add(child)
    await async_session.commit()

    # 验证关系
    await async_session.refresh(child)
    assert child.parent_id == parent.id
    assert child.level == 1


@pytest.mark.asyncio
async def test_requirement_dependencies(async_session):
    """测试依赖关系存储"""
    # 创建项目
    project = Project(name="测试项目")
    async_session.add(project)
    await async_session.commit()

    # 创建需求
    req1 = Requirement(project_id=project.id, content="需求1")
    req2 = Requirement(project_id=project.id, content="需求2")
    req3 = Requirement(
        project_id=project.id,
        content="需求3",
        dependencies=[]
    )

    async_session.add_all([req1, req2, req3])
    await async_session.flush()  # Flush to get IDs

    # Now set dependencies
    req3.dependencies = [req1.id, req2.id]
    await async_session.commit()

    # 验证依赖关系
    assert len(req3.dependencies) == 2
    assert req1.id in req3.dependencies
    assert req2.id in req3.dependencies


@pytest.mark.asyncio
async def test_validation_node_uniqueness(async_session):
    """测试验证节点唯一性"""
    # 创建项目和需求
    project = Project(name="测试项目")
    async_session.add(project)
    await async_session.commit()

    requirement = Requirement(project_id=project.id, content="叶子需求")
    async_session.add(requirement)
    await async_session.commit()

    # 创建第一个验证节点
    validation1 = ValidationNode(requirement_id=requirement.id)
    async_session.add(validation1)
    await async_session.commit()

    # 尝试创建第二个验证节点（应该失败）
    validation2 = ValidationNode(requirement_id=requirement.id)
    async_session.add(validation2)
    
    with pytest.raises(Exception):  # 应该抛出唯一性约束异常
        await async_session.commit()


@pytest.mark.asyncio
async def test_chain_state_cascade_delete(async_session):
    """测试链状态级联删除"""
    # 创建项目和链状态
    project = Project(name="测试项目")
    async_session.add(project)
    await async_session.flush()  # Flush to get project ID

    chain_state = ChainState(project_id=project.id)
    async_session.add(chain_state)
    await async_session.commit()

    # 删除项目
    await async_session.delete(project)
    await async_session.commit()

    # 验证链状态也被删除
    result = await async_session.execute(
        select(ChainState).where(ChainState.project_id == project.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_requirement_content_validation(async_session):
    """测试需求内容验证"""
    # 创建项目
    project = Project(name="测试项目")
    async_session.add(project)
    await async_session.commit()

    # 尝试创建空内容的需求
    with pytest.raises(ValueError, match="需求内容不能为空"):
        req = Requirement(project_id=project.id, content="")
        async_session.add(req)
        await async_session.flush()

    # 尝试创建只有空格的需求
    with pytest.raises(ValueError, match="需求内容不能为空"):
        req = Requirement(project_id=project.id, content="   ")
        async_session.add(req)
        await async_session.flush()


@pytest.mark.asyncio
async def test_event_sequence(async_session):
    """测试事件序列号"""
    # 创建项目
    project = Project(name="测试项目")
    async_session.add(project)
    await async_session.commit()

    # 创建多个事件
    for i in range(5):
        event = Event(
            project_id=project.id,
            event_type=f"Event{i}",
            aggregate_id=f"Aggregate{i}",
            payload={"data": f"value{i}"},
            sequence=i
        )
        async_session.add(event)

    await async_session.commit()

    # 验证事件数量
    result = await async_session.execute(
        select(Event).where(Event.project_id == project.id)
    )
    events = result.scalars().all()
    assert len(events) == 5