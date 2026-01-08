WebSocket 客户端示例

展示如何通过 WebSocket 连接到远程 MCP SSH 服务器。
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketMCPClient:
    """WebSocket MCP 客户端"""
    
    def __init__(self, url: str, api_key: str, client_id: str):
        self.url = url
        self.api_key = api_key
        self.client_id = client_id
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.request_id = 0
    
    async def connect(self):
        """连接到服务器"""
        headers = {
            "X-API-Key": self.api_key,
            "X-Client-ID": self.client_id
        }
        
        self.websocket = await websockets.connect(self.url, extra_headers=headers)
        logger.info(f"已连接到 WebSocket 服务器: {self.url}")
        
        # 初始化连接
        await self._initialize()
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            logger.info("已断开 WebSocket 连接")
    
    async def _initialize(self):
        """初始化连接"""
        init_request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "logging": {}
                },
                "clientInfo": {
                    "name": "websocket-client",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await self._send_request(init_request)
        logger.info("初始化成功")
    
    def _next_id(self) -> int:
        """获取下一个请求 ID"""
        self.request_id += 1
        return self.request_id
    
    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求并等待响应"""
        if not self.websocket:
            raise Exception("未连接到服务器")
        
        # 发送请求
        await self.websocket.send(json.dumps(request))
        
        # 等待响应
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def list_tools(self) -> list:
        """列出可用工具"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list"
        }
        
        response = await self._send_request(request)
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(request)
        return response.get("result", {})
    
    async def listen_for_notifications(self):
        """监听服务器通知"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                # 处理通知（非响应消息）
                if "method" in data:
                    logger.info(f"收到通知: {data['method']}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket 连接已关闭")
        except Exception as e:
            logger.error(f"监听通知时出错: {e}")


async def interactive_client():
    """交互式客户端"""
    # 配置
    ws_url = "ws://localhost:8080/ws"
    api_key = "your-api-key"
    client_id = "interactive-client"
    
    # 创建客户端
    client = WebSocketMCPClient(ws_url, api_key, client_id)
    
    try:
        # 连接到服务器
        await client.connect()
        
        # 列出可用工具
        tools = await client.list_tools()
        print("可用工具:")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool['name']}: {tool['description']}")
        
        # 交互式命令循环
        while True:
            print("\n可用命令:")
            print("  1. 执行工具")
            print("  2. 列出工具")
            print("  3. 退出")
            
            choice = input("请选择 (1-3): ").strip()
            
            if choice == "1":
                # 选择工具
                tool_name = input("输入工具名称: ").strip()
                
                # 获取工具参数
                tool = next((t for t in tools if t['name'] == tool_name), None)
                if not tool:
                    print("未知工具")
                    continue
                
                print(f"工具 {tool_name} 的参数:")
                schema = tool.get('inputSchema', {}).get('properties', {})
                required = tool.get('inputSchema', {}).get('required', [])
                
                arguments = {}
                for param_name, param_info in schema.items():
                    if param_name in required:
                        value = input(f"  {param_name} (必需): ").strip()
                        arguments[param_name] = value
                    else:
                        value = input(f"  {param_name} (可选): ").strip()
                        if value:
                            arguments[param_name] = value
                
                # 执行工具
                try:
                    result = await client.call_tool(tool_name, arguments)
                    if result.get('isError'):
                        print(f"错误: {result.get('content', [{}])[0].get('text', '')}")
                    else:
                        print("结果:")
                        for content in result.get('content', []):
                            print(content.get('text', ''))
                except Exception as e:
                    print(f"执行失败: {e}")
            
            elif choice == "2":
                # 重新列出工具
                tools = await client.list_tools()
                print("\n可用工具:")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
            
            elif choice == "3":
                break
            
            else:
                print("无效选择")
    
    except Exception as e:
        logger.error(f"错误: {e}")
    
    finally:
        # 断开连接
        await client.disconnect()


async def main():
    """主函数"""
    print("WebSocket MCP 客户端示例")
    print("=" * 40)
    
    await interactive_client()


if __name__ == "__main__":
    asyncio.run(main())