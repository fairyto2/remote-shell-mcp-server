"""
远程 MCP SSH 客户端示例

展示如何连接到远程 MCP SSH 服务器并使用其功能。
"""

import asyncio
import json
import aiohttp
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RemoteMCPClient:
    """远程 MCP 客户端"""
    
    def __init__(self, base_url: str, api_key: str, client_id: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client_id = client_id
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
    
    async def connect(self):
        """连接到服务器"""
        self.session = aiohttp.ClientSession()
        
        # 获取认证令牌
        await self._authenticate()
        
        logger.info(f"已连接到远程 MCP 服务器: {self.base_url}")
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
            logger.info("已断开连接")
    
    async def _authenticate(self):
        """认证"""
        headers = {
            "X-API-Key": self.api_key,
            "X-Client-ID": self.client_id
        }
        
        async with self.session.post(
            f"{self.base_url}/auth/token",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.token = data.get("token")
                logger.info("认证成功")
            else:
                error = await response.text()
                raise Exception(f"认证失败: {error}")
    
    async def _make_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送 MCP 请求"""
        if not self.session or not self.token:
            raise Exception("未连接到服务器")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        async with self.session.post(
            f"{self.base_url}/mcp",
            headers=headers,
            data=json.dumps(request_data)
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.text()
                raise Exception(f"请求失败: {error}")
    
    async def list_tools(self) -> list:
        """列出可用工具"""
        response = await self._make_request("tools/list")
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        response = await self._make_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return response.get("result", {})
    
    async def ssh_connect(self, name: str, host: str, username: str, 
                         password: str = None, key_filename: str = None, 
                         port: int = 22) -> bool:
        """建立 SSH 连接"""
        arguments = {
            "name": name,
            "host": host,
            "username": username,
            "port": port
        }
        
        if password:
            arguments["password"] = password
        if key_filename:
            arguments["key_filename"] = key_filename
        
        result = await self.call_tool("ssh_connect", arguments)
        return not result.get("isError", False)
    
    async def ssh_execute(self, connection: str, command: str, timeout: int = 30) -> str:
        """执行 SSH 命令"""
        result = await self.call_tool("ssh_execute", {
            "connection": connection,
            "command": command,
            "timeout": timeout
        })
        
        if result.get("isError"):
            raise Exception(f"命令执行失败: {result.get('content', [{}])[0].get('text', '')}")
        
        return result.get("content", [{}])[0].get("text", "")
    
    async def session_create(self, name: str, connection: str) -> str:
        """创建会话"""
        result = await self.call_tool("session_create", {
            "name": name,
            "connection": connection
        })
        
        if result.get("isError"):
            raise Exception(f"创建会话失败: {result.get('content', [{}])[0].get('text', '')}")
        
        # 从响应中提取会话 ID
        text = result.get("content", [{}])[0].get("text", "")
        # 假设格式为 "会话创建成功: name (ID: session_id)"
        if "ID:" in text:
            return text.split("ID: ")[1].rstrip(")")
        
        raise Exception("无法获取会话 ID")
    
    async def session_execute(self, session_id: str, command: str) -> str:
        """在会话中执行命令"""
        result = await self.call_tool("session_execute", {
            "session_id": session_id,
            "command": command
        })
        
        if result.get("isError"):
            raise Exception(f"命令执行失败: {result.get('content', [{}])[0].get('text', '')}")
        
        return result.get("content", [{}])[0].get("text", "")


async def main():
    """主函数 - 演示客户端使用"""
    # 配置
    server_url = "http://localhost:8080"
    api_key = "your-api-key"
    client_id = "example-client"
    
    # 创建客户端
    client = RemoteMCPClient(server_url, api_key, client_id)
    
    try:
        # 连接到服务器
        await client.connect()
        
        # 列出可用工具
        tools = await client.list_tools()
        print("可用工具:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # 建立 SSH 连接
        print("\n建立 SSH 连接...")
        success = await client.ssh_connect(
            name="test-server",
            host="example.com",
            username="testuser",
            password="testpass"
        )
        
        if success:
            print("SSH 连接成功")
            
            # 执行命令
            print("\n执行命令 'ls -la'...")
            output = await client.ssh_execute("test-server", "ls -la")
            print("命令输出:")
            print(output)
            
            # 创建会话
            print("\n创建会话...")
            session_id = await client.session_create("test-session", "test-server")
            print(f"会话创建成功，ID: {session_id}")
            
            # 在会话中执行命令
            print("\n在会话中执行命令 'pwd'...")
            output = await client.session_execute(session_id, "pwd")
            print("命令输出:")
            print(output)
            
            # 断开 SSH 连接
            await client.call_tool("ssh_disconnect", {"name": "test-server"})
            print("\nSSH 连接已断开")
        else:
            print("SSH 连接失败")
    
    except Exception as e:
        logger.error(f"错误: {e}")
    
    finally:
        # 断开连接
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
