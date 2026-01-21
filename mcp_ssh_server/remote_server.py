"""远程 MCP SSH 服务器（FastMCP 版本）

通过 Streamable HTTP 在 `/mcp` 提供 MCP 服务，并提供 `/ws` WebSocket 传输。
"""

from __future__ import annotations

import logging
import os
import time
import json
from typing import Any, Dict, Optional

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.websocket import websocket_server
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import WebSocketRoute

from .session_manager import SessionManager
from .ssh_manager import SSHConfig, SSHConnectionManager

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- 配置加载 ---

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    default_config = {
        "server": {
            "host": os.getenv("MCP_SSH_HOST", "0.0.0.0"),
            "port": int(os.getenv("MCP_SSH_PORT", "8080")),
            "log_level": os.getenv("MCP_SSH_LOG_LEVEL", "INFO"),
        },
        "ssh": {
            "default_timeout": 30,
            "max_connections": 50,
            "keepalive_interval": 60,
            "connection_cleanup_hours": 24,
        },
        "sessions": {
            "max_sessions": 100,
            "session_cleanup_hours": 24,
            "default_working_directory": "/home",
        },
    }

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                import json
                file_config = json.load(f)
            
            # 简单的深度合并
            def deep_update(base_dict, update_dict):
                for key, value in update_dict.items():
                    if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                        deep_update(base_dict[key], value)
                    else:
                        base_dict[key] = value
            
            deep_update(default_config, file_config)
            logger.info(f"已加载配置文件: {config_path}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")

    return default_config

# --- 全局状态 ---

config_path = os.getenv("MCP_SSH_CONFIG")
config = load_config(config_path)

ssh_manager = SSHConnectionManager()
session_manager = SessionManager()

# --- MCP 服务器初始化 ---

# 配置传输安全设置，允许所有 Host 和 Origin
# 这是解决 421 Misdirected Request 的关键
transport_security_settings = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

mcp = FastMCP(
    name="mcp-ssh-server",
    log_level=str(config["server"].get("log_level", "INFO")).upper(),
    transport_security=transport_security_settings,
    sse_path="/mcp",  # 使用 sse_path 参数而不是 streamable_http_path
)

# --- 工具定义 ---

@mcp.tool()
def ssh_connect(
    name: str,
    host: str,
    username: str,
    port: int = 22,
    password: str | None = None,
    key_filename: str | None = None,
    timeout: int = 30,
) -> str:
    """建立 SSH 连接"""
    ssh_cfg = SSHConfig(
        host=host,
        username=username,
        port=port,
        password=password,
        key_filename=key_filename,
        timeout=timeout,
    )
    if not ssh_manager.add_connection(name, ssh_cfg):
        raise ToolError(f"SSH 连接失败: {name}")
    return f"SSH 连接建立成功: {name}"

@mcp.tool()
def ssh_disconnect(name: str) -> str:
    """断开 SSH 连接"""
    ssh_manager.remove_connection(name)
    return f"SSH 连接已断开: {name}"

@mcp.tool()
def ssh_list_connections() -> str:
    """列出所有 SSH 连接"""
    connections = ssh_manager.list_connections()
    if not connections:
        return "没有活跃的 SSH 连接"
    result = "SSH 连接列表:\n"
    for name, info in connections.items():
        status = "已连接" if info["is_connected"] else "未连接"
        result += f"- {name}: {info['username']}@{info['host']} ({status})\n"
    return result

@mcp.tool()
def ssh_execute(connection: str, command: str, timeout: int = 30) -> str:
    """在远程服务器上执行命令"""
    result = ssh_manager.execute_command(connection, command, timeout)
    if result["success"]:
        output = f"命令执行成功:\n{result['stdout']}"
        if result["stderr"]:
            output += f"\n标准错误:\n{result['stderr']}"
        return output
    raise ToolError(f"命令执行失败: {result.get('error', '未知错误')}")

@mcp.tool()
def ssh_upload(connection: str, local_path: str, remote_path: str) -> str:
    """上传文件到远程服务器"""
    result = ssh_manager.upload_file(connection, local_path, remote_path)
    if result["success"]:
        return f"文件上传成功: {local_path} -> {remote_path}"
    raise ToolError(f"文件上传失败: {result.get('error', '未知错误')}")

