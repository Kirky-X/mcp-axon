# ❓ 常见问题 (FAQ)

### Axon 需求链化系统常见问题

---

## 📋 目录

- [一般问题](#一般问题)
- [安装与配置](#安装与配置)
- [使用与功能](#使用与功能)
- [性能](#性能)
- [故障排除](#故障排除)
- [贡献](#贡献)
- [许可证](#许可证)

---

## 一般问题

### 什么是 Axon？

**Axon** 是一个基于 Model Context Protocol (MCP) 的智能需求链化管理系统，专门用于将复杂的需求分解为可执行的链式结构。

**核心功能：**

- 智能需求分解
- 依赖关系管理
- 链式执行构建
- 并行处理支持
- 状态追踪管理
- 快照回滚功能

### 为什么选择 Axon？

| 特性       | Axon     | 传统管理 |
| ---------- | -------- | -------- |
| 智能化程度 | 高       | 低       |
| 依赖管理   | 自动检测 | 手动管理 |
| 易用性     | 简单     | 复杂     |
| 文档完善度 | 全面     | 基础     |

### 使用什么数据库？

Axon 使用 **real-ladybug** 图数据库客户端，底层存储为本地文件数据库：

- 基于图数据模型（节点和关系）
- 支持事务管理
- 连接池管理

**数据库文件路径：**

| 组件 | 默认数据库文件 | 配置文件位置 |
|------|---------------|-------------|
| SDK | `mcp_axon.lbug` | `src/core/sdk.py:35` |
| CLI | `requirements.db` | `src/cli/cli.py:30` |
| Server | `requirements.db` | `src/api/mcp_server.py:36` |

可通过环境变量 `MCP_AXON_DB_PATH` 统一覆盖默认路径：

```bash
export MCP_AXON_DB_PATH="/path/to/your/database.lbug"
```

### 支持哪些平台？

| 平台        | 架构          | 状态    |
| ----------- | ------------- | ------- |
| **Linux**   | x86_64, ARM64 | ✅ 支持 |
| **macOS**   | x86_64, ARM64 | ✅ 支持 |
| **Windows** | x86_64        | ✅ 支持 |

### 使用什么编程语言？

- **Python**: 3.12+
- **主要依赖**（见 `pyproject.toml`）:
  - `mcp>=1.27.0,<2.0.0` - MCP 协议
  - `real-ladybug>=0.15.3` - 图数据库客户端
  - `pydantic>=2.11.0,<3.0.0` - 数据验证
  - `networkx>=3.6.1,<4.0.0` - 图算法
  - `dependency-injector>=4.49.0` - 依赖注入
  - `typer>=0.24.1` - CLI 框架
  - `transitions>=0.9.3` - 状态机
  - `cachetools>=7.0.5` - 缓存管理
  - `tenacity>=9.1.4,<10.0.0` - 重试机制

---

## 安装与配置

### 如何安装 Axon？

```bash
# 克隆仓库
git clone https://github.com/Kirky-X/axon.git
cd axon

# 使用 uv 安装
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装依赖（开发模式含 dev 依赖）
uv pip install -e ".[dev]"

# 或仅安装生产依赖
uv pip install -e .
```

### 系统要求是什么？

| 组件     | 最低要求 | 推荐   |
| -------- | -------- | ------ |
| Python   | 3.12     | 3.12   |
| 内存     | 512 MB   | 2 GB+  |
| 磁盘空间 | 100 MB   | 500 MB |
| CPU      | 1 核     | 4+ 核  |

### 如何验证安装？

```python
from src.core.sdk import RequirementSDK

sdk = RequirementSDK()
project = sdk.manage_project(name="测试", description="验证安装")
print(f"✅ 安装成功: {project['project_id']}")
```

---

## 使用与功能

### 如何开始使用？

**CLI 方式:**

```bash
# 1. 创建项目
axon project create --name "我的项目" --desc "描述"

# 2. 添加需求
axon requirement create --project <project_id> --content "用户认证功能"

# 3. 标记为叶子节点
axon requirement mark-leaf <requirement_id>

# 4. 添加验证
axon validation add <requirement_id> --tests '[{"name": "测试", "steps": ["步骤"], "expected_result": "结果"}]'

# 5. 获取下一个待执行需求
axon execution next --project <project_id>

# 6. 标记需求完成
axon execution complete <requirement_id> --project <project_id>

# 7. 查看执行状态
axon execution state --project <project_id>
```

**可用的 CLI 命令：**

- `axon project` - 项目管理（create/get/update）
- `axon requirement` - 需求管理（create/get/list/update/delete/mark-leaf）
- `axon dependency` - 依赖管理（add/transfer）
- `axon validation` - 验证管理（add/run）
- `axon execution` - 执行管理（next/complete/state）
- `axon snapshot` - 快照管理（create/restore/list）
- `axon lock` - 锁管理（acquire/release/check）
- `axon version` - 版本查询

**HTTP 方式:**

```bash
# 启动 HTTP 服务器
axon-server --mode http --http-port 8080

# 查看可用端点
curl http://localhost:8080/

# 健康检查
curl http://localhost:8080/health

# 查看性能指标
curl http://localhost:8080/metrics

# API 版本信息
curl http://localhost:8080/api_version
```

### 支持哪些需求类型？

**需求层级：**

- 根需求（项目顶级需求）
- 子需求（可嵌套分解）
- 叶子节点（可执行需求）

**需求状态：**

- `DRAFT` - 草稿
- `DECOMPOSING` - 分解中
- `LEAF` - 叶子节点（可执行需求）
- `VALIDATED` - 已验证
- `CHAINED` - 已链化
- `COMPLETED` - 已完成

**状态转换规则：**

```
DRAFT → DECOMPOSING → LEAF → VALIDATED → CHAINED → COMPLETED
  ↓         ↓           ↓          ↓
  └─────────┴───────────┴──────────┘
         （允许回退重新处理）
```

### 如何处理错误？

**CLI 方式:**

CLI 命令会直接显示错误信息，根据提示修正即可。

**MCP 方式:**

```json
// 成功响应
{
  "success": true,
  "data": { /* 操作结果 */ },
  "timestamp": "2024-01-01T00:00:00",
  "next_action": "manage_requirement"
}

// 错误响应
{
  "success": false,
  "error": "错误描述",
  "error_type": "ValidationError" // 或具体异常类型
}

// 限流响应
{
  "success": false,
  "error": "请求过于频繁，请稍后再试。当前限制: 100 次/60秒，剩余次数: 0",
  "error_type": "RateLimitExceeded"
}
```

**HTTP 方式:**

HTTP API 返回标准 HTTP 状态码和 JSON 响应：

- `200` - 成功
- `404` - 端点不存在
- `503` - 服务不健康

---

## 性能

### 性能指标如何？

| 操作                 | 要求     | 实测       |
| -------------------- | -------- | ---------- |
| CRUD 操作            | < 50ms   | 1.06ms ✅  |
| 拓扑排序 (2000 节点) | < 1000ms | 2.82ms ✅  |
| 全量链化 (2000 节点) | < 2000ms | 92.58ms ✅ |

### 如何优化性能？

1. **使用批量操作**

   ```bash
   # CLI 批量添加需求
   for content in "需求1" "需求2" "需求3"; do
       axon requirement create --project <project_id> --content "$content"
   done
   ```

2. **合理使用缓存**
   - 系统自动缓存查询结果
   - 无需手动配置

3. **及时释放锁**
   ```bash
   axon lock acquire --project <project_id> --session <session_id>
   try
       # 操作
   finally
       axon lock release --project <project_id> --session <session_id>
   ```

### 内存使用情况如何？

| 场景        | 内存使用 |
| ----------- | -------- |
| 基本初始化  | ~10 MB   |
| 100 个需求  | ~20 MB   |
| 1000 个需求 | ~50 MB   |
| 2000 个需求 | ~100 MB  |

---

## 故障排除

### 常见错误

| 错误       | 原因               | 解决方案         |
| ---------- | ------------------ | ---------------- |
| 锁获取失败 | 已被其他会话占用   | 等待或释放锁     |
| 依赖循环   | 需求间形成循环依赖 | 检查依赖关系     |
| 数据库错误 | 并发访问冲突       | 使用会话 ID 控制 |

### 获取帮助

- 查看 [用户指南](USER_GUIDE.md)
- 查看 [API 参考](API_REFERENCE.md)
- [创建 Issue](https://github.com/Kirky-X/axon/issues)

---

## 贡献

### 如何贡献？

1. Fork 本仓库
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

### 贡献什么？

- 修复 bug
- 添加新功能
- 改进文档
- 编写测试

### 贡献指南

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 许可证

### 使用什么许可证？

MIT 许可证

### 可以用于商业项目吗？

是的，MIT 许可证允许商业使用。

---

**[用户指南](USER_GUIDE.md)** • **[API 参考](API_REFERENCE.md)** • **[架构设计](ARCHITECTURE.md)**
