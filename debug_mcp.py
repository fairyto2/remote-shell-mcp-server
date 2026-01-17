from mcp.server import Server
import inspect

server = Server("test")

print(f"Type of list_tools: {type(server.list_tools)}")
print(f"Is callable: {callable(server.list_tools)}")
print(f"Signature: {inspect.signature(server.list_tools)}")

try:
    print("Calling list_tools()...")
    res = server.list_tools()
    print(f"Result: {res}")
except Exception as e:
    print(f"Error calling list_tools(): {e}")
