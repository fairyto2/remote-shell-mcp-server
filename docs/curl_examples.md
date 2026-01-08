# curl 测试示例

本文档提供了使用 curl 测试远程 MCP SSH 服务器的各种请求示例。

## 基本配置

```bash
# 服务器地址
SERVER_URL="http://localhost:8080"

# 认证信息（来自 config/remote_config.json）
API_KEY="admin-key"
CLIENT_ID="admin"
```

## 1. 健康检查

### 无认证请求（应该返回 401）
```bash
curl -s "$SERVER_URL/health"
```

### 带认证请求
```bash
curl -s \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  "$SERVER_URL/health"
```

## 2. 状态检查

```bash
curl -s \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  "$SERVER_URL/status"
```

## 3. MCP 协议请求

### MCP 初始化
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {
        "tools": {},
        "logging": {}
      },
      "clientInfo": {
        "name": "curl-test-client",
        "version": "1.0.0"
      }
    }
  }' \
  "$SERVER_URL/mcp"
```

### 列出可用工具
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }' \
  "$SERVER_URL/mcp"
```

## 4. SSH 操作示例

### 建立 SSH 连接
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "ssh_connect",
      "arguments": {
        "name": "my-server",
        "host": "192.168.1.100",
        "username": "admin",
        "password": "your-password",
        "port": 22
      }
    }
  }' \
  "$SERVER_URL/mcp"
```

### 执行命令
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "ssh_execute",
      "arguments": {
        "connection": "my-server",
        "command": "ls -la"
      }
    }
  }' \
  "$SERVER_URL/mcp"
```

### 创建会话
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "session_create",
      "arguments": {
        "name": "my-session",
        "connection": "my-server"
      }
    }
  }' \
  "$SERVER_URL/mcp"
```

### 在会话中执行命令
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
      "name": "session_execute",
      "arguments": {
        "session_id": "your-session-id",
        "command": "pwd"
      }
    }
  }' \
  "$SERVER_URL/mcp"
```

### 文件操作 - 列出目录
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {
      "name": "ssh_list",
      "arguments": {
        "connection": "my-server",
        "path": "/home",
        "detailed": true
      }
    }
  }' \
  "$SERVER_URL/mcp"
```

## 5. 错误测试

### 无效认证
```bash
curl -s \
  -H "X-API-Key: invalid-key" \
  -H "X-Client-ID: test" \
  "$SERVER_URL/health"
```

### 无效请求格式
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID" \
  -d '{
    "invalid": "request"
  }' \
  "$SERVER_URL/mcp"
```

## 6. WebSocket 连接测试

虽然 curl 不支持 WebSocket，但可以使用 `wscat` 或其他 WebSocket 客户端：

```bash
# 安装 wscat
npm install -g wscat

# 连接 WebSocket
wscat -c "ws://localhost:8080/ws" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Client-ID: $CLIENT_ID"
```

## 7. 完整测试脚本

运行项目中的完整测试脚本：

```bash
./test_curl.sh
```

## 注意事项

1. 确保服务器正在运行：`./start_remote_server.sh`
2. 检查配置文件 `config/remote_config.json` 中的 API 密钥
3. SSH 连接测试需要真实的 SSH 服务器信息
4. 某些操作可能需要先建立 SSH 连接
5. 会话操作需要有效的会话 ID

## 响应格式

成功响应示例：
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "logging": {}
    },
    "serverInfo": {
      "name": "mcp-ssh-server",
      "version": "0.1.0"
    }
  }
}
```

错误响应示例：
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method not found"
  }
}
```