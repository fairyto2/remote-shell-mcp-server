
import inspect
from mcp.server.fastmcp import FastMCP
import mcp.server

print("FastMCP init signature:")
print(inspect.signature(FastMCP.__init__))

print("\nFastMCP.streamable_http_app signature:")
print(inspect.signature(FastMCP.streamable_http_app))

try:
    from mcp.server import transport_security
    print("\nmcp.server.transport_security content:")
    print(dir(transport_security))
except ImportError:
    print("\nCould not import mcp.server.transport_security")
