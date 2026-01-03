# Prompt管理系统 - 产品需求文档 (PRD)

仓库地址：https://gitee.com/kirky-x/prompts

## 1. 产品概述

### 1.1 产品定位
基于SQLite的企业级Prompt版本管理系统，提供完整的CRUD接口、语义搜索、版本控制和多客户端适配能力。支持MCP服务器、HTTP服务器和Python接口三种部署模式。

### 1.2 核心价值
- **版本化管理**：完整的Prompt版本控制，支持历史追溯和多版本并存
- **语义检索**：基于向量的语义搜索能力，快速定位相关Prompt
- **智能客户端适配**：自动识别并适配不同LLM客户端（OpenAI、Anthropic、Claude等）的特殊要求，包括默认原则动态加载与合并机制
- **动态组装**：支持占位符替换和原则动态注入，实现Prompt的灵活组合
- **标准化输出**：兼容OpenAI标准格式，降低集成成本
- **原则继承**：支持客户端默认原则与手动引用原则的智能化合并，确保手动优先级

### 1.3 技术栈
- **数据库**：SQLite + sqlite-vec（本地）/ Supabase PostgreSQL + pgvector（云端）
- **框架**：LangChain（PromptTemplate + ChatOpenAI）
- **缓存**：moka-py（进程内缓存，TTL=1h）
- **并发控制**：进程内队列 + 乐观锁（预留Redis队列扩展接口）

---

## 2. 核心功能清单

### 2.1 CRUD操作

#### 2.1.1 Create（创建） ✅ 已实现
**功能描述**：创建新的Prompt或为现有Prompt创建新版本

**输入参数**：
```json
{
  "name": "code_review_prompt",
  "description": "用于代码审查的AI助手prompt",
  "version_type": "major|minor",  // major: 1.0->2.0, minor: 1.0->1.1
  "tags": ["code", "review", "python"],
  "roles": [
    {
      "role_type": "system",
      "content": "You are a senior code reviewer...",
      "order": 1,
      "template_variables": {
        "language": {"required": true, "default": null},
        "style_guide": {"required": false, "default": "PEP8"}
      }
    },
    {
      "role_type": "user",
      "content": "Please review this {language} code...",
      "order": 2
    }
  ],
  "llm_config": {
    "model": "gpt-4",
    "temperature": 0.3,
    "max_tokens": 2000,
    "top_p": 0.9
  },
  "client_type": "openai",  // 可选，智能客户端适配标识，支持openai、anthropic、claude等
  "principle_refs": [  // 可选，手动引用特定原则（优先级高于客户端默认原则）
    {"principle_id": "oop_principle", "version": "latest"},
    {"principle_id": "clean_code", "version": "1.2"}
  ],
  "change_log": "Initial version with basic review template"
}
```

**处理逻辑**：
1. **版本管理**：检查`name`是否存在：
   - 不存在：创建新Prompt（版本1.0）
   - 存在：根据`version_type`计算新版本号（major: 1.0→2.0, minor: 1.0→1.1）
2. **向量化处理**：自动向量化`description`字段，支持语义搜索
3. **智能客户端适配**：如果指定`client_type`，执行以下智能适配流程：
   - **客户端识别**：自动识别并创建客户端实体（如不存在）
   - **原则合并**：动态加载该客户端的默认原则配置
   - **优先级处理**：与手动引用的原则进行智能合并，确保手动引用优先级高于默认配置
   - **去重机制**：自动过滤重复原则，避免冲突
4. **事务性操作**：原子性写入所有关联表（prompts、versions、roles、principles、clients等）
5. **缓存管理**：清除相关缓存，确保数据一致性
6. **版本标记**：自动更新最新版本标记，维护版本链完整性

**返回结果**：
```json
{
  "prompt_id": "uuid-123",
  "version_id": "uuid-456",
  "version": "1.0",
  "created_at": "2025-01-20T10:30:00Z"
}
```

#### 2.1.2 Search（搜索） ✅ 已实现
**功能描述**：基于语义和标签的混合搜索

**输入参数**：
```json
{
  "query": "代码审查相关的prompt",  // 可选，用于向量语义搜索
  "tags": ["code", "review"],      // 可选，用于全文索引精确匹配
  "logic": "AND|OR",                // 默认AND
  "version_filter": "latest|all|specific",  // 默认latest
  "specific_version": "1.2",        // 当version_filter=specific时必填
  "limit": 10,
  "offset": 0
}
```

