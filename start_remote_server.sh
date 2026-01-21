#!/bin/bash

# 远程 MCP SSH 服务器启动脚本

# 设置环境变量
export MCP_SSH_HOST=${MCP_SSH_HOST:-"0.0.0.0"}
export MCP_SSH_PORT=${MCP_SSH_PORT:-"8080"}
export MCP_SSH_LOG_LEVEL=${MCP_SSH_LOG_LEVEL:-"INFO"}
export MCP_SSH_CONFIG=${MCP_SSH_CONFIG:-"config/remote_config.json"}

# 检查配置文件
if [ ! -f "$MCP_SSH_CONFIG" ]; then
    echo "警告: 配置文件 $MCP_SSH_CONFIG 不存在"
    echo "使用默认配置"
fi

# 启动服务器
echo "启动远程 MCP SSH 服务器..."
echo "监听地址: $MCP_SSH_HOST:$MCP_SSH_PORT"
echo "配置文件: $MCP_SSH_CONFIG"
echo "日志级别: $MCP_SSH_LOG_LEVEL"
echo ""

# 使用模块方式启动
uv run python -m mcp_ssh_server.remote_server
