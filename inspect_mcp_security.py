from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

print("TransportSecuritySettings fields:")
for field in TransportSecuritySettings.model_fields:
    print(field)
