"""
MCP SSH 服务器

提供 MCP 协议接口，实现 SSH 远程连接和多轮交互功能。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    Tool,
    TextContent,
)

from .ssh_manager import SSHConnectionManager, SSHConfig
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class MCPSshServer:
    """MCP SSH 服务器"""

    def __init__(self):
        self.server = Server("mcp-ssh-server")
        self.ssh_manager = SSHConnectionManager()
        self.session_manager = SessionManager()

        self._setup_handlers()

    def _setup_handlers(self):
        """设置 MCP 处理器"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出可用工具"""
            tools = [
                Tool(
                    name="ssh_connect",
                    description="建立 SSH 连接",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "连接名称"},
                            "host": {"type": "string", "description": "主机地址"},
                            "port": {
                                "type": "integer",
                                "description": "端口号",
                                "default": 22,
                            },
                            "username": {"type": "string", "description": "用户名"},
                            "password": {"type": "string", "description": "密码"},
                            "key_filename": {
                                "type": "string",
                                "description": "私钥文件路径",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "连接超时时间",
                                "default": 30,
                            },
                        },
                        "required": ["name", "host", "username"],
                    },
                ),
                Tool(
                    name="ssh_disconnect",
                    description="断开 SSH 连接",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "连接名称"}
                        },
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="ssh_list_connections",
                    description="列出所有 SSH 连接",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="ssh_execute",
                    description="在远程服务器上执行命令",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection": {"type": "string", "description": "连接名称"},
                            "command": {
                                "type": "string",
                                "description": "要执行的命令",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "命令超时时间",
                                "default": 30,
                            },
                        },
                        "required": ["connection", "command"],
                    },
                ),
                Tool(
                    name="session_create",
                    description="创建新的交互会话",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "会话名称"},
                            "connection": {
                                "type": "string",
                                "description": "SSH 连接名称",
                            },
                        },
                        "required": ["name", "connection"],
                    },
                ),
                Tool(
                    name="session_list",
                    description="列出所有会话",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="session_delete",
                    description="删除会话",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "会话 ID"}
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="session_execute",
                    description="在会话中执行命令",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "会话 ID"},
                            "command": {
                                "type": "string",
                                "description": "要执行的命令",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "命令超时时间",
                                "default": 30,
                            },
                        },
                        "required": ["session_id", "command"],
                    },
                ),
                Tool(
                    name="session_history",
                    description="获取会话历史记录",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "会话 ID"},
                            "count": {
                                "type": "integer",
                                "description": "返回消息数量",
                                "default": 20,
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="session_context",
                    description="获取会话上下文信息",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "会话 ID"}
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="ssh_upload",
                    description="上传文件到远程服务器",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection": {"type": "string", "description": "连接名称"},
                            "local_path": {"type": "string", "description": "本地文件路径"},
                            "remote_path": {"type": "string", "description": "远程文件路径"},
                        },
                        "required": ["connection", "local_path", "remote_path"],
                    },
                ),
                Tool(
                    name="ssh_download",
                    description="从远程服务器下载文件",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection": {"type": "string", "description": "连接名称"},
                            "remote_path": {"type": "string", "description": "远程文件路径"},
                            "local_path": {"type": "string", "description": "本地文件路径"},
                        },
                        "required": ["connection", "remote_path", "local_path"],
                    },
                ),
                Tool(
                    name="ssh_list",
                    description="列出远程目录内容",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection": {"type": "string", "description": "连接名称"},
                            "path": {
                                "type": "string",
                                "description": "目录路径",
                                "default": ".",
                            },
                        },
                        "required": ["connection"],
                    },
                ),
                Tool(
                    name="ssh_shell",
                    description="创建交互式 shell",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection": {"type": "string", "description": "连接名称"},
                            "term": {
                                "type": "string",
                                "description": "终端类型",
                                "default": "xterm",
                            },
                        },
                        "required": ["connection"],
                    },
                ),
                Tool(
                    name="shell_send",
                    description="在交互式 shell 中发送命令",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "会话 ID"},
                            "command": {"type": "string", "description": "要执行的命令"},
                        },
                        "required": ["session_id", "command"],
                    },
                ),
                Tool(
                    name="shell_close",
                    description="关闭交互式 shell",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "会话 ID"}
                        },
                        "required": ["session_id"],
                    },
                ),
            ]
            return tools

        @self.server.call_tool()
        async def call_tool(request: CallToolRequest) -> CallToolResult:
            """处理工具调用"""
            try:
                args = request.params.arguments or {}
                if request.params.name == "ssh_connect":
                    return await self._handle_ssh_connect(args)
                elif request.params.name == "ssh_disconnect":
                    return await self._handle_ssh_disconnect(args)
                elif request.params.name == "ssh_list_connections":
                    return await self._handle_ssh_list_connections(args)
                elif request.params.name == "ssh_execute":
                    return await self._handle_ssh_execute(args)
                elif request.params.name == "session_create":
                    return await self._handle_session_create(args)
                elif request.params.name == "session_list":
                    return await self._handle_session_list(args)
                elif request.params.name == "session_delete":
                    return await self._handle_session_delete(args)
                elif request.params.name == "session_execute":
                    return await self._handle_session_execute(args)
                elif request.params.name == "session_history":
                    return await self._handle_session_history(args)
                elif request.params.name == "session_context":
                    return await self._handle_session_context(args)
                elif request.params.name == "ssh_upload":
                    return await self._handle_ssh_upload(args)
                elif request.params.name == "ssh_download":
                    return await self._handle_ssh_download(args)
                elif request.params.name == "ssh_list":
                    return await self._handle_ssh_list(args)
                elif request.params.name == "ssh_shell":
                    return await self._handle_ssh_shell(args)
                elif request.params.name == "shell_send":
                    return await self._handle_shell_send(args)
                elif request.params.name == "shell_close":
                    return await self._handle_shell_close(args)
                else:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text", text=f"未知工具: {request.params.name}"
                            )
                        ],
                        isError=True,
                    )

            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"工具调用失败: {str(e)}")],
                    isError=True,
                )

    async def _handle_ssh_connect(self, args: Dict[str, Any]) -> CallToolResult:
        """处理 SSH 连接"""
        name = args["name"]
        host = args["host"]
        username = args["username"]
        port = args.get("port", 22)
        password = args.get("password")
        key_filename = args.get("key_filename")
        timeout = args.get("timeout", 30)

        config = SSHConfig(
            host=host,
            username=username,
            port=port,
            password=password,
            key_filename=key_filename,
            timeout=timeout,
        )

        success = self.ssh_manager.add_connection(name, config)

        if success:
            return CallToolResult(
                content=[TextContent(type="text", text=f"SSH 连接建立成功: {name}")]
            )
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"SSH 连接失败: {name}")],
                isError=True,
            )

    async def _handle_ssh_disconnect(self, args: Dict[str, Any]) -> CallToolResult:
        """处理 SSH 断开连接"""
        name = args["name"]
        self.ssh_manager.remove_connection(name)

        return CallToolResult(
            content=[TextContent(type="text", text=f"SSH 连接已断开: {name}")]
        )

    async def _handle_ssh_list_connections(
        self, args: Dict[str, Any]
    ) -> CallToolResult:
        """处理列出 SSH 连接"""
        connections = self.ssh_manager.list_connections()

        if not connections:
            return CallToolResult(
                content=[TextContent(type="text", text="没有活跃的 SSH 连接")]
            )

        result = "SSH 连接列表:\n"
        for name, info in connections.items():
            status = "已连接" if info["is_connected"] else "未连接"
            result += f"- {name}: {info['username']}@{info['host']} ({status})\n"

        return CallToolResult(content=[TextContent(type="text", text=result)])

    async def _handle_ssh_execute(self, args: Dict[str, Any]) -> CallToolResult:
        """处理 SSH 命令执行"""
        connection = args["connection"]
        command = args["command"]
        timeout = args.get("timeout", 30)

        result = self.ssh_manager.execute_command(connection, command, timeout)

        if result["success"]:
            output = f"命令执行成功:\n{result['stdout']}"
            if result["stderr"]:
                output += f"\n标准错误:\n{result['stderr']}"
        else:
            output = f"命令执行失败: {result.get('error', '未知错误')}"

        return CallToolResult(
            content=[TextContent(type="text", text=output)],
            isError=not result["success"],
        )

    async def _handle_session_create(self, args: Dict[str, Any]) -> CallToolResult:
        """处理创建会话"""
        name = args["name"]
        connection = args["connection"]

        # 检查连接是否存在
        ssh_conn = self.ssh_manager.get_connection(connection)
        if not ssh_conn:
            return CallToolResult(
                content=[
                    TextContent(type="text", text=f"SSH 连接不存在: {connection}")
                ],
                isError=True,
            )

        session_id = self.session_manager.create_session(name, connection)

        return CallToolResult(
            content=[
                TextContent(
                    type="text", text=f"会话创建成功: {name} (ID: {session_id})"
                )
            ]
        )

    async def _handle_session_list(self, args: Dict[str, Any]) -> CallToolResult:
        """处理列出会话"""
        sessions = self.session_manager.list_sessions()

        if not sessions:
            return CallToolResult(
                content=[TextContent(type="text", text="没有活跃的会话")]
            )

        result = "会话列表:\n"
        for session in sessions:
            result += f"- {session['name']} (ID: {session['id']})\n"
            result += f"  连接: {session['connection_name']}\n"
            result += f"  消息数: {session['message_count']}\n"
            result += f"  工作目录: {session['working_directory']}\n"

        return CallToolResult(content=[TextContent(type="text", text=result)])

    async def _handle_session_delete(self, args: Dict[str, Any]) -> CallToolResult:
        """处理删除会话"""
        session_id = args["session_id"]
        success = self.session_manager.delete_session(session_id)

        if success:
            return CallToolResult(
                content=[TextContent(type="text", text=f"会话已删除: {session_id}")]
            )
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"会话不存在: {session_id}")],
                isError=True,
            )

    async def _handle_session_execute(self, args: Dict[str, Any]) -> CallToolResult:
        """处理会话中执行命令"""
        session_id = args["session_id"]
        command = args["command"]
        timeout = args.get("timeout", 30)

        session = self.session_manager.get_session(session_id)
        if not session:
            return CallToolResult(
                content=[TextContent(type="text", text=f"会话不存在: {session_id}")],
                isError=True,
            )

        # 添加用户消息
        self.session_manager.add_user_message(session_id, command)

        # 执行命令
        result = self.ssh_manager.execute_command(
            session.connection_name, command, timeout
        )

        # 添加助手消息
        if result["success"]:
            response = f"命令执行成功:\n{result['stdout']}"
            if result["stderr"]:
                response += f"\n标准错误:\n{result['stderr']}"
        else:
            response = f"命令执行失败: {result.get('error', '未知错误')}"

        self.session_manager.add_assistant_message(
            session_id, response, command, result
        )

        return CallToolResult(
            content=[TextContent(type="text", text=response)],
            isError=not result["success"],
        )

    async def _handle_session_history(self, args: Dict[str, Any]) -> CallToolResult:
        """处理获取会话历史"""
        session_id = args["session_id"]
        count = args.get("count", 20)

        history = self.session_manager.get_session_history(session_id, count)

        if not history:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", text=f"会话不存在或无历史记录: {session_id}"
                    )
                ]
            )

        result = f"会话历史 (最近 {len(history)} 条消息):\n"
        for msg in history:
            timestamp = msg["timestamp"]
            role = msg["role"]
            content = msg["content"]
            result += f"[{role}] {timestamp}: {content}\n"
            if msg["command"]:
                result += f"执行命令: {msg['command']}\n"

        return CallToolResult(content=[TextContent(type="text", text=result)])

    async def _handle_session_context(self, args: Dict[str, Any]) -> CallToolResult:
        """处理获取会话上下文"""
        session_id = args["session_id"]

        context = self.session_manager.get_session_context(session_id)

        if not context:
            return CallToolResult(
                content=[TextContent(type="text", text=f"会话不存在: {session_id}")],
                isError=True,
            )

        result = f"会话上下文:\n"
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

        return CallToolResult(content=[TextContent(type="text", text=result)])

    async def _handle_ssh_upload(self, args: Dict[str, Any]) -> CallToolResult:
        """处理文件上传"""
        connection = args["connection"]
        local_path = args["local_path"]
        remote_path = args["remote_path"]

        result = self.ssh_manager.upload_file(connection, local_path, remote_path)

        if result["success"]:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"文件上传成功: {local_path} -> {remote_path}"
                    )
                ]
            )
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"文件上传失败: {result.get('error', '未知错误')}"
                    )
                ],
                isError=True,
            )

    async def _handle_ssh_download(self, args: Dict[str, Any]) -> CallToolResult:
        """处理文件下载"""
        connection = args["connection"]
        remote_path = args["remote_path"]
        local_path = args["local_path"]

        result = self.ssh_manager.download_file(connection, remote_path, local_path)

        if result["success"]:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"文件下载成功: {remote_path} -> {local_path}"
                    )
                ]
            )
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"文件下载失败: {result.get('error', '未知错误')}"
                    )
                ],
                isError=True,
            )

    async def _handle_ssh_list(self, args: Dict[str, Any]) -> CallToolResult:
        """处理目录列表"""
        connection = args["connection"]
        path = args.get("path", ".")

        result = self.ssh_manager.list_directory(connection, path)

        if result["success"]:
            files = result["files"]
            if not files:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"目录为空: {path}")]
                )

            output = f"目录内容: {path}\n"
            for file_info in files:
                file_type = "目录" if file_info["type"] == "directory" else "文件"
                output += f"{file_type}: {file_info['name']}"
                if file_info["size"]:
                    output += f" ({file_info['size']} 字节)"
                if file_info["permissions"]:
                    output += f" [{file_info['permissions']}]"
                output += "\n"

            return CallToolResult(content=[TextContent(type="text", text=output)])
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"获取目录列表失败: {result.get('error', '未知错误')}"
                    )
                ],
                ),
                            isError=True,
                        )
                
                    async def _handle_ssh_shell(self, args: Dict[str, Any]) -> CallToolResult:
                        """处理创建交互式 shell"""
                        connection = args["connection"]
                        term = args.get("term", "xterm")
                
                        # 创建 shell
                        result = self.ssh_manager.create_shell(connection, term)
                
                        if result["success"]:
                            shell = result["shell"]
                            
                            # 为所有使用该连接的会话创建 shell
                            sessions = self.session_manager.list_sessions()
                            for session in sessions:
                                if session["connection_name"] == connection:
                                    self.session_manager.create_shell(session["id"], shell)
                
                            return CallToolResult(
                                content=[
                                    TextContent(
                                        type="text",
                                        text=f"交互式 shell 创建成功: {connection} (终端类型: {term})"
                                    )
                                ]
                            )
                        else:
                            return CallToolResult(
                                content=[
                                    TextContent(
                                        type="text",
                                        text=f"创建交互式 shell 失败: {result.get('error', '未知错误')}"
                                    )
                                ],
                                isError=True,
                            )
                
                    async def _handle_shell_send(self, args: Dict[str, Any]) -> CallToolResult:
                        """处理在 shell 中发送命令"""
                        session_id = args["session_id"]
                        command = args["command"]
                
                        # 检查会话是否存在
                        session = self.session_manager.get_session(session_id)
                        if not session:
                            return CallToolResult(
                                content=[TextContent(type="text", text=f"会话不存在: {session_id}")],
                                isError=True,
                            )
                
                        # 检查 shell 是否活跃
                        if not self.session_manager.is_shell_active(session_id):
                            return CallToolResult(
                                content=[TextContent(type="text", text=f"会话 {session_id} 没有活跃的 shell")],
                                isError=True,
                            )
                
                        # 获取 shell
                        shell = self.session_manager.get_shell(session_id)
                        if not shell:
                            return CallToolResult(
                                content=[TextContent(type="text", text=f"无法获取会话 {session_id} 的 shell")],
                                isError=True,
                            )
                
                        # 发送命令
                        result = self.ssh_manager.send_shell_command(session.connection_name, shell, command)
                
                        if result["success"]:
                            # 添加用户消息
                            self.session_manager.add_user_message(session_id, command)
                
                            # 添加助手消息
                            response = f"Shell 命令执行成功:\n{result['output']}"
                            self.session_manager.add_assistant_message(
                                session_id, response, command, result
                            )
                
                            return CallToolResult(
                                content=[TextContent(type="text", text=response)]
                            )
                        else:
                            error_msg = f"Shell 命令执行失败: {result.get('error', '未知错误')}"
                            self.session_manager.add_assistant_message(
                                session_id, error_msg, command, result
                            )
                
                            return CallToolResult(
                                content=[TextContent(type="text", text=error_msg)],
                                isError=True,
                            )
                
                    async def _handle_shell_close(self, args: Dict[str, Any]) -> CallToolResult:
                        """处理关闭 shell"""
                        session_id = args["session_id"]
                
                        # 检查会话是否存在
                        session = self.session_manager.get_session(session_id)
                        if not session:
                            return CallToolResult(
                                content=[TextContent(type="text", text=f"会话不存在: {session_id}")],
                                isError=True,
                            )
                
                        # 检查 shell 是否活跃
                        if not self.session_manager.is_shell_active(session_id):
                            return CallToolResult(
                                content=[TextContent(type="text", text=f"会话 {session_id} 没有活跃的 shell")],
                                isError=True,
                            )
                
                        # 获取 shell
                        shell = self.session_manager.get_shell(session_id)
                        if not shell:
                            return CallToolResult(
                                content=[TextContent(type="text", text=f"无法获取会话 {session_id} 的 shell")],
                                isError=True,
                            )
                
                        # 关闭 shell
                        result = self.ssh_manager.close_shell(session.connection_name, shell)
                
                        if result["success"]:
                            # 更新会话状态
                            self.session_manager.close_shell(session_id)
                
                            return CallToolResult(
                                content=[TextContent(type="text", text=f"交互式 shell 已关闭: {session_id}")]
                            )
                        else:
                            return CallToolResult(
                                content=[
                                    TextContent(
                                        type="text",
                                        text=f"关闭 shell 失败: {result.get('error', '未知错误')}"
                                    )
                                ],
                                isError=True,
                            )
                
                    async def run(self):        """运行服务器"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mcp-ssh-server",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None, experimental_capabilities={}
                    ),
                ),
            )

    def shutdown(self):
        """关闭服务器"""
        self.ssh_manager.shutdown()


# 创建全局服务器实例
mcp_ssh_server = MCPSshServer()


async def main():
    """主函数"""
    try:
        await mcp_ssh_server.run()
    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")
    finally:
        mcp_ssh_server.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