**搜索逻辑**：
1. **向量搜索**（如果提供`query`）：
   - 将query向量化
   - 在`prompt_versions`的description向量字段上执行KNN搜索
   - 返回Top-K相似结果

2. **标签过滤**（如果提供`tags`）：
   - 通过`prompt_tags`关联表进行精确匹配

3. **逻辑组合**：
   - `AND`：向量搜索结果 ∩ 标签匹配结果
   - `OR`：向量搜索结果 ∪ 标签匹配结果

4. **版本过滤**：
   - `latest`：只返回`is_latest=true`的版本
   - `all`：返回所有`is_active=true`的版本
   - `specific`：返回指定版本号

5. **排序**：相似度优先，创建时间次之

**返回结果**：
```json
{
  "total": 25,
  "results": [
    {
      "prompt_id": "uuid-123",
      "name": "code_review_prompt",
      "version": "1.2",
      "description": "用于代码审查的AI助手prompt",
      "tags": ["code", "review"],
      "similarity_score": 0.92,
      "created_at": "2025-01-20T10:30:00Z"
    }
  ]
}
```

#### 2.1.3 Get（获取） ✅ 已实现
**功能描述**：获取指定Prompt的完整内容

**输入参数**：
```json
{
  "name": "code_review_prompt",
  "version": "1.2",  // 可选，默认latest
  "output_format": "openai|formatted|both",  // 默认openai
  "template_vars": {  // 可选，用于占位符替换
    "language": "Python",
    "style_guide": "Google Style"
  },
  "runtime_params": {  // 可选，覆盖存储的配置
    "temperature": 0.5,
    "stream": true
  }
}
```

**处理逻辑**：
1. 从缓存中查找：`prompt:{name}:v{version}` 或 `prompt:{name}:latest`
2. 缓存未命中时从数据库加载：
   - 读取`prompt_versions`基础信息
   - 关联查询`prompt_roles`（按order排序）
   - 关联查询`llm_configs`
   - 动态加载引用的原则Prompt
   - 如果指定了client_type，加载客户端默认原则
3. 占位符替换：
   - 遍历所有role的content
   - 使用Jinja2引擎替换`{variable}`
   - 验证必需参数是否提供
4. 组装输出格式
5. 写入缓存（TTL=1h）

**返回结果（openai格式）**：
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "system",
      "content": "You are a senior code reviewer..."
    },
    {
      "role": "system",
      "content": "[原则] 遵循面向接口编程原则..."
    },
    {
      "role": "user",
      "content": "Please review this Python code..."
    }
  ],
  "temperature": 0.5,
  "max_tokens": 2000,
  "top_p": 0.9,
  "stream": true
}
```

**返回结果（formatted格式）**：
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ]
}
```

**返回结果（both格式）**：
```json
{
  "openai_format": { /* 完整请求体 */ },
  "formatted": { /* 消息数组 */ }
}
```

#### 2.1.4 Update（更新） ✅ 已实现
**功能描述**：更新Prompt（实际为创建新版本）

**输入参数**：与Create相同，但必须提供`name`和当前`version_number`（乐观锁）

**处理逻辑**：
1. 乐观锁检查：验证`version_number`是否匹配
2. 冲突处理：如果检查失败，将请求加入队列等待重试
3. 队列处理：FIFO顺序执行，自动递增minor版本号
4. 创建新版本记录（`is_active=true`）
5. 如果需要，更新`is_latest`标识（将旧版本的latest设为false）
6. 清除受影响版本的缓存

**返回结果**：同Create

#### 2.1.5 Delete（删除） ✅ 已实现
**功能描述**：软删除，将版本标记为inactive

**输入参数**：
```json
{
  "name": "code_review_prompt",
  "version": "1.2"  // 可选，默认删除所有版本
}
```

**处理逻辑**：
1. 将指定版本的`is_active`设为false
2. 不允许删除历史版本（只能设为inactive）
3. 清除缓存

**约束**：
- 不支持物理删除
- 必须至少保留一个active版本

#### 2.1.6 Activate（激活） ✅ 已实现
**功能描述**：将inactive版本重新激活

**输入参数**：
```json
{
  "name": "code_review_prompt",
  "version": "1.1",
  "set_as_latest": true  // 可选，是否同时设为latest
}
```

**处理逻辑**：
1. 将`is_active`设为true
2. 如果`set_as_latest=true`，更新latest标识
3. 清除缓存

---

## 3. 数据模型设计

### 3.1 核心实体关系

