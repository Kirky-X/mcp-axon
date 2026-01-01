<div align="center">

# 📘 API Reference

### MCP-Axon 需求链化系统完整 API 文档

[🏠 Home](../README.md) • [📖 User Guide](USER_GUIDE.md) • [🏗️ Architecture](ARCHITECTURE.md)

---

</div>

## 📋 MCP 工具列表

MCP-Axon 提供了 22 个工具来管理需求链化系统的各个方面：

### 🏗️ 项目管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `create_project` | 创建新的需求链项目 | 初始化项目 |
| `update_project` | 更新项目信息 | 修改项目名称或描述 |
| `get_project` | 获取项目详细信息 | 查询项目状态 |
| `get_project_state` | 查询项目当前状态 | 获取进度和统计信息 |

### 📝 需求管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `add_requirement` | 添加需求节点 | 创建新需求 |
| `update_requirement` | 更新需求内容或状态 | 修改现有需求 |
| `mark_as_leaf` | 标记需求为叶子节点 | 表示需求无需进一步分解 |
| `delete_requirement` | 删除需求节点 | 移除需求及其子节点 |
| `get_next_requirement` | 获取下一个待执行需求 | 链式执行导航 |
| `mark_requirement_completed` | 标记需求为已完成 | 推进执行进度 |

### 🔗 依赖管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `add_dependency` | 添加依赖关系 | 建立需求间依赖 |
| `transfer_dependencies` | 应用依赖传递映射 | 处理复杂依赖关系 |

### ✅ 验证管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `add_validation` | 为叶子节点添加验证 | 设置测试用例和验收标准 |

### ⛓ 链化工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `trigger_chaining` | 手动触发链化 | 启动需求链化过程 |
| `resolve_parallel_order` | 指定并行节点执行顺序 | 处理并行需求执行 |

### 💾 状态管理工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `create_snapshot` | 创建项目状态快照 | 保存当前状态 |
| `restore_snapshot` | 从快照恢复项目状态 | 回滚到之前状态 |
| `list_snapshots` | 列出项目的所有快照 | 查看快照历史 |

### 🔒 并发控制工具

| 工具名称 | 描述 | 用途 |
|----------|------|------|
| `acquire_lock` | 获取项目锁 | 防止并发修改 |
| `release_lock` | 释放项目锁 | 解除锁定 |
| `is_locked` | 检查项目是否被锁定 | 查询锁定状态 |
| `get_lock_info` | 获取项目锁的详细信息 | 查看锁的详细信息 |

---

## Overview

<div align="center">

### 🎯 API 设计原则

</div>

<table>
<tr>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/easy.png" width="64"><br>
<b>简单易用</b><br>直观的 MCP 工具接口
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/security-checked.png" width="64"><br>
<b>安全可靠</b><br>类型安全和默认安全
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/module.png" width="64"><br>
<b>可组合</b><br>灵活构建复杂工作流
</td>
<td width="25%" align="center">
<img src="https://img.icons8.com/fluency/96/000000/documentation.png" width="64"><br>
<b>文档完善</b><br>全面的 API 文档
</td>
</tr>
</table>

---

## 🏗️ 项目管理 API

### 创建项目

<div align="center">

#### 🚀 create_project

</div>

创建一个新的需求链项目。

<table>
<tr>
<td width="30%"><b>工具名称</b></td>
<td width="70%">

```
create_project
```

</td>
</tr>
<tr>
<td><b>描述</b></td>
<td>创建新的需求链项目。创建后可以开始添加需求节点。</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `name` (string, 必填): 项目名称
- `description` (string, 可选): 项目描述

</td>
</tr>
<tr>
<td><b>返回值</b></td>
<td><code>Dict[str, Any]</code> - 包含项目 ID 和创建信息的字典</td>
</tr>
<tr>
<td><b>示例</b></td>
<td>

```json
{
  "success": true,
  "data": {
    "id": "12345678-1234-1234-1234-123456789012",
    "name": "电商平台",
    "description": "电商系统需求管理",
    "status": "CREATED",
    "created_at": "2026-01-01T12:00:00Z",
    "next_action": "add_root_requirement"
  },
  "timestamp": "2026-01-01T12:00:00Z"
}
```

</td>
</tr>
</table>

### 更新项目

<div align="center">

#### 📝 update_project

</div>

更新项目的基本信息。

<table>
<tr>
<td width="30%"><b>工具名称</b></td>
<td width="70%">

```
update_project
```

</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `project_id` (string, 必填): 项目 ID
- `name` (string, 可选): 新项目名称
- `description` (string, 可选): 新项目描述

</td>
</tr>
<tr>
<td><b>返回值</b></td>
<td><code>Dict[str, Any]</code> - 更新后的项目信息</td>
</tr>
</table>

### 获取项目

<div align="center">

#### 🔍 get_project

</div>

获取项目的详细信息。

<table>
<tr>
<td width="30%"><b>工具名称</b></td>
<td width="70%">

```
get_project
```

