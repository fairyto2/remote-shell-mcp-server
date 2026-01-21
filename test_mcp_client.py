
import asyncio
import sys
import httpx
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    # 服务器地址，假设本地运行在 8080 端口
    # FastMCP 默认的 SSE 路径通常是 /sse
    base_url = "http://localhost:8080"
    
    print(f"Checking server health at {base_url}/health...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}/health")
            print(f"Health check: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # 尝试连接 /mcp (我们之前在 ApiKeyAuthMiddleware 中放行了 /mcp)
    # FastMCP 默认可能使用 /sse，但我们在 remote_server.py 中没有显式指定 streamable_http_path，
    # 默认值取决于 FastMCP 版本。
    # 不过我们在 middleware 中放行了 /mcp，但如果 FastMCP 用的是 /sse，那就会被拦截。
    # 让我们先检查一下代码。
    
    server_url = "http://localhost:8080/mcp" 
    print(f"\nConnecting to MCP server at {server_url}...")
    
    try:
        async with sse_client(server_url) as (read_stream, write_stream):
            print("SSE connection established.")
            async with ClientSession(read_stream, write_stream) as session:
                print("Initializing session...")
                await session.initialize()
                print("Connected to MCP server!")
                
                # 列出工具
                print("\n--- Available Tools ---")
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    print(f"- {tool.name}: {tool.description}")
                
                # 调用测试工具：列出 SSH 连接（预期为空）
                print("\n--- Testing ssh_list_connections ---")
                result = await session.call_tool("ssh_list_connections", {})
                print(f"Result: {result.content[0].text}")
                
    except Exception as e:
        print(f"Error connecting to {server_url}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
