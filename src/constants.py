# Copyright (c) 2026 Kirky.X. All rights reserved.
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.

"""系统常量定义"""

import re

# UUID 验证正则（全局共享，避免各模块重复定义）
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class Limits:
    """系统限制常量"""

    # 字符串长度限制
    MAX_PROJECT_NAME_LENGTH = 200
    MAX_REQUIREMENT_CONTENT_LENGTH = 5000
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_TEST_CASE_NAME_LENGTH = 200

    # 需求树限制
    MAX_DEPTH = 10
    MAX_NODES = 10000
    MAX_EDGES = 50000

    # 项目限制
    MAX_CONCURRENT_PROJECTS = 5


class CacheSizes:
    """缓存容量常量"""

    PROJECT_CACHE_SIZE = 50
    REQUIREMENT_CACHE_SIZE = 200
    CHAIN_CACHE_SIZE = 50


class Timeouts:
    """超时常量"""

    LOCK_TIMEOUT_MINUTES = 30
    RATE_LIMIT_WINDOW_SECONDS = 60


class Database:
    """数据库配置常量"""

    DEFAULT_POOL_SIZE = 5
    DEFAULT_MAX_OVERFLOW = 10
    POOL_RECYCLE_SECONDS = 3600


class PerformanceThresholds:
    """性能阈值常量"""

    SLOW_OPERATION_SECONDS = 1.0
    SLOW_DB_QUERY_SECONDS = 0.5
    SLOW_API_CALL_SECONDS = 0.5


class ComplexityScoring:
    """复杂度评分常量"""

    CONTENT_LENGTH_THRESHOLD = 200
    CONTENT_LENGTH_SCORE = 0.3
    KEYWORD_SCORE = 0.15
    ROOT_LEVEL_SCORE = 0.2
    DECOMPOSE_THRESHOLD = 0.5  # 降低阈值，从 0.7 改为 0.5，更容易触发分解


class Chain:
    """链化相关常量"""

    DEFAULT_BATCH_SIZE = 100
    MAX_RETRIES = 3


class APIVersion:
    """API 版本控制常量"""

    CURRENT_VERSION = "1.0.0"
    MIN_SUPPORTED_VERSION = "1.0.0"

    # 版本兼容性
    SUPPORTED_VERSIONS = ["1.0.0"]

    # 版本历史
    VERSION_HISTORY = {
        "1.0.0": "初始版本，支持所有核心功能",
    }


class EventType:
    """事件类型常量"""

    PROJECT_CREATED = "ProjectCreated"
    PROJECT_UPDATED = "ProjectUpdated"
    PROJECT_DELETED = "ProjectDeleted"
    PROJECT_STATUS_CHANGED = "ProjectStatusChanged"
    REQUIREMENT_ADDED = "RequirementAdded"
    REQUIREMENT_UPDATED = "RequirementUpdated"
    REQUIREMENT_DELETED = "RequirementDeleted"
    REQUIREMENT_STATUS_CHANGED = "RequirementStatusChanged"
    VALIDATION_ADDED = "ValidationAdded"
    VALIDATION_UPDATED = "ValidationUpdated"
    CHAINING_TRIGGERED = "ChainingTriggered"
    CHAINING_COMPLETED = "ChainingCompleted"
    SNAPSHOT_CREATED = "SnapshotCreated"
    SNAPSHOT_RESTORED = "SnapshotRestored"
    LOCK_ACQUIRED = "ProjectLockAcquired"
    LOCK_RELEASED = "ProjectLockReleased"
    DEPENDENCY_ADDED = "DependencyAdded"
    DEPENDENCY_REMOVED = "DependencyRemoved"
    REQUIREMENT_COMPLETED = "RequirementCompleted"


class Messages:
    """用户可见的中文消息常量"""

    LOCK_ACQUIRED = "锁获取成功"
    LOCK_IN_USE = "锁已被占用"
    LOCK_RELEASED = "锁释放成功"
    LOCK_NOT_OWNER = "锁不属于该会话"
    PROJECT_LOCKED = "项目已锁定"
    PROJECT_NOT_LOCKED = "项目未锁定"
    SNAPSHOT_CREATED = "快照创建成功"
