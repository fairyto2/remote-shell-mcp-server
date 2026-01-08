"""
测试认证功能
"""

import asyncio
import aiohttp
import json

async def test_auth():
    """测试认证"""
    # 配置
    base_url = "http://localhost:8080"
    
    # 测试无认证的请求
    print("测试无认证请求...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/health") as response:
            print(f"健康检查 (无认证): {response.status}")
            if response.status != 200:
                data = await response.json()
                print(f"  错误: {data}")
    
    # 测试带认证的请求
    print("\n测试带认证请求...")
    headers = {
        "X-API-Key": "admin-key",
        "X-Client-ID": "admin"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/health", headers=headers) as response:
            print(f"健康检查 (带认证): {response.status}")
            if response.status == 200:
                data = await response.json()
                print(f"  结果: {data}")
            else:
                data = await response.json()
                print(f"  错误: {data}")
    
    # 测试 MCP 请求
    print("\n测试 MCP 请求...")
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
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/mcp",
            headers=headers,
            data=json.dumps(init_request)
        ) as response:
            print(f"MCP 初始化: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(f"  结果: {data}")
            else:
                error = await response.text()
                print(f"  错误: {error}")

if __name__ == "__main__":
    asyncio.run(test_auth())
