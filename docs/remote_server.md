 # 远程 MCP SSH 服务器

远程 MCP SSH 服务器允许您通过网络访问 MCP SSH 服务，支持多客户端连接和远程管理。

## 功能特性

- 🌐 **远程访问**: 通过 HTTP/WebSocket 提供远程 MCP 服务
- 🔐 **安全认证**: 支持 JWT 令牌和 API 密钥认证
- 🛡️ **安全防护**: IP 白名单、速率限制、CORS 支持
- 🔧 **灵活配置**: 支持配置文件和环境变量
- 📊 **监控支持**: 提供健康检查和状态监控端点
- 🔄 **多客户端**: 支持多个客户端同时连接

## 安装

### 依赖要求

除了基础依赖外，远程服务器还需要：

```bash
pip install aiohttp PyJWT cryptography
```

或使用 uv：

```bash
uv install aiohttp PyJWT cryptography
```

## 快速开始

### 1. 配置服务器

复制示例配置文件：

```bash
cp config/remote_config.json config/my_config.json
```

编辑配置文件，设置您的 API 密钥和安全选项：

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080
  },
  "security": {
    "enable_auth": true,
    "api_keys": {
      "my-client": "your-secret-api-key"
    }
  }
}
```

### 2. 启动服务器

```bash
# 使用默认配置
uv run python remote_main.py

# 使用自定义配置
MCP_SSH_CONFIG_FILE=config/my_config.json uv run python remote_main.py

# 使用环境变量
MCP_SSH_HOST=0.0.0.0 MCP_SSH_PORT=8080 uv run python remote_main.py
```

### 3. 测试连接

```bash
# 运行简单测试
uv run python examples/simple_test.py
```

## 配置说明

### 服务器配置

```json
{
  "server": {
    "host": "0.0.0.0",        // 监听地址
    "port": 8080,              // 监听端口
    "log_level": "INFO"        // 日志级别
  }
}
```

### 安全配置

```json
{
  "security": {
    "enable_auth": true,           // 是否启用认证
    "jwt_secret": "your-secret",   // JWT 密钥
    "jwt_algorithm": "HS256",      // JWT 算法
    "jwt_expiration": 3600,        // JWT 过期时间（秒）
    "api_keys": {                  // API 密钥映射
      "client1": "key1",
      "client2": "key2"
    },
    "allowed_ips": [               // 允许的 IP 地址
      "127.0.0.1",
      "192.168.1.0/24"
    ],
    "rate_limit": 100,             // 速率限制（每分钟）
    "enable_cors": true,           // 是否启用 CORS
    "cors_origins": ["*"]          // CORS 允许的源
  }
}
```

### SSH 配置

```json
{
  "ssh": {
    "default_timeout": 30,           // 默认超时时间
    "max_connections": 50,            // 最大连接数
    "keepalive_interval": 60,         // 保活间隔
    "connection_cleanup_hours": 24    // 连接清理时间
  }
}
```

### 会话配置

```json
{
  "sessions": {
    "max_sessions": 100,              // 最大会话数
    "session_cleanup_hours": 24,      // 会话清理时间
    "default_working_directory": "/home"  // 默认工作目录
  }
}
```

## API 端点

### WebSocket 端点

- `ws://host:port/ws` - WebSocket MCP 连接

### HTTP 端点

- `POST /mcp` - HTTP MCP 请求
- `GET /health` - 健康检查
- `GET /status` - 服务器状态

## 客户端连接

### HTTP 客户端

```python
import aiohttp
import json

async def call_tool():
    headers = {
        "X-API-Key": "your-api-key",
        "X-Client-ID": "your-client-id"
    }
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "ssh_connect",
            "arguments": {
                "name": "my-server",
                "host": "example.com",
                "username": "user",
                "password": "pass"
            }
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8080/mcp",
            headers=headers,
            data=json.dumps(request)
        ) as response:
            result = await response.json()
            print(result)
```

### WebSocket 客户端

```python
import asyncio
import json
import websockets

async def websocket_client():
    headers = {
        "X-API-Key": "your-api-key",
        "X-Client-ID": "your-client-id"
    }
    
    async with websockets.connect(
        "ws://localhost:8080/ws",
        extra_headers=headers,
        subprotocols=["mcp"],
    ) as websocket:
        # 初始化
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}}
            }
        }
        
        await websocket.send(json.dumps(init_request))
        response = await websocket.recv()
        print(json.loads(response))
```

## 安全最佳实践

### 1. 认证配置

- 始终启用认证 (`enable_auth: true`)
- 使用强密码作为 JWT 密钥
- 定期轮换 API 密钥
- 为不同客户端使用不同的 API 密钥

### 2. 网络安全

- 配置 IP 白名单限制访问
- 使用 HTTPS/WSS 在生产环境中
- 配置防火墙规则限制端口访问
- 使用 VPN 进行额外保护

### 3. 监控和日志

- 启用详细日志记录
- 监控异常活动
- 定期检查日志文件
- 设置告警机制

## 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `MCP_SSH_HOST` | 服务器监听地址 | `0.0.0.0` |
| `MCP_SSH_PORT` | 服务器监听端口 | `8080` |
| `MCP_SSH_LOG_LEVEL` | 日志级别 | `INFO` |
| `MCP_SSH_CONFIG_FILE` | 配置文件路径 | - |
| `MCP_SSH_JWT_SECRET` | JWT 密钥 | 随机生成 |
| `MCP_SSH_API_KEYS` | API 密钥 (格式: id1:key1,id2:key2) | - |
| `MCP_SSH_ALLOWED_IPS` | 允许的 IP (逗号分隔) | - |
| `MCP_SSH_RATE_LIMIT` | 速率限制 | `100` |
| `MCP_SSH_ENABLE_CORS` | 是否启用 CORS | `true` |

## 故障排除

### 常见问题

1. **连接被拒绝**
   - 检查服务器是否启动
   - 验证端口和地址配置
   - 检查防火墙设置

2. **认证失败**
   - 验证 API 密钥是否正确
   - 检查客户端 ID 是否匹配
   - 确认认证已启用

3. **速率限制**
   - 检查请求频率
   - 调整速率限制配置
   - 使用正确的客户端 ID

4. **CORS 错误**
   - 检查 CORS 配置
   - 验证请求源是否在允许列表中
   - 确认 CORS 已启用

### 调试模式

启用详细日志：

```bash
MCP_SSH_LOG_LEVEL=DEBUG uv run python remote_main.py
```

## 部署建议

### Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN pip install -e .

EXPOSE 8080

CMD ["python", "remote_main.py"]
```

构建和运行：

```bash
docker build -t mcp-ssh-remote .
docker run -p 8080:8080 -v $(pwd)/config:/app/config mcp-ssh-remote
```

### Systemd 服务

创建服务文件 `/etc/systemd/system/mcp-ssh-remote.service`：

```ini
[Unit]
Description=MCP SSH Remote Server
After=network.target

[Service]
Type=simple
User=mcp-ssh
WorkingDirectory=/opt/mcp-ssh-server
Environment=MCP_SSH_CONFIG_FILE=/opt/mcp-ssh-server/config/remote_config.json
ExecStart=/opt/mcp-ssh-server/.venv/bin/python remote_main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl enable mcp-ssh-remote
sudo systemctl start mcp-ssh-remote
```

## 性能优化

1. **连接池**: 配置合适的连接池大小
2. **缓存**: 启用适当的缓存机制
3. **负载均衡**: 使用反向代理进行负载均衡
4. **资源限制**: 设置合理的资源限制
5. **监控**: 实施性能监控和告警

## 许可证

MIT License