</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `project_id` (string, 必填): 项目 ID

</td>
</tr>
<tr>
<td><b>返回值</b></td>
<td><code>Dict[str, Any]</code> - 项目详细信息</td>
</tr>
</table>

---

## 📝 需求管理 API

### 添加需求

<div align="center">

#### ➕ add_requirement

</div>

添加需求节点到项目中。

<table>
<tr>
<td width="30%"><b>工具名称</b></td>
<td width="70%">

```
add_requirement
```

</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `project_id` (string, 必填): 项目 ID
- `content` (string, 必填): 需求内容
- `parent_id` (string, 可选): 父需求 ID
- `order_in_parent` (integer, 可选): 在父需求中的顺序

</td>
</tr>
<tr>
<td><b>返回值</b></td>
<td><code>Dict[str, Any]</code> - 需求信息</td>
</tr>
<tr>
<td><b>示例</b></td>
<td>

```json
{
  "success": true,
  "data": {
    "requirement_id": "87654321-4321-4321-4321-210987654321",
    "content": "用户认证模块",
    "level": 0,
    "status": "DRAFT",
    "needs_decomposition": true,
    "next_action": "decompose_requirement"
  }
}
```

</td>
</tr>
</table>

### 标记为叶子节点

<div align="center">

#### 🍃 mark_as_leaf

</div>

标记需求为叶子节点，表示该需求不需要进一步分解。

<table>
<tr>
<td width="30%"><b>工具名称</b></td>
<td width="70%">

```
mark_as_leaf
```

</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `requirement_id` (string, 必填): 需求 ID

</td>
</tr>
<tr>
<td><b>返回值</b></td>
<td><code>Dict[str, Any]</code> - 更新后的需求信息</td>
</tr>
</table>

### 添加验证

<div align="center">

#### ✅ add_validation

</div>

为叶子节点添加测试用例和验收标准。

<table>
<tr>
<td width="30%"><b>工具名称</b></td>
<td width="70%">

```
add_validation
```

</td>
</tr>
<tr>
<td><b>参数</b></td>
<td>

- `requirement_id` (string, 必填): 需求 ID（必须是叶子节点）
- `test_cases` (array, 可选): 测试用例列表
- `acceptance_criteria` (string, 可选): 验收标准

</td>
</tr>
<tr>
<td><b>返回值</b></td>
<td><code>Dict[str, Any]</code> - 验证节点信息</td>
</tr>
<tr>
<td><b>示例</b></td>
<td>

```json
{
  "success": true,
  "data": {
    "validation_id": "98765432-1234-1234-1234-123456789012",
    "test_cases": [
      {
        "name": "登录测试",
        "steps": ["输入用户名密码", "点击登录"],
        "expected_result": "登录成功"
      }
    ],
    "acceptance_criteria": "用户能够成功登录系统",
    "status": "pending"
  },
  "next_action": "trigger_chaining"
}
```

</td>
</tr>
</table>

---

## Algorithms

<div align="center">

#### 🔐 Supported Cryptographic Algorithms

</div>

### `Algorithm` Enum

<table>
<tr>
<td width="30%"><b>Definition</b></td>
<td width="70%">

```rust
pub enum Algorithm {
    // Symmetric Encryption
    AES128GCM,
    AES192GCM,
    AES256GCM,
    SM4GCM,
    
    // Asymmetric Signatures
    ECDSAP256,
    ECDSAP384,
    ECDSAP521,
    RSA2048,
    RSA3072,
    RSA4096,
    Ed25519,
    SM2,
}
```

</td>
</tr>
</table>

### Algorithm Details

<details open>
<summary><b>🔐 Symmetric Encryption</b></summary>

<table>
<tr>
<th>Algorithm</th>
<th>Key Size</th>
<th>Security Level</th>
<th>Performance</th>
<th>Use Case</th>
</tr>
<tr>
<td><b>AES-128-GCM</b></td>
<td>128-bit</td>
<td>🟢 High</td>
<td>⚡⚡⚡ Very Fast</td>
<td>General purpose</td>
</tr>
<tr>
<td><b>AES-192-GCM</b></td>
<td>192-bit</td>
<td>🟢 High</td>
<td>⚡⚡ Fast</td>
<td>Extra security</td>
</tr>
<tr>
<td><b>AES-256-GCM</b></td>
<td>256-bit</td>
<td>🟢 Very High</td>
<td>⚡⚡ Fast</td>
<td>Maximum security</td>
</tr>
<tr>
<td><b>SM4-GCM</b></td>
<td>128-bit</td>
<td>🟢 High</td>
<td>⚡ Moderate</td>
<td>Chinese standards</td>
</tr>
</table>

</details>

<details>
<summary><b>✍️ Digital Signatures</b></summary>