```
prompts (1) ──────< (N) prompt_versions
                            │
                            ├──< (N) prompt_roles
                            │
                            ├──< (1) llm_configs
                            │
                            ├──< (N) prompt_tags ──< (N) tags
                            │
                            ├──< (N) version_principle_refs ──< (1) principle_prompts
                            │
                            └──< (N) version_client_mapping ──< (1) llm_clients
```

### 3.2 字段说明

#### prompts（Prompt主表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(200) | 全局唯一标识，用于引用 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 最后更新时间 |

**索引**：
- UNIQUE(name)

#### prompt_versions（版本表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| prompt_id | UUID | 外键 -> prompts.id |
| version | VARCHAR(10) | 版本号（x.x格式） |
| version_number | INTEGER | 乐观锁版本号，自动递增 |
| description | TEXT | 语义描述 |
| description_vector | BLOB | description的向量表示（sqlite-vec） |
| is_active | BOOLEAN | 是否激活 |
| is_latest | BOOLEAN | 是否最新版本 |
| change_log | TEXT | 变更记录 |
| created_at | TIMESTAMP | 创建时间 |

**索引**：
- UNIQUE(prompt_id, version)
- INDEX(is_active, is_latest)
- VECTOR INDEX(description_vector) -- sqlite-vec

#### prompt_roles（角色内容表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| version_id | UUID | 外键 -> prompt_versions.id |
| role_type | ENUM | system/user/assistant/principle |
| content | TEXT | Prompt内容（支持Jinja2占位符） |
| order | INTEGER | 执行顺序 |
| template_variables | JSON | 模板变量定义 |

**template_variables格式**：
```json
{
  "variable_name": {
    "required": true,
    "default": null,
    "description": "变量说明"
  }
}
```

**索引**：
- INDEX(version_id, order)

#### llm_configs（LLM配置表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| version_id | UUID | 外键 -> prompt_versions.id（UNIQUE） |
| model | VARCHAR(100) | 模型名称 |
| temperature | FLOAT | 温度参数 |
| max_tokens | INTEGER | 最大token数 |
| top_p | FLOAT | top_p采样 |
| top_k | INTEGER | top_k采样 |
| frequency_penalty | FLOAT | 频率惩罚 |
| presence_penalty | FLOAT | 存在惩罚 |
| stop_sequences | JSON | 停止序列数组 |
| other_params | JSON | 扩展参数 |

**索引**：
- UNIQUE(version_id)

#### tags（标签表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(50) | 标签名（全局唯一） |

**索引**：
- UNIQUE(name)
- FULLTEXT INDEX(name) -- 全文索引

#### prompt_tags（Prompt-标签关联表）
| 字段 | 类型 | 说明 |
|------|------|------|
| version_id | UUID | 外键 -> prompt_versions.id |
| tag_id | UUID | 外键 -> tags.id |

**索引**：
- PRIMARY KEY(version_id, tag_id)

#### principle_prompts（原则Prompt表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(200) | 原则名称（全局唯一） |
| version | VARCHAR(10) | 版本号 |
| content | TEXT | 原则内容 |
| is_active | BOOLEAN | 是否激活 |
| is_latest | BOOLEAN | 是否最新版本 |
| created_at | TIMESTAMP | 创建时间 |

**索引**：
- UNIQUE(name, version)
- INDEX(is_active, is_latest)

#### version_principle_refs（版本-原则引用表）
| 字段 | 类型 | 说明 |
|------|------|------|
| version_id | UUID | 外键 -> prompt_versions.id |
| principle_id | UUID | 外键 -> principle_prompts.id |
| ref_version | VARCHAR(10) | 引用的原则版本（"latest"或具体版本号） |
| order | INTEGER | 原则插入顺序 |

**索引**：
- INDEX(version_id, order)

#### llm_clients（LLM客户端表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(50) | 客户端名称（openai/anthropic/...） |
| default_principles | JSON | 默认原则ID数组 |

**default_principles格式**：
```json
[
  {"principle_name": "api_design", "version": "latest"},
  {"principle_name": "error_handling", "version": "1.0"}
]
```

**索引**：
- UNIQUE(name)

#### version_client_mapping（版本-客户端关联表）
| 字段 | 类型 | 说明 |
|------|------|------|
| version_id | UUID | 外键 -> prompt_versions.id |
| client_id | UUID | 外键 -> llm_clients.id |

**索引**：
- INDEX(version_id)

---

## 4. 接口规范

### 4.1 Python核心接口