@mcp.tool()
def ssh_download(connection: str, remote_path: str, local_path: str) -> str:
    """从远程服务器下载文件"""
    result = ssh_manager.download_file(connection, remote_path, local_path)
    if result["success"]:
        return f"文件下载成功: {remote_path} -> {local_path}"
    raise ToolError(f"文件下载失败: {result.get('error', '未知错误')}")

@mcp.tool()
def ssh_list(connection: str, path: str = ".") -> str:
    """列出远程目录内容"""
    result = ssh_manager.list_directory(connection, path)
    if not result["success"]:
        raise ToolError(f"获取目录列表失败: {result.get('error', '未知错误')}")
    files = result["files"]
    if not files:
        return f"目录为空: {path}"
    output = f"目录内容: {path}\n"
    for file_info in files:
        file_type = "目录" if file_info["type"] == "directory" else "文件"
        output += f"{file_type}: {file_info['name']}"
        if file_info["size"]:
            output += f" ({file_info['size']} 字节)"
        if file_info["permissions"]:
            output += f" [{file_info['permissions']}]"
        output += "\n"
    return output

@mcp.tool()
def session_create(name: str, connection: str) -> str:
    """创建新的交互会话"""
    if not ssh_manager.get_connection(connection):
        raise ToolError(f"SSH 连接不存在: {connection}")
    session_id = session_manager.create_session(name, connection)
    return f"会话创建成功: {name} (ID: {session_id})"

@mcp.tool()
def session_list() -> str:
    """列出所有会话"""
    sessions = session_manager.list_sessions()
    if not sessions:
        return "没有活跃的会话"
    result = "会话列表:\n"
    for session in sessions:
        result += f"- {session['name']} (ID: {session['id']})\n"
        result += f"  连接: {session['connection_name']}\n"
        result += f"  消息数: {session['message_count']}\n"
        result += f"  工作目录: {session['working_directory']}\n"
    return result

@mcp.tool()
def session_delete(session_id: str) -> str:
    """删除会话"""
    if not session_manager.delete_session(session_id):
        raise ToolError(f"会话不存在: {session_id}")
    return f"会话已删除: {session_id}"

@mcp.tool()
def session_execute(session_id: str, command: str, timeout: int = 30) -> str:
    """在会话中执行命令"""
    session = session_manager.get_session(session_id)
    if not session:
        raise ToolError(f"会话不存在: {session_id}")
    session_manager.add_user_message(session_id, command)
    result = ssh_manager.execute_command(session.connection_name, command, timeout)
    if result["success"]:
        response = f"命令执行成功:\n{result['stdout']}"
        if result["stderr"]:
            response += f"\n标准错误:\n{result['stderr']}"
    else:
        response = f"命令执行失败: {result.get('error', '未知错误')}"
    session_manager.add_assistant_message(session_id, response, command, result)
    if not result["success"]:
        raise ToolError(response)
    return response

@mcp.tool()
def session_history(session_id: str, count: int = 20) -> str:
    """获取会话历史记录"""
    history = session_manager.get_session_history(session_id, count)
    if not history:
        return f"会话不存在或无历史记录: {session_id}"
    result = f"会话历史 (最近 {len(history)} 条消息):\n"
    for msg in history:
        result += f"[{msg['role']}] {msg['timestamp']}: {msg['content']}\n"
        if msg['command']:
            result += f"执行命令: {msg['command']}\n"
    return result

@mcp.tool()
def session_context(session_id: str) -> str:
    """获取会话上下文信息"""
    context = session_manager.get_session_context(session_id)
    if not context:
        raise ToolError(f"会话不存在: {session_id}")
    result = "会话上下文:\n"
    result += f"会话 ID: {context['session_id']}\n"
    result += f"会话名称: {context['name']}\n"
    result += f"SSH 连接: {context['connection_name']}\n"
    result += f"工作目录: {context['working_directory']}\n"
    result += f"消息数量: {context['message_count']}\n"
    result += f"最后活动: {context['last_activity']}\n"
    if context["environment"]:
        result += "环境变量:\n"
        for key, value in context["environment"].items():
            result += f"  {key}={value}\n"
    return result

