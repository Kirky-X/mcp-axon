# ❓ 常见问题 (FAQ)

### MCP-Axon 需求链化系统常见问题

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

### 什么是 MCP-Axon？

**MCP-Axon** 是一个基于 Model Context Protocol (MCP) 的智能需求链化管理系统，专门用于将复杂的需求分解为可执行的链式结构。

**核心功能：**
- 智能需求分解
- 依赖关系管理
- 链式执行构建
- 并行处理支持
- 状态追踪管理
- 快照回滚功能

### 为什么选择 MCP-Axon？

| 特性 | MCP-Axon | 传统管理 |
|-----|---------|---------|
| 智能化程度 | 高 | 低 |
| 依赖管理 | 自动检测 | 手动管理 |
| 易用性 | 简单 | 复杂 |
| 文档完善度 | 全面 | 基础 |

### 使用什么数据库？

MCP-Axon 使用 **real_ladybug** 图数据库客户端,支持:
- Cypher 查询语言
- 图数据存储 (节点和关系)
- 事务管理
- 连接池

默认数据库文件为 `mcp_axon.lbug`,可通过环境变量 `MCP_AXON_DB_PATH` 配置。

### 支持哪些平台？

| 平台 | 架构 | 状态 |
|-----|------|------|
| **Linux** | x86_64, ARM64 | ✅ 支持 |
| **macOS** | x86_64, ARM64 | ✅ 支持 |
| **Windows** | x86_64 | ✅ 支持 |

### 使用什么编程语言？

- **Python**: 3.12+
- **主要依赖**:
  - `mcp>=1.27.0` - MCP 协议
  - `real-ladybug>=0.15.3` - 图数据库客户端
  - `pydantic>=2.11.0` - 数据验证
  - `networkx>=3.6.1` - 图算法
  - `dependency-injector>=4.49.0` - 依赖注入
  - `typer>=0.24.1` - CLI 框架

---

## 安装与配置

### 如何安装 MCP-Axon？

```bash
# 克隆仓库
git clone https://github.com/Kirky-X/axon.git
cd axon

# 使用 uv 安装
uv venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装项目
uv pip install -e .
```

### 系统要求是什么？

| 组件 | 最低要求 | 推荐 |
|-----|---------|------|
| Python | 3.12 | 3.12 |
| 内存 | 512 MB | 2 GB+ |
| 磁盘空间 | 100 MB | 500 MB |
| CPU | 1 核 | 4+ 核 |

### 如何验证安装？

```python
from src.core.sdk import RequirementSDK

sdk = RequirementSDK()
project = sdk.create_project(name="测试", description="验证安装")
print(f"✅ 安装成功: {project['id']}")
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

# 5. 触发链化
axon execution trigger --project <project_id>

# 6. 获取下一个需求
axon execution next --project <project_id>
```

**MCP 方式:**

通过 MCP 客户端调用相应工具，参考 [API 参考](API_REFERENCE.md)。

**HTTP 方式:**

```bash
# 启动 HTTP 服务器
axon-server --mode http --http-port 8080

# 使用 REST API
curl -X POST http://localhost:8080/api/tools/manage_project \
  -H "Content-Type: application/json" \
  -d '{"action": "create", "name": "我的项目", "description": "描述"}'
```

### 支持哪些需求类型？

**需求层级：**
- 根需求（项目顶级需求）
- 子需求（可嵌套分解）
- 叶子节点（可执行需求）

**需求状态：**
- `DRAFT` - 草稿
- `DECOMPOSING` - 分解中
- `LEAF` - 叶子节点
- `VALIDATED` - 已验证
- `CHAINED` - 已链化
- `EXECUTING` - 执行中
- `COMPLETED` - 已完成

### 如何处理错误？

**CLI 方式:**

CLI 命令会直接显示错误信息，根据提示修正即可。

**MCP 方式:**

```json
// 错误响应格式
{
  "success": false,
  "error": "错误描述",
  "error_type": "错误类型"
}
```

**HTTP 方式:**

HTTP API 返回标准 HTTP 状态码和错误信息。

---

## 性能

### 性能指标如何？

| 操作 | 要求 | 实测 |
|-----|------|------|
| CRUD 操作 | < 50ms | 1.06ms ✅ |
| 拓扑排序 (2000 节点) | < 1000ms | 2.82ms ✅ |
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

| 场景 | 内存使用 |
|-----|---------|
| 基本初始化 | ~10 MB |
| 100 个需求 | ~20 MB |
| 1000 个需求 | ~50 MB |
| 2000 个需求 | ~100 MB |

---

## 故障排除

### 常见错误

| 错误 | 原因 | 解决方案 |
|-----|------|---------|
| 锁获取失败 | 已被其他会话占用 | 等待或释放锁 |
| 依赖循环 | 需求间形成循环依赖 | 检查依赖关系 |
| 数据库错误 | 并发访问冲突 | 使用会话 ID 控制 |

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
