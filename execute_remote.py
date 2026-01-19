"""
使用 MCP 执行远程命令的示例
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

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self):
        """连接到服务器"""
        self.session = aiohttp.ClientSession()
        logger.info(f"已连接到远程 MCP 服务器: {self.base_url}")

    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
            logger.info("已断开连接")

    async def _make_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送 MCP 请求"""
        if not self.session:
            raise Exception("未连接到服务器")

        headers = {"Content-Type": "application/json"}

        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params if params is not None else {},
        }

        async with self.session.post(
            f"{self.base_url}/mcp", headers=headers, json=request_data
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.text()
                raise Exception(f"请求失败: {error}")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        response = await self._make_request(
            "tools/call", {"name": name, "arguments": arguments}
        )
        return response.get("result", {})


async def execute_remote_command():
    """执行远程命令"""
    # 配置
    server_url = "http://localhost:8080"

    # 创建客户端
    client = RemoteMCPClient(server_url)

    try:
        # 连接到服务器
        await client.connect()

        # 建立 SSH 连接到 10.7.195.122
        print("建立 SSH 连接到 10.7.195.122...")
        result = await client.call_tool(
            "ssh_connect",
            {
                "name": "remote-server",
                "host": "10.7.195.122",
                "username": "topsec",
                "password": "",  # 假设使用密钥或密码，实际需要配置
            },
        )

        if not result.get("isError", False):
            print("SSH 连接成功")

            # 执行 docker ps 命令
            print("执行 docker ps 命令...")
            result = await client.call_tool(
                "ssh_execute",
                {"connection": "remote-server", "command": "docker ps", "timeout": 30},
            )

            if not result.get("isError", False):
                output = result.get("content", [{}])[0].get("text", "")
                print("命令输出:")
                print(output)
            else:
                print(f"命令执行失败: {result}")

            # 断开连接
            await client.call_tool("ssh_disconnect", {"name": "remote-server"})
            print("SSH 连接已断开")
        else:
            print(f"SSH 连接失败: {result}")

    except Exception as e:
        logger.error(f"错误: {e}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(execute_remote_command())
