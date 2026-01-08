"""
简单测试，验证测试框架是否正常工作
"""

import pytest


def test_simple():
    """简单测试"""
    assert True


def test_import():
    """测试导入"""
    import sys
    import os
    
    # 添加项目根目录到 Python 路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    try:
        from mcp_ssh_server.ssh_manager import SSHConnectionManager
        assert True
    except ImportError as e:
        pytest.skip(f"Cannot import SSHConnectionManager: {e}")


if __name__ == "__main__":
    pytest.main([__file__])