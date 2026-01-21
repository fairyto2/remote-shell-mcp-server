"""
简单的测试客户端

用于测试远程 MCP SSH 服务器的连接和基本功能。
"""

import asyncio
import aiohttp
import json


async def test_connection():
    """测试连接"""
    base_url = "http://localhost:8080"
    api_key = "test-key"
    client_id = "test-client"
    
    async with aiohttp.ClientSession() as session:
        # 测试健康检查
        print("测试健康检查...")
        async with session.get(f"{base_url}/health") as response:
            if response.status == 200:
                data = await response.json()
                print(f"健康检查成功: {data}")
            else:
                print(f"健康检查失败: {response.status}")
                return
        
        # 测试状态
        print("\n测试状态...")
        async with session.get(f"{base_url}/status") as response:
            if response.status == 200:
                data = await response.json()
                print(f"状态: {data}")
            else:
                print(f"状态检查失败: {response.status}")
        
        # 测试认证
        print("\n测试认证...")
        headers = {
            "X-API-Key": api_key,
            "X-Client-ID": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # 发送初始化请求
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        async with session.post(
            f"{base_url}/mcp",
            headers=headers,
            data=json.dumps(init_request),
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"初始化成功: {data}")
            else:
                error = await response.text()
                print(f"初始化失败: {error}")
                return
        
        # 测试列出工具
        print("\n测试列出工具...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        async with session.post(
            f"{base_url}/mcp",
            headers=headers,
            data=json.dumps(tools_request),
        ) as response:
            if response.status == 200:
                data = await response.json()
                tools = data.get("result", {}).get("tools", [])
                print(f"可用工具 ({len(tools)} 个):")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
            else:
                error = await response.text()
                print(f"列出工具失败: {error}")


if __name__ == "__main__":
    asyncio.run(test_connection())