```python
class PromptManager:
    """Prompt管理核心类"""
    
    def create(
        self,
        name: str,
        description: str,
        roles: List[RoleConfig],
        version_type: Literal["major", "minor"] = "minor",
        tags: Optional[List[str]] = None,
        llm_config: Optional[LLMConfig] = None,
        client_type: Optional[str] = None,
        principle_refs: Optional[List[PrincipleRef]] = None,
        change_log: Optional[str] = None
    ) -> PromptVersion:
        """创建或更新Prompt"""
        pass
    
    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        logic: Literal["AND", "OR"] = "AND",
        version_filter: Literal["latest", "all", "specific"] = "latest",
        specific_version: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> SearchResult:
        """搜索Prompt"""
        pass
    
    def get(
        self,
        name: str,
        version: Optional[str] = None,
        output_format: Literal["openai", "formatted", "both"] = "openai",
        template_vars: Optional[Dict[str, Any]] = None,
        runtime_params: Optional[Dict[str, Any]] = None
    ) -> Union[OpenAIRequest, FormattedPrompt, BothFormats]:
        """获取Prompt完整内容"""
        pass
    
    def update(
        self,
        name: str,
        version_number: int,  # 乐观锁
        **kwargs  # 同create参数
    ) -> PromptVersion:
        """更新Prompt（创建新版本）"""
        pass
    
    def delete(
        self,
        name: str,
        version: Optional[str] = None
    ) -> bool:
        """软删除Prompt"""
        pass
    
    def activate(
        self,
        name: str,
        version: str,
        set_as_latest: bool = False
    ) -> bool:
        """激活版本"""
        pass
```

### 4.2 数据类定义

```python
@dataclass
class RoleConfig:
    role_type: Literal["system", "user", "assistant", "principle"]
    content: str
    order: int
    template_variables: Optional[Dict[str, VariableConfig]] = None

@dataclass
class VariableConfig:
    required: bool
    default: Any
    description: Optional[str] = None

@dataclass
class LLMConfig:
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    top_k: Optional[int] = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    other_params: Optional[Dict[str, Any]] = None

@dataclass
class PrincipleRef:
    principle_name: str
    version: str = "latest"  # "latest" 或具体版本号

@dataclass
class OpenAIRequest:
    model: str
    messages: List[Dict[str, str]]
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    stop: Optional[List[str]]
    stream: bool = False
    user: Optional[str] = None

@dataclass
class FormattedPrompt:
    messages: List[Dict[str, str]]
```

---

## 5. 使用场景与示例

### 5.1 场景1：创建代码审查Prompt

```python
manager = PromptManager(db_path="prompts.db")

# 创建初始版本
version = manager.create(
    name="code_review",
    description="Python代码审查助手，支持多种编码规范",
    roles=[
        RoleConfig(
            role_type="system",
            content="You are a senior Python developer...",
            order=1
        ),
        RoleConfig(
            role_type="user",
            content="Review this code following {style_guide}:\n\n{code}",
            order=2,
            template_variables={
                "style_guide": VariableConfig(required=False, default="PEP8"),
                "code": VariableConfig(required=True, default=None)
            }
        )
    ],
    tags=["code", "review", "python"],
    llm_config=LLMConfig(temperature=0.3, max_tokens=2000),
    client_type="openai",  # 自动关联OpenAI的默认原则
    change_log="Initial version"
)

print(f"Created version {version.version}")
```

### 5.2 场景2：搜索相关Prompt

```python
# 语义搜索
results = manager.search(
    query="代码质量检查",
    tags=["code"],
    logic="AND",
    version_filter="latest",
    limit=5
)

for result in results.items:
    print(f"{result.name} v{result.version}: {result.description}")
```

### 5.3 场景3：获取并使用Prompt

```python
# 获取OpenAI格式
openai_request = manager.get(
    name="code_review",
    version="1.0",
    output_format="openai",
    template_vars={
        "code": "def hello():\n    print('world')",
        "style_guide": "Google Style"
    },
    runtime_params={
        "temperature": 0.5,
        "stream": True
    }
)

# 直接调用OpenAI API
import openai
response = openai.ChatCompletion.create(**openai_request.__dict__)
```

### 5.4 场景4：创建新版本

```python
# 重大更新（major版本）
new_version = manager.create(
    name="code_review",
    version_type="major",  # 1.0 -> 2.0
    description="增加了安全审查能力",
    roles=[
        # 新的role配置
    ],
    change_log="Added security review capabilities"
)
```

### 5.5 场景5：管理原则Prompt

