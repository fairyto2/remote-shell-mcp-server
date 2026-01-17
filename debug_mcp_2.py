from mcp.server import Server
import inspect

server = Server("test")

print(f"Type of call_tool: {type(server.call_tool)}")
try:
    print("Calling call_tool()...")
    res = server.call_tool()
    print(f"Result: {res}")
except Exception as e:
    print(f"Error calling call_tool(): {e}")
