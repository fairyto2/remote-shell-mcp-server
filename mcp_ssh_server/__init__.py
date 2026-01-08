"""
MCP SSH Server - 大模型 SSH 远程连接多轮交互服务

提供 SSH 远程连接管理、会话保持、命令执行等功能，
支持大模型通过 MCP 协议与远程服务器进行多轮交互。
"""

from .server import mcp_ssh_server
from .ssh_manager import SSHConnectionManager
from .session_manager import SessionManager

__version__ = "0.1.0"
__all__ = ["mcp_ssh_server", "SSHConnectionManager", "SessionManager"]
