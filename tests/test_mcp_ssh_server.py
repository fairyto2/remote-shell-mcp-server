"""
测试 MCP SSH 服务器功能
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock
from mcp_ssh_server.server import MCPSshServer
from mcp_ssh_server.ssh_manager import SSHConnectionManager, SSHConfig, SSHConnection
from mcp_ssh_server.session_manager import SessionManager
from mcp.server.models import CallToolRequest


class TestMCPSshServer:
    """测试 MCP SSH 服务器"""

    @pytest.fixture
    def mock_server(self):
        """创建模拟的 MCP SSH 服务器"""
        with patch('mcp_ssh_server.ssh_manager.paramiko'), \
             patch('mcp_ssh_server.session_manager.uuid'):
            server = MCPSshServer()
            return server

    @pytest.mark.asyncio
    async def test_list_tools(self, mock_server):
        """测试工具列表"""
        tools = await mock_server.server.list_tools()
        
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "ssh_connect", "ssh_disconnect", "ssh_list_connections", "ssh_execute",
            "session_create", "session_list", "session_delete", "session_execute",
            "session_history", "session_context", "ssh_upload", "ssh_download", "ssh_list"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names

    @pytest.mark.asyncio
    async def test_ssh_connect_success(self, mock_server):
        """测试 SSH 连接成功"""
        # 模拟成功的连接
        mock_server.ssh_manager.add_connection = Mock(return_value=True)
        
        request = CallToolRequest(
            params=Mock(
                name="ssh_connect",
                arguments={
                    "name": "test-conn",
                    "host": "example.com",
                    "username": "testuser",
                    "password": "testpass"
                }
            )
        )
        
        result = await mock_server.call_tool(request)
        
        assert not result.isError
        assert "SSH 连接建立成功: test-conn" in result.content[0].text

    @pytest.mark.asyncio
    async def test_ssh_connect_failure(self, mock_server):
        """测试 SSH 连接失败"""
        # 模拟失败的连接
        mock_server.ssh_manager.add_connection = Mock(return_value=False)
        
        request = CallToolRequest(
            params=Mock(
                name="ssh_connect",
                arguments={
                    "name": "test-conn",
                    "host": "example.com",
                    "username": "testuser",
                    "password": "wrongpass"
                }
            )
        )
        
        result = await mock_server.call_tool(request)
        
        assert result.isError
        assert "SSH 连接失败: test-conn" in result.content[0].text

    @pytest.mark.asyncio
    async def test_ssh_execute_success(self, mock_server):
        """测试 SSH 命令执行成功"""
        # 模拟成功的命令执行
        mock_server.ssh_manager.execute_command = Mock(return_value={
            "success": True,
            "stdout": "test output",
            "stderr": "",
            "exit_code": 0
        })
        
        request = CallToolRequest(
            params=Mock(
                name="ssh_execute",
                arguments={
                    "connection": "test-conn",
                    "command": "ls -la"
                }
            )
        )
        
        result = await mock_server.call_tool(request)
        
        assert not result.isError
        assert "命令执行成功" in result.content[0].text
        assert "test output" in result.content[0].text

    @pytest.mark.asyncio
    async def test_session_create_success(self, mock_server):
        """测试会话创建成功"""
        # 模拟存在的连接
        mock_server.ssh_manager.get_connection = Mock(return_value=Mock())
        # 模拟会话创建
        mock_server.session_manager.create_session = Mock(return_value="session-123")
        
        request = CallToolRequest(
            params=Mock(
                name="session_create",
                arguments={
                    "name": "test-session",
                    "connection": "test-conn"
                }
            )
        )
        
        result = await mock_server.call_tool(request)
        
        assert not result.isError
        assert "会话创建成功: test-session" in result.content[0].text
        assert "session-123" in result.content[0].text

    @pytest.mark.asyncio
    async def test_ssh_upload_success(self, mock_server):
        """测试文件上传成功"""
        # 模拟成功的文件上传
        mock_server.ssh_manager.upload_file = Mock(return_value={
            "success": True,
            "local_path": "/local/file.txt",
            "remote_path": "/remote/file.txt"
        })
        
        request = CallToolRequest(
            params=Mock(
                name="ssh_upload",
                arguments={
                    "connection": "test-conn",
                    "local_path": "/local/file.txt",
                    "remote_path": "/remote/file.txt"
                }
            )
        )
        
        result = await mock_server.call_tool(request)
        
        assert not result.isError
        assert "文件上传成功" in result.content[0].text

    @pytest.mark.asyncio
    async def test_ssh_list_success(self, mock_server):
        """测试目录列表成功"""
        # 模拟成功的目录列表
        mock_server.ssh_manager.list_directory = Mock(return_value={
            "success": True,
            "path": "/home/user",
            "files": [
                {
                    "name": "file1.txt",
                    "type": "file",
                    "size": 1024,
                    "permissions": "644"
                },
                {
                    "name": "dir1",
                    "type": "directory",
                    "size": 0,
                    "permissions": "755"
                }
            ]
        })
        
        request = CallToolRequest(
            params=Mock(
                name="ssh_list",
                arguments={
                    "connection": "test-conn",
                    "path": "/home/user"
                }
            )
        )
        
        result = await mock_server.call_tool(request)
        
        assert not result.isError
        assert "目录内容: /home/user" in result.content[0].text
        assert "文件: file1.txt" in result.content[0].text
        assert "目录: dir1" in result.content[0].text


class TestSSHConnectionManager:
    """测试 SSH 连接管理器"""

    @pytest.fixture
    def mock_paramiko(self):
        """模拟 paramiko 模块"""
        with patch('mcp_ssh_server.ssh_manager.paramiko') as mock:
            # 模拟 SSH 客户端
            mock_client = Mock()
            mock_client.exec_command.return_value = (
                Mock(),  # stdin
                Mock(read=Mock(return_value=b"output")),  # stdout
                Mock(read=Mock(return_value=b"")),  # stderr
            )
            mock_client.open_sftp.return_value = Mock()
            mock.SSHClient.return_value = mock_client
            mock.AutoAddPolicy.return_value = Mock()
            yield mock

    def test_add_connection_success(self, mock_paramiko):
        """测试添加连接成功"""
        manager = SSHConnectionManager()
        config = SSHConfig(
            host="example.com",
            username="testuser",
            password="testpass"
        )
        
        result = manager.add_connection("test-conn", config)
        
        assert result is True
        assert "test-conn" in manager.connections
        assert manager.connections["test-conn"].is_connected is True

    def test_remove_connection(self, mock_paramiko):
        """测试移除连接"""
        manager = SSHConnectionManager()
        config = SSHConfig(
            host="example.com",
            username="testuser",
            password="testpass"
        )
        
        # 先添加连接
        manager.add_connection("test-conn", config)
        assert "test-conn" in manager.connections
        
        # 移除连接
        manager.remove_connection("test-conn")
        assert "test-conn" not in manager.connections

    def test_execute_command(self, mock_paramiko):
        """测试执行命令"""
        manager = SSHConnectionManager()
        config = SSHConfig(
            host="example.com",
            username="testuser",
            password="testpass"
        )
        
        # 添加连接
        manager.add_connection("test-conn", config)
        
        # 执行命令
        result = manager.execute_command("test-conn", "echo test")
        
        assert result["success"] is True
        assert result["stdout"] == "output"
        assert result["command"] == "echo test"

    def test_upload_file(self, mock_paramiko):
        """测试上传文件"""
        manager = SSHConnectionManager()
        config = SSHConfig(
            host="example.com",
            username="testuser",
            password="testpass"
        )
        
        # 添加连接
        manager.add_connection("test-conn", config)
        
        # 上传文件
        result = manager.upload_file("test-conn", "/local/file.txt", "/remote/file.txt")
        
        assert result["success"] is True
        assert result["local_path"] == "/local/file.txt"
        assert result["remote_path"] == "/remote/file.txt"

    def test_list_directory(self, mock_paramiko):
        """测试列出目录"""
        manager = SSHConnectionManager()
        config = SSHConfig(
            host="example.com",
            username="testuser",
            password="testpass"
        )
        
        # 模拟 SFTP 目录列表
        mock_sftp = mock_paramiko.SSHClient.return_value.open_sftp.return_value
        mock_file = Mock()
        mock_file.filename = "test.txt"
        mock_file.st_mode = 0o100644  # 普通文件
        mock_file.st_size = 1024
        mock_file.st_mtime = 1234567890
        mock_sftp.listdir_attr.return_value = [mock_file]
        
        # 添加连接
        manager.add_connection("test-conn", config)
        
        # 列出目录
        result = manager.list_directory("test-conn", "/home/user")
        
        assert result["success"] is True
        assert result["path"] == "/home/user"
        assert len(result["files"]) == 1
        assert result["files"][0]["name"] == "test.txt"


class TestSessionManager:
    """测试会话管理器"""

    def test_create_session(self):
        """测试创建会话"""
        manager = SessionManager()
        session_id = manager.create_session("test-session", "test-conn")
        
        assert session_id is not None
        assert session_id in manager.sessions
        assert manager.sessions[session_id].name == "test-session"
        assert manager.sessions[session_id].connection_name == "test-conn"

    def test_delete_session(self):
        """测试删除会话"""
        manager = SessionManager()
        session_id = manager.create_session("test-session", "test-conn")
        
        # 删除会话
        result = manager.delete_session(session_id)
        
        assert result is True
        assert session_id not in manager.sessions

    def test_add_user_message(self):
        """测试添加用户消息"""
        manager = SessionManager()
        session_id = manager.create_session("test-session", "test-conn")
        
        # 添加用户消息
        message_id = manager.add_user_message(session_id, "test command")
        
        assert message_id is not None
        session = manager.get_session(session_id)
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "test command"

    def test_add_assistant_message(self):
        """测试添加助手消息"""
        manager = SessionManager()
        session_id = manager.create_session("test-session", "test-conn")
        
        # 添加助手消息
        message_id = manager.add_assistant_message(
            session_id, 
            "command output", 
            "test command",
            {"success": True, "stdout": "output"}
        )
        
        assert message_id is not None
        session = manager.get_session(session_id)
        assert len(session.messages) == 1
        assert session.messages[0].role == "assistant"
        assert session.messages[0].content == "command output"
        assert session.messages[0].command == "test command"

    def test_get_session_history(self):
        """测试获取会话历史"""
        manager = SessionManager()
        session_id = manager.create_session("test-session", "test-conn")
        
        # 添加消息
        manager.add_user_message(session_id, "user message")
        manager.add_assistant_message(session_id, "assistant message")
        
        # 获取历史
        history = manager.get_session_history(session_id)
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "user message"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "assistant message"

    def test_export_import_session(self):
        """测试导出和导入会话"""
        manager = SessionManager()
        session_id = manager.create_session("test-session", "test-conn")
        
        # 添加消息
        manager.add_user_message(session_id, "user message")
        manager.add_assistant_message(session_id, "assistant message")
        
        # 导出会话
        exported_data = manager.export_session(session_id)
        assert exported_data is not None
        
        # 删除会话
        manager.delete_session(session_id)
        assert session_id not in manager.sessions
        
        # 导入会话
        new_session_id = manager.import_session(exported_data)
        assert new_session_id is not None
        assert new_session_id in manager.sessions
        
        # 验证导入的数据
        session = manager.get_session(new_session_id)
        assert session.name == "test-session"
        assert session.connection_name == "test-conn"
        assert len(session.messages) == 2


if __name__ == "__main__":
    pytest.main([__file__])