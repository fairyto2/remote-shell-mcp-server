"""
测试 Python 路径
"""

import sys
import os

print("Python path:")
for p in sys.path:
    print(f"  {p}")

print("\nCurrent working directory:", os.getcwd())

try:
    import mcp
    print("\nmcp module location:", os.path.dirname(mcp.__file__))
    print("mcp module contents:", [x for x in dir(mcp) if not x.startswith('_')])
except ImportError as e:
    print(f"\nCannot import mcp: {e}")

try:
    from mcp.server import Server
    print("\nSuccessfully imported Server from mcp.server")
except ImportError as e:
    print(f"\nCannot import Server from mcp.server: {e}")
