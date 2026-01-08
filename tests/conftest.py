import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock, patch

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Mock external dependencies
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all external dependencies that might not be available"""
    with patch.dict(
        "sys.modules", {"paramiko": Mock(), "mcp": Mock(), "pydantic": Mock()}
    ):
        yield
