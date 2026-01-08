#!/bin/bash

# 远程 MCP SSH 服务器 curl 测试脚本

# 服务器配置
SERVER_URL="http://localhost:8080"
API_KEY="admin-key"
CLIENT_ID="admin"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_test() {
    echo -e "${YELLOW}测试: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 1. 测试健康检查（无认证）
print_test "健康检查（无认证）"
response=$(curl -s -w "\n%{http_code}" "$SERVER_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "401" ]; then
    print_success "正确返回 401 未授权"
else
    print_error "期望 401，实际 $http_code"
fi

# 2. 测试健康检查（带认证）
print_test "健康检查（带认证）"
response=$(curl -s -w "\n%{http_code}" \
    -H "X-API-Key: $API_KEY" \
    -H "X-Client-ID: $CLIENT_ID" \
    "$SERVER_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    print_success "健康检查成功"
    echo "  响应: $body"
else
    print_error "健康检查失败，状态码: $http_code"
fi

# 3. 测试状态检查
print_test "状态检查"
response=$(curl -s -w "\n%{http_code}" \
    -H "X-API-Key: $API_KEY" \
    -H "X-Client-ID: $CLIENT_ID" \
    "$SERVER_URL/status")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    print_success "状态检查成功"
    echo "  响应: $body"
else
    print_error "状态检查失败，状态码: $http_code"
fi

# 4. MCP 初始化
print_test "MCP 初始化"
init_request='{
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
}'

response=$(curl -s -w "\n%{http_code}" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -H "X-Client-ID: $CLIENT_ID" \
    -d "$init_request" \
    "$SERVER_URL/mcp")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    print_success "MCP 初始化成功"
    echo "  响应: $body"
else
    print_error "MCP 初始化失败，状态码: $http_code"
    echo "  响应: $body"
fi

# 5. 列出工具
print_test "列出可用工具"
tools_request='{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
}'

response=$(curl -s -w "\n%{http_code}" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -H "X-Client-ID: $CLIENT_ID" \
    -d "$tools_request" \
    "$SERVER_URL/mcp")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    print_success "获取工具列表成功"
    tool_count=$(echo "$body" | jq -r '.result.tools | length' 2>/dev/null || echo "N/A")
    echo "  工具数量: $tool_count"
    
    # 显示前几个工具
    echo "  前5个工具:"
    echo "$body" | jq -r '.result.tools[:5] | .[] | "  - \(.name): \(.description)"' 2>/dev/null || echo "  无法解析工具列表"
else
    print_error "获取工具列表失败，状态码: $http_code"
    echo "  响应: $body"
fi

# 6. 测试 SSH 连接（需要实际的 SSH 服务器）
print_test "建立 SSH 连接（示例）"
connect_request='{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "ssh_connect",
        "arguments": {
            "name": "test-server",
            "host": "example.com",
            "username": "testuser",
            "password": "testpass"
        }
    }
}'

response=$(curl -s -w "\n%{http_code}" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -H "X-Client-ID: $CLIENT_ID" \
    -d "$connect_request" \
    "$SERVER_URL/mcp")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    print_success "SSH 连接请求已发送"
    echo "  响应: $body"
else
    print_error "SSH 连接请求失败，状态码: $http_code"
    echo "  响应: $body"
fi

# 7. 测试无效认证
print_test "无效认证测试"
response=$(curl -s -w "\n%{http_code}" \
    -H "X-API-Key: invalid-key" \
    -H "X-Client-ID: test" \
    "$SERVER_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "401" ]; then
    print_success "正确拒绝无效认证"
else
    print_error "期望 401，实际 $http_code"
fi

# 8. 测试速率限制（快速发送多个请求）
print_test "速率限制测试（发送5个快速请求）"
success_count=0
for i in {1..5}; do
    response=$(curl -s -w "\n%{http_code}" \
        -H "X-API-Key: $API_KEY" \
        -H "X-Client-ID: test-$i" \
        "$SERVER_URL/health")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        ((success_count++))
    fi
done

echo "  成功请求: $success_count/5"
if [ $success_count -le 5 ]; then
    print_success "速率限制正常工作"
else
    print_error "速率限制可能未生效"
fi

echo -e "\n${YELLOW}测试完成！${NC}"
echo "注意：SSH 连接测试使用了示例服务器，实际使用时请替换为真实的 SSH 服务器信息。"