<table>
<tr>
<th>Algorithm</th>
<th>Key Size</th>
<th>Security Level</th>
<th>Signature Size</th>
<th>Use Case</th>
</tr>
<tr>
<td><b>ECDSA-P256</b></td>
<td>256-bit</td>
<td>🟢 High</td>
<td>~64 bytes</td>
<td>Modern standard</td>
</tr>
<tr>
<td><b>ECDSA-P384</b></td>
<td>384-bit</td>
<td>🟢 Very High</td>
<td>~96 bytes</td>
<td>High security</td>
</tr>
<tr>
<td><b>RSA-2048</b></td>
<td>2048-bit</td>
<td>🟢 High</td>
<td>256 bytes</td>
<td>Legacy support</td>
</tr>
<tr>
<td><b>Ed25519</b></td>
<td>256-bit</td>
<td>🟢 High</td>
<td>64 bytes</td>
<td>Fast verification</td>
</tr>
<tr>
<td><b>SM2</b></td>
<td>256-bit</td>
<td>🟢 High</td>
<td>~64 bytes</td>
<td>Chinese standards</td>
</tr>
</table>

</details>

---

## Error Handling

<div align="center">

#### 🚨 Error Types and Handling

</div>

### `Error` Enum

```rust
pub enum Error {
    // Initialization Errors
    AlreadyInitialized,
    NotInitialized,
    InitializationFailed,
    
    // Key Errors
    KeyNotFound,
    KeyGenerationFailed,
    InvalidKeyState,
    
    // Cryptographic Errors
    EncryptionFailed,
    DecryptionFailed,
    SignatureFailed,
    VerificationFailed,
    
    // Algorithm Errors
    AlgorithmNotSupported,
    AlgorithmNotFound,
    
    // I/O Errors
    IoError(std::io::Error),
    
    // Custom errors
    Custom(String),
}
```

### Error Handling Pattern

<table>
<tr>
<td width="50%">

**Pattern Matching**
```rust
match operation() {
    Ok(result) => {
        println!("Success: {:?}", result);
    }
    Err(Error::KeyNotFound) => {
        eprintln!("Key not found");
    }
    Err(Error::EncryptionFailed) => {
        eprintln!("Encryption failed");
    }
    Err(e) => {
        eprintln!("Error: {:?}", e);
    }
}
```

</td>
<td width="50%">

**? Operator**
```rust
fn process_data() -> Result<(), Error> {
    init()?;
    
    let km = KeyManager::new()?;
    let key = km.generate_key(
        Algorithm::AES256GCM
    )?;
    
    let cipher = Cipher::new(
        Algorithm::AES256GCM
    )?;
    
    Ok(())
}
```

</td>
</tr>
</table>

---

## Type Definitions

### Common Types

<table>
<tr>
<td width="50%">

**Key ID**
```rust
pub type KeyId = String;
```

**Algorithm Type**
```rust
pub enum Algorithm { /* ... */ }
```

</td>
<td width="50%">

**Result Type**
```rust
pub type Result<T> = 
    std::result::Result<T, Error>;
```

**Log Level**
```rust
pub enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
}
```

</td>
</tr>
</table>

---

## Examples

<div align="center">

### 💡 Common Usage Patterns

</div>

### Example 1: Basic Encryption

```rust
use project_name::{init, Cipher, KeyManager, Algorithm};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize
    init()?;
    
    // Setup
    let km = KeyManager::new()?;
    let key_id = km.generate_key(Algorithm::AES256GCM)?;
    let cipher = Cipher::new(Algorithm::AES256GCM)?;
    
    // Encrypt
    let plaintext = b"Hello, World!";
    let ciphertext = cipher.encrypt(&km, &key_id, plaintext)?;
    
    // Decrypt
    let decrypted = cipher.decrypt(&km, &key_id, &ciphertext)?;
    
    assert_eq!(plaintext, &decrypted[..]);
    println!("✅ Success!");
    
    Ok(())
}
```

### Example 2: Digital Signatures

```rust
use project_name::{init, Cipher, KeyManager, Algorithm};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    init()?;
    
    let km = KeyManager::new()?;
    let key_id = km.generate_key(Algorithm::ECDSAP256)?;
    let signer = Cipher::new(Algorithm::ECDSAP256)?;
    
    // Sign
    let message = b"Important document";
    let signature = signer.sign(&km, &key_id, message)?;
    
    // Verify
    let is_valid = signer.verify(&km, &key_id, message, &signature)?;
    assert!(is_valid);
    
    println!("✅ Signature verified!");
    
    Ok(())
}
```

### Example 3: Advanced Configuration

```rust
use project_name::{init_with_config, Config, LogLevel};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config = Config::builder()
        .thread_pool_size(8)
        .cache_size(2048)
        .log_level(LogLevel::Debug)
        .enable_metrics(true)
        .enable_audit(true)
        .build()?;
    
    init_with_config(config)?;
    
    // Use the library...
    
    Ok(())
}
```

---

<div align="center">

**[📖 User Guide](USER_GUIDE.md)** • **[🏗️ Architecture](ARCHITECTURE.md)** • **[🏠 Home](../README.md)**

Made with ❤️ by the Documentation Team

[⬆ Back to Top](#-api-reference)

</div>