@mcp.tool()
def ssh_shell(connection: str, term: str = "xterm") -> str:
    """创建交互式 shell"""
    result = ssh_manager.create_shell(connection, term)
    if not result["success"]:
        raise ToolError(f"创建交互式 shell 失败: {result.get('error', '未知错误')}")
    shell = result["shell"]
    sessions = session_manager.list_sessions()
    for session in sessions:
        if session["connection_name"] == connection:
            session_manager.create_shell(session["id"], shell)
    return f"交互式 shell 创建成功: {connection} (终端类型: {term})"

@mcp.tool()
def shell_send(session_id: str, command: str) -> str:
    """在交互式 shell 中发送命令"""
    session = session_manager.get_session(session_id)
    if not session:
        raise ToolError(f"会话不存在: {session_id}")
    if not session_manager.is_shell_active(session_id):
        raise ToolError(f"会话 {session_id} 没有活跃的 shell")
    shell = session_manager.get_shell(session_id)
    if not shell:
        raise ToolError(f"无法获取会话 {session_id} 的 shell")
    result = ssh_manager.send_shell_command(session.connection_name, shell, command)
    if result["success"]:
        session_manager.add_user_message(session_id, command)
        response = f"Shell 命令执行成功:\n{result['output']}"
        session_manager.add_assistant_message(session_id, response, command, result)
        return response
    error_msg = f"Shell 命令执行失败: {result.get('error', '未知错误')}"
    session_manager.add_assistant_message(session_id, error_msg, command, result)
    raise ToolError(error_msg)

@mcp.tool()
def shell_close(session_id: str) -> str:
    """关闭交互式 shell"""
    session = session_manager.get_session(session_id)
    if not session:
        raise ToolError(f"会话不存在: {session_id}")
    if not session_manager.is_shell_active(session_id):
        raise ToolError(f"会话 {session_id} 没有活跃的 shell")
    shell = session_manager.get_shell(session_id)
    if not shell:
        raise ToolError(f"无法获取会话 {session_id} 的 shell")
    result = ssh_manager.close_shell(session.connection_name, shell)
    if not result["success"]:
        raise ToolError(f"关闭 shell 失败: {result.get('error', '未知错误')}")
    session_manager.close_shell(session_id)
    return f"交互式 shell 已关闭: {session_id}"

# --- 路由定义 ---

@mcp.custom_route("/", methods=["GET"])
async def root_handler(_: Request) -> Response:
    return JSONResponse(
        {
            "server": "mcp-ssh-server",
            "version": "0.1.0",
            "message": "欢迎使用 MCP SSH 服务器，请使用 /mcp 进行 MCP 通信，或使用 /ws 进行 WebSocket 通信",
            "endpoints": {
                "mcp": "/mcp",
                "websocket": "/ws",
                "health": "/health",
                "status": "/status",
            },
        }
    )

@mcp.custom_route("/health", methods=["GET"])
async def health_handler(_: Request) -> Response:
    return JSONResponse({"status": "healthy", "timestamp": time.time()})

@mcp.custom_route("/status", methods=["GET"])
async def status_handler(_: Request) -> Response:
    return JSONResponse(
        {
            "server": "mcp-ssh-server",
            "version": "0.1.0",
            "ssh_connections": len(ssh_manager.list_connections()),
            "sessions": len(session_manager.list_sessions()),
        }
    )

def main():
    host = config["server"]["host"]
    port = config["server"]["port"]
    logger.info(f"远程 MCP SSH 服务器启动在 {host}:{port}")

    # 重新初始化 mcp 以匹配原代码的路径配置（如果需要）
    # 但 FastMCP 实例已经创建。
    
    # 获取 ASGI 应用
    # 使用 sse_app() 来支持 SSE 传输，因为它与 sse_path 配置匹配
    mcp_app = mcp.sse_app()
    

    # 启动服务器
    uvicorn.run(mcp_app, host=host, port=port, log_level="debug")

if __name__ == "__main__":
    main()
