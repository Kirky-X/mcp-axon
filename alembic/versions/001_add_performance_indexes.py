# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""add performance indexes

Revision ID: 001_add_performance_indexes
Revises:
Create Date: 2026-01-03 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_add_performance_indexes"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加性能优化索引"""

    # 获取数据库连接
    bind = op.get_bind()

    # 获取现有索引
    inspector = sa.inspect(bind)
    existing_indexes = [idx["name"] for idx in inspector.get_indexes("requirements")]
    existing_indexes.extend([idx["name"] for idx in inspector.get_indexes("events")])
    existing_indexes.extend([idx["name"] for idx in inspector.get_indexes("projects")])

    # 为 requirements 表添加索引（如果不存在）
    if "idx_req_project" not in existing_indexes:
        op.create_index("idx_req_project", "requirements", ["project_id"], unique=False)

    if "idx_req_status" not in existing_indexes:
        op.create_index("idx_req_status", "requirements", ["status"], unique=False)

    # 为 events 表添加索引（如果不存在）
    if "idx_event_project" not in existing_indexes:
        op.create_index("idx_event_project", "events", ["project_id"], unique=False)

    # 为 projects 表添加索引（如果不存在）
    if "idx_project_status" not in existing_indexes:
        op.create_index("idx_project_status", "projects", ["status"], unique=False)

    if "idx_project_locked_by" not in existing_indexes:
        op.create_index(
            "idx_project_locked_by", "projects", ["locked_by"], unique=False
        )

    if "idx_project_created_at" not in existing_indexes:
        op.create_index(
            "idx_project_created_at", "projects", ["created_at"], unique=False
        )

    if "idx_project_updated_at" not in existing_indexes:
        op.create_index(
            "idx_project_updated_at", "projects", ["updated_at"], unique=False
        )


def downgrade() -> None:
    """移除性能优化索引"""
    # 移除 requirements 表的索引
    op.drop_index("idx_req_project", table_name="requirements")
    op.drop_index("idx_req_status", table_name="requirements")

    # 移除 events 表的索引
    op.drop_index("idx_event_project", table_name="events")

    # 移除 projects 表的索引
    op.drop_index("idx_project_status", table_name="projects")
    op.drop_index("idx_project_locked_by", table_name="projects")
    op.drop_index("idx_project_created_at", table_name="projects")
    op.drop_index("idx_project_updated_at", table_name="projects")
