# 🏗️ 架构设计

### MCP-Axon 需求链化系统架构设计

---

## 📋 目录

- [概述](#概述)
- [系统架构](#系统架构)
- [组件设计](#组件设计)
- [数据流](#数据流)
- [技术栈](#技术栈)
- [设计决策](#设计决策)
- [性能考虑](#性能考虑)
- [安全架构](#安全架构)
- [扩展性](#扩展性)

---

## 概述

MCP-Axon 采用分层架构设计，基于 Model Context Protocol (MCP) 标准，提供智能需求链化管理功能。

### 设计目标

- **模块化设计**: 清晰的职责分离，便于维护和扩展
- **高性能**: 优化的数据结构和算法，支持大规模需求管理
- **可靠性**: 完善的错误处理和状态管理机制
- **可扩展性**: 支持插件式扩展和自定义组件
- **易用性**: 简洁的 MCP 工具接口，降低使用门槛

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP 客户端                              │
│                   (Claude AI, IDE)                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      MCP 协议层                              │
│                   (mcp Python SDK)                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      API 层                                  │
│                 (src/api/mcp_server.py)                     │
│                 (src/api/tools.py)                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      SDK 层                                  │
│              (src/core/sdk.py - RequirementSDK)             │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  服务层      │ │  服务层      │ │  服务层      │
    │ProjectManager│ │Requirement  │ │Dependency   │
    │              │ │Manager      │ │Service      │
    └─────────────┘ └─────────────┘ └─────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            ▼
    ┌─────────────────────────────────────────────────────┐
    │                    数据层                            │
    │         (src/db/graph_queries.py - Cypher)          │
    │         (src/db/graph_models.py - Pydantic)         │
    │         (real_ladybug - LadybugDB 图数据库)          │
    └─────────────────────────────────────────────────────┘
```

### 分层架构

| 层次           | 职责     | 组件                                         |
| -------------- | -------- | -------------------------------------------- |
| **MCP 协议层** | 通信协议 | MCP Python SDK, JSON-RPC 2.0                 |
| **API 层**     | 请求处理 | MCP 服务器、ToolRouter、输入验证、速率限制             |
| **SDK 层**     | SDK 入口 | RequirementSDK, 服务协调                     |
| **服务层**     | 核心业务 | 各业务服务管理器                             |
| **容器层**     | 依赖注入 | dependency-injector 容器                     |
| **数据层**     | 数据存储 | real_ladybug, Cypher 查询模板, Pydantic 模型 |

---

## 组件设计

### 1. RequirementSDK

系统的主入口类，负责协调各服务管理器。

```python
class RequirementSDK:
    """需求链化 SDK - 主入口"""

    def __init__(self, db_path: str | None = None):
        """
        初始化 SDK

        Args:
            db_path: 数据库文件路径 (默认从环境变量 MCP_AXON_DB_PATH 获取)
        """
        # 优先使用环境变量，其次使用参数，最后使用默认值
        self.db_path = os.getenv("MCP_AXON_DB_PATH", db_path or "mcp_axon.lbug")

        # 初始化容器和数据库
        init_container(db_path=self.db_path)
        init_database()

        # 从容器获取服务
        container = get_container()
        self.project_manager = container.project_manager()
        self.requirement_manager = container.requirement_manager()
        self.dependency_service = container.dependency_service()
        self.validation_service = container.validation_service()
        self.chain_builder = container.chain_builder()
        self.chain_orchestrator = container.chain_orchestrator()
        self.lock_manager = container.lock_manager()
        self.snapshot_manager = container.snapshot_manager()
```

### 2. 项目管理器 (ProjectManager)

负责项目的 CRUD 操作和状态管理。

```python
class ProjectManager:
    """项目管理器"""

    def create_project(self, name: str, description: str) -> Dict[str, Any]:
        """创建项目"""

    def get_project(self, project_id: str) -> Optional[Project]:
        """获取项目"""

    def update_project(self, project_id: str, **kwargs) -> Project:
        """更新项目"""
```

### 3. 需求管理器 (RequirementManager)

负责需求节点的增删改查和复杂度评估。

```python
class RequirementManager:
    """需求管理器"""

    def add_requirement(self, project_id: str, content: str,
                       parent_id: Optional[str] = None) -> Dict[str, Any]:
        """添加需求"""

    def mark_as_leaf(self, requirement_id: str) -> Requirement:
        """标记为叶子节点"""

    def evaluate_complexity(self, content: str, level: int) -> float:
        """评估需求复杂度"""
```

### 4. 依赖服务 (DependencyService)

负责依赖关系的管理和循环检测。

```python
class DependencyService:
    """依赖服务"""

    def add_dependency(self, requirement_id: str, dependency_id: str) -> None:
        """添加依赖"""

    def detect_cycle(self, project_id: str) -> Optional[List[str]]:
        """检测循环依赖"""

    def transfer_dependencies(self, parent_id: str, mapping: Dict[str, List[str]]):
        """依赖传递"""
```

### 5. 链化构建器 (ChainBuilder)

基于拓扑排序构建需求执行链。

```python
class ChainBuilder:
    """链化构建器"""

    def build_chain(self, project_id: str) -> List[Dict[str, Any]]:
        """构建执行链"""

    def topological_sort(self, project_id: str) -> List[str]:
        """拓扑排序 (Kahn 算法)"""

    def identify_parallel_nodes(self, sorted_ids: List[str]) -> List[List[str]]:
        """识别并行节点"""
```

### 6. 链化编排器 (ChainOrchestrator)

协调链化过程，处理并行节点和状态更新。

```python
class ChainOrchestrator:
    """链化编排器"""

    def orchestrate(self, project_id: str) -> Dict[str, Any]:
        """执行链化编排"""

    def resolve_parallel_order(self, project_id: str, sorted_order: List[str]):
        """解决并行顺序"""
```

---

## 数据流

### 请求处理流程

```
1. MCP 客户端发送请求
2. MCP 服务器接收并解析请求
3. 工具路由器定位对应的处理函数
4. SDK 协调相关服务处理请求
5. 服务层执行业务逻辑
6. 数据层持久化数据
7. 返回结果给 MCP 客户端
```

### 链化流程

```
1. 触发链化 (trigger_chaining)
2. 拓扑排序 (topological_sort)
3. 识别并行节点 (identify_parallel_nodes)
4. 构建链表 (build_chain)
5. 更新需求状态
6. 返回执行链
```

---

## 技术栈

### 核心技术

| 类别         | 技术                 | 版本   | 用途             |
| ------------ | -------------------- | ------ | ---------------- |
| **语言**     | Python               | 3.12+  | 主要开发语言     |
| **协议**     | MCP                  | >=1.27.0 | 模型上下文协议   |
| **数据库**   | real_ladybug         | >=0.15.3 | 图数据库客户端     |
| **查询语言** | Cypher               | -      | 图查询语言       |
| **数据验证** | Pydantic             | >=2.11.0 | 数据模型和验证   |
| **依赖注入** | dependency-injector  | >=4.49.0 | 服务生命周期管理 |
| **图算法**   | NetworkX             | >=3.6.1 | 拓扑排序等算法   |
| **状态机**   | transitions          | >=0.9.3 | 状态管理         |
| **缓存**     | cachetools           | >=7.0.5 | 查询缓存         |
| **CLI**      | Typer                | >=0.24.1 | 命令行界面       |
| **测试**     | pytest               | >=9.0.0 | 测试框架         |
| **重试**     | tenacity             | >=9.1.4 | 失败重试机制     |

### 依赖关系

```
RequirementSDK
    ├── ProjectManager (数据库操作)
    ├── RequirementManager (数据库操作)
    ├── DependencyService (数据库操作)
    ├── ValidationService (数据库操作)
    ├── ChainBuilder (图算法 - 拓扑排序)
    ├── ChainOrchestrator (状态管理)
    ├── SnapshotManager (快照管理)
    └── ProjectLockManager (并发控制)
            │
            ▼
    real_ladybug (Neo4j 图数据库客户端)
            │
            ▼
    Neo4j 数据库 (Cypher 查询)
```

---

## 设计决策

### 决策 1: 为什么选择 Neo4j 图数据库？

| 优点         | 说明                                   |
| ------------ | -------------------------------------- |
| 原生图存储   | 需求依赖关系天然适合图模型             |
| Cypher 查询  | 声明式图查询语言，表达力强             |
| 依赖遍历     | 高效的依赖路径查询和循环检测           |
| 关系一等公民 | HAS_CHILD、DEPENDS_ON 等边类型直接建模 |

### 决策 2: 为什么使用 MCP 协议？

- 与 Claude AI 深度集成
- 标准化的工具调用接口
- 支持 AI 驱动的交互式体验

### 决策 3: 为什么使用拓扑排序？

- 自动处理复杂的依赖关系
- 识别并行可执行的需求
- 生成最优的执行顺序

### 决策 4: 为什么使用 dependency-injector？

- 显式依赖声明，易于理解
- 支持 Singleton/Factory 等多种生命周期
- 便于测试时替换 mock
- 与服务容器无缝集成

### 决策 5: 为什么使用 real_ladybug 作为图数据库客户端？

- 轻量级图数据库客户端
- 支持 Cypher 参数化查询，防止注入
- 与项目图模型需求匹配
- 提供连接池和事务管理

### 决策 6: 为什么使用 dependency-injector？

- 显式依赖声明，易于理解
- 支持 Singleton/Factory 等多种生命周期
- 便于测试时替换 mock
- 与服务容器无缝集成
- 统一管理组件依赖关系

### 决策 7: 为什么使用 Typer 构建 CLI？

- 基于 Python 类型提示，自动生成帮助文档
- 简洁的装饰器语法，易于维护
- 支持子命令和参数验证
- 与 FastAPI 同源，生态良好

---

## 性能考虑

### 性能目标

| 操作                 | 目标    | 实测       |
| -------------------- | ------- | ---------- |
| create_project       | < 10ms  | ✅ 1.06ms  |
| add_requirement      | < 30ms  | ✅ 1.06ms  |
| get_next_requirement | < 50ms  | ✅ 1.06ms  |
| 拓扑排序 (2000 节点) | < 500ms | ✅ 2.82ms  |
| 全量链化 (2000 节点) | < 2s    | ✅ 92.58ms |

### 性能优化策略

1. **连接池管理**
   - Neo4j 客户端内置连接池支持

2. **查询优化**
   - 使用 Cypher 参数化查询
   - 批量操作减少数据库访问

3. **算法优化**
   - Kahn 算法 O(V+E) 复杂度
   - 图数据库原生遍历操作

4. **缓存策略**
   - 查询结果缓存
   - 依赖关系缓存

---

## 安全架构

### 安全措施

| 层级           | 措施              | 说明               |
| -------------- | ----------------- | ------------------ |
| **输入验证**   | Pydantic 校验     | 严格的参数类型检查 |
| **注入防护**   | Cypher 参数化查询 | 参数化查询         |
| **并发安全**   | 锁机制            | 项目级锁定         |
| **数据完整性** | 事务管理          | ACID 事务支持      |
| **审计日志**   | 事件记录          | 操作历史追踪       |

### 并发控制

```python
# 获取锁
sdk.acquire_lock(project_id, session_id="session_123")

# 执行操作
sdk.add_requirement(project_id, "新需求")

# 释放锁
sdk.release_lock(project_id, session_id="session_123")
```

---

## 扩展性

### 当前限制

- 单机部署，无法水平扩展
- 项目锁依赖超时机制
- 速率限制配置需要优化

### 未来改进方向

| 方向            | 说明           |
| --------------- | -------------- |
| 分布式部署 | 支持多实例部署 |
| Redis 分布式锁  | 高并发场景     |
| WebSocket 推送  | 实时链化进度   |
| 需求版本历史    | 回溯和审计     |
| 插件机制        | 扩展链化策略   |
| 配置中心        | 动态配置管理   |

### 可扩展点

- 自定义复杂度评估规则
- 自定义验证节点类型
- 自定义事件处理器
- 自定义链化策略

---

**[用户指南](USER_GUIDE.md)** • **[API 参考](API_REFERENCE.md)** • **[FAQ](FAQ.md)**
