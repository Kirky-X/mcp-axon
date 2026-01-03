# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""SQLAlchemy 数据模型定义"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)


class Base(DeclarativeBase):
    """SQLAlchemy 基类"""

    pass


class ProjectStatus(PyEnum):
    """项目状态枚举"""

    CREATED = "CREATED"
    DECOMPOSING = "DECOMPOSING"
    CHAINING = "CHAINING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"


class RequirementStatus(PyEnum):
    """需求状态枚举"""

    DRAFT = "DRAFT"
    DECOMPOSING = "DECOMPOSING"
    LEAF = "LEAF"
    CHAINED = "CHAINED"
    VALIDATED = "VALIDATED"


class ValidationStatus(PyEnum):
    """验证状态枚举"""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class ChainStatus(PyEnum):
    """链化状态枚举"""

    IDLE = "IDLE"
    BUILDING = "BUILDING"
    COMPLETED = "COMPLETED"


class Project(Base):
    """项目实体"""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProjectStatus.CREATED.value
    )
    locked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # 关系
    requirements: Mapped[List["Requirement"]] = relationship(
        "Requirement", back_populates="project", cascade="all, delete-orphan"
    )
    chain_state: Mapped[Optional["ChainState"]] = relationship(
        "ChainState",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="project", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_project_status", "status"),
        Index("idx_project_locked_by", "locked_by"),
    )


class Requirement(Base):
    """需求节点实体"""

    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=True
    )
    content: Mapped[str] = mapped_column(String(5000), nullable=False)
    decompose_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RequirementStatus.DRAFT.value
    )
    level: Mapped[int] = mapped_column(Integer, default=0)
    order_in_parent: Mapped[int] = mapped_column(Integer, default=0)
    dependencies: Mapped[List[str]] = mapped_column(JSON, default=list)
    chain_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    next_requirement_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    # 关系
    project: Mapped["Project"] = relationship("Project", back_populates="requirements")
    parent: Mapped[Optional["Requirement"]] = relationship(
        "Requirement", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Requirement"]] = relationship(
        "Requirement", back_populates="parent", cascade="all, delete-orphan"
    )
    validation: Mapped[Optional["ValidationNode"]] = relationship(
        "ValidationNode",
        back_populates="requirement",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # 索引
    __table_args__ = (
        Index("idx_req_project_status", "project_id", "status"),
        Index("idx_req_parent", "parent_id"),
        Index("idx_req_chain_order", "project_id", "chain_order"),
    )

    @validates("content")
    def validate_content(self, key: str, value: str) -> str:
        """验证需求内容"""
        if not value or not value.strip():
            raise ValueError("需求内容不能为空")
        return value.strip()


class ValidationNode(Base):
    """验证节点实体"""

    __tablename__ = "validation_nodes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    requirement_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    test_cases: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    acceptance_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=ValidationStatus.PENDING.value
    )
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # 关系
    requirement: Mapped["Requirement"] = relationship(
        "Requirement", back_populates="validation"
    )

    # 索引
    __table_args__ = (Index("idx_validation_status", "status"),)


class ChainState(Base):
    """链化状态实体"""

    __tablename__ = "chain_states"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ChainStatus.IDLE.value
    )
    chain_head_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    current_node_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    total_nodes: Mapped[int] = mapped_column(Integer, default=0)
    completed_nodes: Mapped[int] = mapped_column(Integer, default=0)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    last_chained_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    chain_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # 关系
    project: Mapped["Project"] = relationship("Project", back_populates="chain_state")


class Event(Base):
    """事件记录实体"""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    event_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # 关系
    project: Mapped["Project"] = relationship("Project", back_populates="events")

    # 索引
    __table_args__ = (
        Index("idx_event_project_seq", "project_id", "sequence"),
        Index("idx_event_type", "event_type"),
    )
