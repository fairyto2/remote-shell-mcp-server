# MCP SSH Server

一个用于大模型 SSH 远程连接多轮交互的 MCP (Model Context Protocol) 服务。

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#测试)

## 功能特性

- 🔐 **安全的 SSH 连接管理**: 支持密码和密钥认证，连接池和自动重连
- 💬 **多轮交互会话**: 维护会话状态、历史记录和上下文信息
- ⚡ **命令执行**: 在远程服务器上安全执行命令，支持超时控制
- 📁 **文件操作**: 上传、下载和浏览远程文件
- 🐚 **交互式 Shell**: 支持持久化 shell 会话和实时交互
- 🔧 **灵活配置**: 支持环境变量和配置文件
- 📊 **完整日志**: 详细的操作日志和错误追踪

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/remote-shell-mcp-server.git
cd remote-shell-mcp-server

# 安装依赖
uv install

# 安装项目
uv pip install -e .
```

### 基本使用

1. **启动服务器**
```bash
uv run mcp_ssh_server
```

2. **建立 SSH 连接**
```json
{
  "name": "ssh_connect",
  "arguments": {
    "name": "my-server",
    "host": "example.com",
    "username": "user",
    "password": "password"
  }
}
```

3. **创建会话**
```json
{
  "name": "session_create",
  "arguments": {
    "name": "my-session",
    "connection": "my-server"
  }
}
```

4. **执行命令**
```json
{
  "name": "session_execute",
  "arguments": {
    "session_id": "会话ID",
    "command": "ls -la"
  }
}
```

详细使用说明请参考 [快速开始指南](docs/quickstart.md) 和 [完整使用文档](docs/usage.md)。

## MCP 工具列表

### SSH 连接管理
- `ssh_connect` - 建立 SSH 连接
- `ssh_disconnect` - 断开 SSH 连接
- `ssh_list_connections` - 列出所有 SSH 连接
- `ssh_execute` - 在远程服务器上执行命令

### 文件操作
- `ssh_upload` - 上传文件到远程服务器
- `ssh_download` - 从远程服务器下载文件
- `ssh_list` - 列出远程目录内容

### 交互式 Shell
- `ssh_shell` - 创建交互式 shell
- `shell_send` - 在 shell 中发送命令
- `shell_close` - 关闭交互式 shell

### 会话管理
- `session_create` - 创建新的交互会话
- `session_list` - 列出所有会话
- `session_delete` - 删除会话
- `session_execute` - 在会话中执行命令
- `session_history` - 获取会话历史记录
- `session_context` - 获取会话上下文信息

## 配置

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `MCP_SSH_LOG_LEVEL` | 日志级别 | `INFO` |
| `MCP_SSH_TIMEOUT` | 默认 SSH 连接超时时间（秒） | `30` |
| `MCP_SSH_CONFIG` | 配置文件路径 | `~/.mcp_ssh_config.json` |

### 配置文件

示例配置文件 (`config/example.json`):

```json
{
  "log_level": "INFO",
  "default_timeout": 30,
  "max_sessions": 100,
  "connections": {
    "prod-server": {
      "host": "prod.example.com",
      "username": "deploy",
      "key_filename": "/path/to/private/key",
      "port": 22,
      "timeout": 30
    }
  }
}
```

## 架构设计

### 核心组件

1. **SSHConnectionManager**: SSH 连接管理器
   - 连接池管理
   - 连接状态监控
   - 自动重连机制
   - 文件操作支持

2. **SessionManager**: 会话管理器
   - 多会话支持
   - 历史记录管理
   - 上下文信息维护
   - 会话导入/导出

3. **MCPSshServer**: MCP 服务器
   - 协议处理
   - 工具注册
   - 请求路由

### 安全特性

- 🔒 **连接隔离**: 每个会话使用独立的 SSH 连接
- 🔑 **认证支持**: 支持密码和密钥认证
- ⏱️ **超时保护**: 命令执行超时机制
- 📝 **日志审计**: 完整的操作日志记录
- 🧹 **自动清理**: 定期清理不活跃会话

## 开发

### 项目结构

```
mcp_ssh_server/
├── __init__.py          # 包初始化
├── server.py            # MCP 服务器主类
├── ssh_manager.py       # SSH 连接管理
├── session_manager.py   # 会话管理
└── config.py           # 配置管理

tests/                   # 测试文件
├── conftest.py         # 测试配置
├── test_simple_core.py # 核心逻辑测试
└── ...

docs/                    # 文档
├── quickstart.md       # 快速开始指南
├── usage.md           # 完整使用文档
└── ...

config/                  # 配置文件
└── example.json        # 配置示例
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_simple_core.py -v

# 生成覆盖率报告
uv run pytest --cov=mcp_ssh_server
```

### 代码质量

```bash
# 代码格式化
uv run black mcp_ssh_server/
uv run isort mcp_ssh_server/

# 类型检查
uv run mypy mcp_ssh_server/

# 代码检查
uv run ruff check mcp_ssh_server/
```

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

### 调试模式

启用详细日志：

```bash
MCP_SSH_LOG_LEVEL=DEBUG uv run mcp_ssh_server
```

## 路线图

- [ ] 支持 SSH 代理转发
- [ ] 添加 SFTP 文件编辑功能
- [ ] 实现命令模板和快捷方式
- [ ] 支持多服务器批量操作
- [ ] 添加 Web 管理界面
- [ ] 集成监控和告警

## 贡献

我们欢迎各种形式的贡献！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 致谢

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Paramiko](https://www.paramiko.org/) - SSH 库
- [FastAPI](https://fastapi.tiangolo.com/) - API 框架灵感

## 联系方式

- 项目主页: https://github.com/your-username/remote-shell-mcp-server
- 问题反馈: https://github.com/your-username/remote-shell-mcp-server/issues
- 文档: https://github.com/your-username/remote-shell-mcp-server/docs