```python
# 创建原则Prompt
principle_manager = PrincipleManager(db_path="prompts.db")
principle_manager.create(
    name="clean_code",
    content="遵循Clean Code原则：\n1. 函数单一职责\n2. 有意义的命名...",
    version="1.0"
)

# 在Prompt中引用原则
manager.create(
    name="code_review",
    principle_refs=[
        PrincipleRef(principle_name="clean_code", version="latest")
    ],
    # ...其他参数
)
```

---

## 6. 产品限制与约束

### 6.1 功能限制
1. **无用户管理**：所有Prompt对全局可见，无权限控制
2. **无协作功能**：不支持多人协同编辑、评论、审批流程
3. **历史版本只读**：已创建的版本不可修改，只能创建新版本
4. **单机部署**：初期仅支持单进程，不支持分布式部署

### 6.2 性能约束
1. **向量搜索**：单次查询最多返回100条结果
2. **缓存大小**：moka-py缓存上限1000个Prompt（LRU淘汰）
3. **并发队列**：队列最大长度100，超出时拒绝请求
4. **模板变量**：单个role最多支持20个占位符

### 6.3 数据约束
1. **版本号**：格式必须为`x.x`（主版本.次版本），最大99.99
2. **Prompt名称**：最长200字符，仅支持字母、数字、下划线
3. **标签数量**：单个Prompt最多10个标签
4. **原则引用**：单个Prompt最多引用5个原则
5. **role数量**：单个版本最多20个role

### 6.4 安全约束
1. **SQL注入防护**：所有输入参数化查询
2. **模板注入防护**：Jinja2沙箱模式，禁用危险函数
3. **向量维度**：固定为1536维（OpenAI text-embedding-ada-002标准）

---

## 7. 未来扩展规划

### 7.1 Phase 2（短期）
- 支持Redis队列（替代进程内队列）
- 支持分布式缓存（Redis替代moka-py）
- 增加Prompt使用统计（调用次数、成功率）
- 支持A/B测试（同一Prompt多版本对比）

### 7.2 Phase 3（中期）
- 增加Web UI管理界面
- 支持Prompt模板市场（导入/导出）
- 增加变更审批流程
- 支持多租户隔离

### 7.3 Phase 4（长期）
- 智能推荐相似Prompt
- 自动生成变更日志（基于diff）
- Prompt性能分析（响应时间、token消耗）
- 集成CI/CD流程（Prompt即代码）

---

## 8. 验收标准

### 8.1 功能验收
- [ ] 所有CRUD接口正常工作
- [ ] 向量搜索准确率>90%
- [ ] 占位符替换100%成功
- [ ] 乐观锁冲突正确处理
- [ ] 缓存命中率>80%

### 8.2 性能验收
- [ ] 单次查询响应时间<100ms（缓存命中）
- [ ] 单次查询响应时间<500ms（缓存未命中）
- [ ] 支持并发100 QPS
- [ ] 数据库大小<1GB（1万个Prompt）

### 8.3 稳定性验收
- [ ] 7x24小时运行无崩溃
- [ ] 并发场景无数据竞争
- [ ] 队列溢出时优雅降级
- [ ] 数据库损坏可自动恢复

---

## 9. 部署选项

### 9.1 本地部署（SQLite）
- **适用场景**：开发环境、单机部署、数据量较小
- **数据库**：SQLite 3.40+ + sqlite-vec扩展
- **优点**：零配置、轻量级、易于备份
- **限制**：不支持高并发、无法水平扩展

### 9.2 云端部署（Supabase）
- **适用场景**：生产环境、团队协作、高可用要求
- **数据库**：Supabase PostgreSQL + pgvector扩展
- **配置要求**：
  - 启用pgvector扩展：`create extension if not exists vector;`
  - 创建向量搜索RPC函数：`match_prompt_versions`
  - 配置环境变量：`SUPABASE_URL`, `SUPABASE_KEY`
  - 可选直接连接字符串：`SUPABASE_CONNECTION_STRING`
- **安全建议**：
  - 使用Service Role Key进行后端操作
  - 配置RLS（行级安全）策略
  - 定期轮换密钥
  - 限制RPC函数执行权限

### 9.3 数据库切换
系统支持通过配置文件无缝切换本地SQLite和云端Supabase，无需修改业务代码。切换时只需更新`config.toml`中的数据库类型和相关连接参数。

---

**文档版本**：v1.0  
**最后更新**：2025-01-20  
**维护人**：[待填写]
