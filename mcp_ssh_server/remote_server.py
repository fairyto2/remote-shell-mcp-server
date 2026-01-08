"""
远程 MCP 服务器实现

通过 HTTP/WebSocket 提供 MCP 服务，支持远程客户端连接。
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import web, WSMsgType
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    Tool,
    TextContent,
)

from .ssh_manager import SSHConnectionManager, SSHConfig
from .session_manager import SessionManager
from .config import ConfigManager
from .security import SecurityMiddleware, AuthManager, create_default_config

logger = logging.getLogger(__name__)


class RemoteMCPSshServer:
    """远程 MCP SSH 服务器"""

    def __init__(self, config_path: Optional[str] = None):
        # 加载配置
        self.config = self._load_config(config_path)
        
        self.host = self.config["server"]["host"]
        self.port = self.config["server"]["port"]
        self.app = web.Application()
        self.server = Server("mcp-ssh-server")
        self.ssh_manager = SSHConnectionManager()
        self.session_manager = SessionManager()
        
        # 安全配置
        auth_config = self._create_auth_config()
        self.auth_manager = AuthManager(auth_config)
        self.security = SecurityMiddleware(self.auth_manager)
        
        # 客户端连接管理
        self.clients: Dict[str, web.WebSocketResponse] = {}
        self.client_sessions: Dict[str, Dict[str, Any]] = {}
        
        self._setup_routes()
        self._setup_handlers()
        self._setup_middleware()
        
        # 设置日志
        self._setup_logging()

    def _setup_middleware(self):
        """设置中间件"""
        @web.middleware
        async def auth_middleware(request, handler):
            # 认证请求
            client_id = await self.security.authenticate_request(request)
            if not client_id:
                return web.json_response(
                    {"error": "认证失败"},
                    status=401
                )
            
            # 将客户端 ID 添加到请求中
            request["client_id"] = client_id
            
            try:
                response = await handler(request)
                # 添加 CORS 头
                self.security.add_cors_headers(response)
                return response
            except Exception as e:
                logger.error(f"处理请求失败: {e}")
                return web.json_response(
                    {"error": "内部服务器错误"},
                    status=500
                )
        
        self.app.middlewares.append(auth_middleware)

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置文件"""
        import json
        import os
        
        # 默认配置
        default_config = {
            "server": {
                "host": os.getenv("MCP_SSH_HOST", "0.0.0.0"),
                "port": int(os.getenv("MCP_SSH_PORT", "8080")),
                "log_level": os.getenv("MCP_SSH_LOG_LEVEL", "INFO")
            },
            "security": {
                "enable_auth": True,
                "jwt_secret": "",
                "jwt_algorithm": "HS256",
                "jwt_expiration": 3600,
                "api_keys": {},
                "allowed_ips": [],
                "rate_limit": 100,
                "enable_cors": True,
                "cors_origins": ["*"]
            },
            "ssh": {
                "default_timeout": 30,
                "max_connections": 50,
                "keepalive_interval": 60,
                "connection_cleanup_hours": 24
            },
            "sessions": {
                "max_sessions": 100,
                "session_cleanup_hours": 24,
                "default_working_directory": "/home"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": None
            }
        }
        
        # 如果指定了配置文件路径，尝试加载
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # 合并配置
                self._deep_update(default_config, file_config)
                logger.info(f"已加载配置文件: {config_path}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
        
        return default_config
    
    def _deep_update(self, base_dict: dict, update_dict: dict):
        """深度更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _create_auth_config(self) -> 'AuthConfig':
        """创建认证配置"""
        from .security import AuthConfig
        
        security_config = self.config["security"]
        
        return AuthConfig(
            enable_auth=security_config["enable_auth"],
            jwt_secret=security_config["jwt_secret"] or os.getenv("MCP_SSH_JWT_SECRET", ""),
            jwt_algorithm=security_config["jwt_algorithm"],
            jwt_expiration=security_config["jwt_expiration"],
            api_keys=security_config["api_keys"],
            allowed_ips=security_config["allowed_ips"],
            rate_limit=security_config["rate_limit"],
            enable_cors=security_config["enable_cors"],
            cors_origins=security_config["cors_origins"]
        )
    
    def _setup_logging(self):
        """设置日志"""
        import logging
        
        log_config = self.config["logging"]
        
        # 设置日志级别
        log_level = getattr(logging, log_config["level"].upper())
        
        # 创建处理器
        handlers = [logging.StreamHandler()]
        
        # 如果指定了日志文件，添加文件处理器
        if log_config.get("file"):
            try:
                file_handler = logging.FileHandler(log_config["file"])
                handlers.append(file_handler)
            except Exception as e:
                logger.error(f"无法创建日志文件处理器: {e}")
        
        # 配置根日志器
        logging.basicConfig(
            level=log_level,
            format=log_config["format"],
            handlers=handlers
        )
    
    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_post('/mcp', self.http_handler)
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/status', self.status_handler)

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
                            "port": {"type": "integer", "description": "端口号", "default": 22},
                            "username": {"type": "string", "description": "用户名"},
                            "password": {"type": "string", "description": "密码"},
                            "key_filename": {"type": "string", "description": "私钥文件路径"},
                            "timeout": {"type": "integer", "description": "连接超时时间", "default": 30},
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
                            "command": {"type": "string", "description": "要执行的命令"},
                            "timeout": {"type": "integer", "description": "命令超时时间", "default": 30},
                        },
                        "required": ["connection", "command"],
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
                            "path": {"type": "string", "description": "目录路径", "default": "."},
                        },
                        "required": ["connection"],
                    },
                ),
                Tool(
                    name="session_create",
                    description="创建新的交互会话",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "会话名称"},
                            "connection": {"type": "string", "description": "SSH 连接名称"},
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
                            "command": {"type": "string", "description": "要执行的命令"},
                            "timeout": {"type": "integer", "description": "命令超时时间", "default": 30},
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
                            "count": {"type": "integer", "description": "返回消息数量", "default": 20},
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
                elif request.params.name == "ssh_upload":
                    return await self._handle_ssh_upload(args)
                elif request.params.name == "ssh_download":
                    return await self._handle_ssh_download(args)
                elif request.params.name == "ssh_list":
                    return await self._handle_ssh_list(args)
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

    async def websocket_handler(self, request):
        """WebSocket 处理器"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        client_id = str(uuid.uuid4())
        self.clients[client_id] = ws
        self.client_sessions[client_id] = {
            "initialized": False,
            "capabilities": None
        }
        
        logger.info(f"客户端连接: {client_id}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(client_id, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            "error": "无效的 JSON 格式"
                        }))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket 错误: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket 处理错误: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.client_sessions:
                del self.client_sessions[client_id]
            logger.info(f"客户端断开: {client_id}")
        
        return ws

    async def http_handler(self, request):
        """HTTP 处理器"""
        try:
            data = await request.json()
            response = await self._process_mcp_request(data)
            return web.json_response(response)
        except Exception as e:
            logger.error(f"HTTP 处理错误: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)

    async def health_handler(self, request):
        """健康检查处理器"""
        return web.json_response({
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time()
        })

    async def status_handler(self, request):
        """状态检查处理器"""
        return web.json_response({
            "server": "mcp-ssh-server",
            "version": "0.1.0",
            "clients": len(self.clients),
            "ssh_connections": len(self.ssh_manager.list_connections()),
            "sessions": len(self.session_manager.list_sessions())
        })

    async def _handle_websocket_message(self, client_id: str, data: Dict[str, Any]):
        """处理 WebSocket 消息"""
        ws = self.clients.get(client_id)
        if not ws:
            return
        
        try:
            response = await self._process_mcp_request(data)
            await ws.send_str(json.dumps(response))
        except Exception as e:
            logger.error(f"处理 WebSocket 消息失败: {e}")
            await ws.send_str(json.dumps({
                "error": str(e)
            }))

    async def _process_mcp_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理 MCP 请求"""
        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")
        
        if method == "initialize":
            return {
                "id": request_id,
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
        elif method == "tools/list":
            tools = await self.server.list_tools()
            return {
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tools
                    ]
                }
            }
        elif method == "tools/call":
            request = CallToolRequest(
                params=type('Params', (), {
                    'name': params.get('name'),
                    'arguments': params.get('arguments', {})
                })()
            )
            result = await self.server.call_tool(request)
            return {
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": content.type,
                            "text": content.text
                        }
                        for content in result.content
                    ],
                    "isError": result.isError
                }
            }
        else:
            return {
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"未知方法: {method}"
                }
            }

    # 工具处理方法（与原 server.py 相同）
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

    async def _handle_ssh_list_connections(self, args: Dict[str, Any]) -> CallToolResult:
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
                isError=True,
            )

    async def _handle_session_create(self, args: Dict[str, Any]) -> CallToolResult:
        """处理创建会话"""
        name = args["name"]
        connection = args["connection"]

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

        self.session_manager.add_user_message(session_id, command)

        result = self.ssh_manager.execute_command(
            session.connection_name, command, timeout
        )

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

    async def start(self):
        """启动服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"远程 MCP SSH 服务器启动在 {self.host}:{self.port}")
        return runner

    async def stop(self):
        """停止服务器"""
        self.ssh_manager.shutdown()
        logger.info("远程 MCP SSH 服务器已停止")
