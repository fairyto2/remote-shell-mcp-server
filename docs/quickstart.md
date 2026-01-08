# 快速开始指南

## 5 分钟快速上手

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/fairyto2/remote-shell-mcp-server.git
cd remote-shell-mcp-server

# 安装依赖
uv install

# 安装项目
uv pip install -e .
```

### 2. 基本配置

创建配置文件 `~/.mcp_ssh_config.json`：

```json
{
  "connections": {
    "my-server": {
      "host": "your-server.com",
      "username": "your-username",
      "password": "your-password"
    }
  }
}
```

### 3. 启动服务器

```bash
uv run mcp_ssh_server
```

### 4. 使用示例

#### 建立连接
```json
{
  "name": "ssh_connect",
  "arguments": {
    "name": "my-server",
    "host": "your-server.com",
    "username": "your-username",
    "password": "your-password"
  }
}
```

#### 创建会话
```json
{
  "name": "session_create",
  "arguments": {
    "name": "my-session",
    "connection": "my-server"
  }
}
```

#### 执行命令
```json
{
  "name": "session_execute",
  "arguments": {
    "session_id": "会话ID",
    "command": "ls -la"
  }
}
```

## 常见使用场景

### 场景 1：服务器部署

```json
// 1. 连接到生产服务器
{
  "name": "ssh_connect",
  "arguments": {
    "name": "prod",
    "host": "prod.example.com",
    "username": "deploy",
    "key_filename": "/path/to/key"
  }
}

// 2. 创建部署会话
{
  "name": "session_create",
  "arguments": {
    "name": "deploy-session",
    "connection": "prod"
  }
}

// 3. 执行部署命令
{
  "name": "session_execute",
  "arguments": {
    "session_id": "会话ID",
    "command": "cd /app && git pull && docker-compose up -d"
  }
}
```

### 场景 2：日志分析

```json
// 1. 创建交互式 shell
{
  "name": "ssh_shell",
  "arguments": {
    "connection": "prod"
  }
}

// 2. 实时查看日志
{
  "name": "shell_send",
  "arguments": {
    "session_id": "会话ID",
    "command": "tail -f /var/log/app.log"
  }
}

// 3. 分析错误日志
{
  "name": "shell_send",
  "arguments": {
    "session_id": "会话ID",
    "command": "grep ERROR /var/log/app.log | tail -20"
  }
}
```

### 场景 3：文件管理

```json
// 1. 上传配置文件
{
  "name": "ssh_upload",
  "arguments": {
    "connection": "prod",
    "local_path": "./config.json",
    "remote_path": "/app/config.json"
  }
}

// 2. 备份数据
{
  "name": "session_execute",
  "arguments": {
    "session_id": "会话ID",
    "command": "tar -czf /backup/data-$(date +%Y%m%d).tar.gz /data"
  }
}

// 3. 下载备份文件
{
  "name": "ssh_download",
  "arguments": {
    "connection": "prod",
    "remote_path": "/backup/data-20231201.tar.gz",
    "local_path": "./backup/data-20231201.tar.gz"
  }
}
```

## 下一步

- 阅读完整 [使用指南](usage.md)
- 查看 [配置示例](../config/example.json)
- 了解 [安全最佳实践](usage.md#安全注意事项)
- 访问项目主页: https://github.com/fairyto2/remote-shell-mcp-server