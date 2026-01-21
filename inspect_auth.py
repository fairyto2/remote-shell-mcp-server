
import inspect
from mcp.server.fastmcp import FastMCP
try:
    from mcp.server.security import AuthSettings
    print("Found AuthSettings in mcp.server.security")
    print(inspect.signature(AuthSettings))
    print(inspect.getdoc(AuthSettings))
except ImportError:
    print("AuthSettings not found in mcp.server.security")

try:
    from mcp.server.fastmcp import AuthSettings
    print("Found AuthSettings in mcp.server.fastmcp")
    # print(inspect.signature(AuthSettings)) # AuthSettings might be a Pydantic model
    print(AuthSettings.model_json_schema())
except ImportError:
    print("AuthSettings not found in mcp.server.fastmcp")
