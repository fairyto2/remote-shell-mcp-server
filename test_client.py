import asyncio
import httpx
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

def create_client(headers=None, timeout=None, auth=None):
    return httpx.AsyncClient(headers=headers, timeout=timeout, auth=auth, trust_env=False)

async def main():
    # 默认端口是 8080，如果环境变量修改了端口，这里也需要修改
    url = "http://127.0.0.1:8080/mcp"
    print(f"Connecting to {url}...")
    try:
        async with sse_client(url, httpx_client_factory=create_client) as streams:
            read, write = streams
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Connected!")
                
                print("\nListing tools...")
                tools = await session.list_tools()
                for tool in tools.tools:
                    print(f"- {tool.name}: {tool.description}")
                
                print("\nCalling ssh_list_connections...")
                result = await session.call_tool("ssh_list_connections", {})
                print("Result:", result)

                # 测试一个简单的资源读取（如果有的话）
                # print("\nListing resources...")
                # resources = await session.list_resources()
                # print(resources)
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
