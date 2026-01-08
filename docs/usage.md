# MCP SSH 服务器使用指南

## 概述

MCP SSH 服务器是一个基于 Model Context Protocol (MCP) 的服务，提供安全的 SSH 远程连接和多轮交互功能。它允许 AI 助手通过持久化 SSH 会话执行命令、管理文件和进行交互式操作。

## 安装

### 依赖要求

- Python 3.13+
- uv (Python 包管理器)

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/your-username/remote-shell-mcp-server.git
cd remote-shell-mcp-server
```

2. 安装依赖
```bash
uv install
```

3. 以开发模式安装
```bash
uv pip install -e .
```

## 配置

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `MCP_SSH_LOG_LEVEL` | 日志级别 | `INFO` |
| `MCP_SSH_TIMEOUT` | 默认 SSH 连接超时时间（秒） | `30` |
| `MCP_SSH_MAX_SESSIONS` | 最大会话数 | `100` |
| `MCP_SSH_CLEANUP_HOURS` | 会话清理时间（小时） | `24` |
| `MCP_SSH_KEEPALIVE` | 保持连接活跃间隔（秒） | `60` |
| `MCP_SSH_CONFIG` | 配置文件路径 | `~/.mcp_ssh_config.json` |

### 配置文件

配置文件使用 JSON 格式，可以定义 SSH 连接和应用设置。参考 `config/example.json`:

```json
{
  "log_level": "INFO",
  "default_timeout": 30,
  "max_sessions": 100,
  "session_cleanup_hours": 24,
  "keepalive_interval": 60,
  "connections": {
    "my-server": {
      "host": "example.com",
      "username": "user",
      "port": 22,
      "timeout": 30,
      "password": "password"
    }
  }
}
```

## 启动服务器

### 基本启动

```bash
uv run mcp_ssh_server
```

### 使用自定义配置

```bash
MCP_SSH_CONFIG=/path/to/config.json uv run mcp_ssh_server
```

### 调试模式

```bash
MCP_SSH_LOG_LEVEL=DEBUG uv run mcp_ssh_server
```

## MCP 工具

服务器提供以下 MCP 工具：

### SSH 连接管理

#### `ssh_connect`
建立 SSH 连接

**参数：**
- `name` (string, 必需): 连接名称
- `host` (string, 必需): 主机地址
- `port` (integer, 可选): 端口号，默认 22
- `username` (string, 必需): 用户名
- `password` (string, 可选): 密码
- `key_filename` (string, 可选): 私钥文件路径
- `timeout` (integer, 可选): 连接超时时间，默认 30

**示例：**
```json
{
  "name": "ssh_connect",
  "arguments": {
    "name": "my-server",
    "host": "example.com",
    "username": "admin",
    "password": "secret123",
    "port": 22
  }
}
```

#### `ssh_disconnect`
断开 SSH 连接

**参数：**
- `name` (string, 必需): 连接名称

#### `ssh_list_connections`
列出所有 SSH 连接

**参数：** 无

#### `ssh_execute`
在远程服务器上执行命令

**参数：**
- `connection` (string, 必需): 连接名称
- `command` (string, 必需): 要执行的命令
- `timeout` (integer, 可选): 命令超时时间，默认 30

### 文件操作

#### `ssh_upload`
上传文件到远程服务器

**参数：**
- `connection` (string, 必需): 连接名称
- `local_path` (string, 必需): 本地文件路径
- `remote_path` (string, 必需): 远程文件路径

#### `ssh_download`
从远程服务器下载文件

**参数：**
- `connection` (string, 必需): 连接名称
- `remote_path` (string, 必需): 远程文件路径
- `local_path` (string, 必需): 本地文件路径

#### `ssh_list`
列出远程目录内容

**参数：**
- `connection` (string, 必需): 连接名称
- `path` (string, 可选): 目录路径，默认 "."

### 交互式 Shell

#### `ssh_shell`
创建交互式 shell

**参数：**
- `connection` (string, 必需): 连接名称
- `term` (string, 可选): 终端类型，默认 "xterm"

#### `shell_send`
在交互式 shell 中发送命令

**参数：**
- `session_id` (string, 必需): 会话 ID
- `command` (string, 必需): 要执行的命令

#### `shell_close`
关闭交互式 shell

**参数：**
- `session_id` (string, 必需): 会话 ID

### 会话管理

#### `session_create`
创建新的交互会话

**参数：**
- `name` (string, 必需): 会话名称
- `connection` (string, 必需): SSH 连接名称

#### `session_list`
列出所有会话

**参数：** 无

#### `session_delete`
删除会话

**参数：**
- `session_id` (string, 必需): 会话 ID

#### `session_execute`
在会话中执行命令

**参数：**
- `session_id` (string, 必需): 会话 ID
- `command` (string, 必需): 要执行的命令
- `timeout` (integer, 可选): 命令超时时间，默认 30

#### `session_history`
获取会话历史记录

**参数：**
- `session_id` (string, 必需): 会话 ID
- `count` (integer, 可选): 返回消息数量，默认 20

#### `session_context`
获取会话上下文信息

**参数：**
- `session_id` (string, 必需): 会话 ID

## 使用示例

### 基本工作流程

1. **建立 SSH 连接**
```json
{
  "name": "ssh_connect",
  "arguments": {
    "name": "prod-server",
    "host": "prod.example.com",
    "username": "deploy",
    "key_filename": "/path/to/private/key"
  }
}
```

2. **创建会话**
```json
{
  "name": "session_create",
  "arguments": {
    "name": "deploy-session",
    "connection": "prod-server"
  }
}
```

3. **执行命令**
```json
{
  "name": "session_execute",
  "arguments": {
    "session_id": "uuid-string",
    "command": "ls -la"
  }
}
```

4. **查看历史**
```json
{
  "name": "session_history",
  "arguments": {
    "session_id": "uuid-string",
    "count": 10
  }
}
```

### 交互式 Shell 使用

1. **创建交互式 shell**
```json
{
  "name": "ssh_shell",
  "arguments": {
    "connection": "prod-server",
    "term": "xterm-256color"
  }
}
```

2. **在 shell 中执行命令**
```json
{
  "name": "shell_send",
  "arguments": {
    "session_id": "uuid-string",
    "command": "cd /var/log && tail -f nginx.log"
  }
}
```

3. **关闭 shell**
```json
{
  "name": "shell_close",
  "arguments": {
    "session_id": "uuid-string"
  }
}
```

### 文件操作示例

1. **上传文件**
```json
{
  "name": "ssh_upload",
  "arguments": {
    "connection": "prod-server",
    "local_path": "/local/app.tar.gz",
    "remote_path": "/tmp/app.tar.gz"
  }
}
```

2. **列出远程目录**
```json
{
  "name": "ssh_list",
  "arguments": {
    "connection": "prod-server",
    "path": "/tmp"
  }
}
```

3. **下载文件**
```json
{
  "name": "ssh_download",
  "arguments": {
    "connection": "prod-server",
    "remote_path": "/remote/logs/app.log",
    "local_path": "/local/logs/app.log"
  }
}
```

## 安全注意事项

1. **密钥管理**：优先使用密钥认证而非密码认证
2. **权限控制**：确保 SSH 用户只有必要的权限
3. **网络安全**：在不可信网络中使用 VPN 或 SSH 隧道
4. **日志审计**：定期检查 SSH 连接和命令执行日志
5. **会话清理**：定期清理不活跃的会话

## 故障排除

### 常见问题

1. **SSH 连接失败**
   - 检查网络连接和防火墙设置
   - 验证认证信息（密码/密钥）
   - 确认 SSH 服务运行状态

2. **命令执行超时**
   - 增加超时时间设置
   - 检查命令执行时间
   - 验证服务器响应速度

3. **文件传输失败**
   - 检查文件路径和权限
   - 确认磁盘空间充足
   - 验证网络稳定性

4. **会话丢失**
   - 检查 SSH 连接状态
   - 验证会话超时设置
   - 查看服务器日志

### 调试模式

启用详细日志以诊断问题：

```bash
MCP_SSH_LOG_LEVEL=DEBUG uv run mcp_ssh_server
```

### 日志分析

日志包含以下信息：
- SSH 连接建立和断开
- 命令执行结果
- 文件传输状态
- 会话管理操作
- 错误和异常信息

## 开发

### 项目结构

```
mcp_ssh_server/
├── __init__.py          # 包初始化
├── server.py            # MCP 服务器主类
├── ssh_manager.py       # SSH 连接管理
├── session_manager.py   # 会话管理
└── config.py           # 配置管理
```

### 运行测试

```bash
uv run pytest tests/ -v
```

### 代码格式化

```bash
uv run black mcp_ssh_server/
uv run isort mcp_ssh_server/
```

### 类型检查

```bash
uv run mypy mcp_ssh_server/
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！