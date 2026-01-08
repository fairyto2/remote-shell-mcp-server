import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from src.models.connection import ConnectionInfo, AuthMethod, ConnectionStatus
from src.models.command import CommandResult, ExecutionMode
from src.models.file import FileInfo, FileType


class TestSSHConnectionManager:
    """Test SSH connection manager functionality"""

    @pytest.fixture
    def mock_ssh_client(self):
        """Mock SSH client for testing"""
        mock_client = Mock()
        mock_client.connect = AsyncMock()
        mock_client.exec_command = AsyncMock()
        mock_client.close = AsyncMock()
        mock_client.get_transport = Mock()
        mock_client.get_transport.return_value.is_active = True
        return mock_client

    @pytest.fixture
    def connection_manager(self, mock_ssh_client):
        """Create connection manager with mocked SSH client"""
        with patch("src.ssh_manager.SSHClient", return_value=mock_ssh_client):
            from src.ssh_manager import SSHConnectionManager

            return SSHConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_success(self, connection_manager):
        """Test successful SSH connection"""
        conn_request = {
            "host": "example.com",
            "port": 22,
            "username": "testuser",
            "auth_method": AuthMethod.PASSWORD,
            "password": "secret123",
        }

        connection_info = await connection_manager.connect(conn_request)

        assert connection_info.host == "example.com"
        assert connection_info.username == "testuser"
        assert connection_info.status == ConnectionStatus.CONNECTED
        assert connection_info.connection_id in connection_manager.connections

    @pytest.mark.asyncio
    async def test_connect_failure(self, connection_manager):
        """Test SSH connection failure"""
        connection_manager.ssh_client.connect.side_effect = Exception(
            "Connection failed"
        )

        conn_request = {
            "host": "invalid.com",
            "port": 22,
            "username": "testuser",
            "auth_method": AuthMethod.PASSWORD,
            "password": "secret123",
        }

        with pytest.raises(Exception, match="Connection failed"):
            await connection_manager.connect(conn_request)

    @pytest.mark.asyncio
    async def test_disconnect(self, connection_manager):
        """Test SSH disconnection"""
        # First connect
        conn_request = {
            "host": "example.com",
            "port": 22,
            "username": "testuser",
            "auth_method": AuthMethod.PASSWORD,
            "password": "secret123",
        }

        connection_info = await connection_manager.connect(conn_request)
        connection_id = connection_info.connection_id

        # Then disconnect
        await connection_manager.disconnect(connection_id)

        assert connection_id not in connection_manager.connections
        connection_manager.ssh_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_command(self, connection_manager):
        """Test command execution"""
        # Setup mock command execution
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"hello world\n"
        mock_stderr = Mock()
        mock_stderr.read.return_value = b""
        mock_stdin = Mock()

        connection_manager.ssh_client.exec_command.return_value = (
            mock_stdin,
            mock_stdout,
            mock_stderr,
        )

        # Connect first
        conn_request = {
            "host": "example.com",
            "port": 22,
            "username": "testuser",
            "auth_method": AuthMethod.PASSWORD,
            "password": "secret123",
        }

        connection_info = await connection_manager.connect(conn_request)

        # Execute command
        result = await connection_manager.execute_command(
            connection_info.connection_id, "echo 'hello world'"
        )

        assert isinstance(result, CommandResult)
        assert result.command == "echo 'hello world'"
        assert result.stdout == "hello world\n"
        assert result.exit_code == 0
        assert result.connection_id == connection_info.connection_id

    @pytest.mark.asyncio
    async def test_execute_command_not_connected(self, connection_manager):
        """Test command execution on non-existent connection"""
        with pytest.raises(ValueError, match="Connection not found"):
            await connection_manager.execute_command("invalid-id", "ls -la")

    @pytest.mark.asyncio
    async def test_connection_cleanup(self, connection_manager):
        """Test automatic connection cleanup"""
        # Connect multiple connections
        connections = []
        for i in range(3):
            conn_request = {
                "host": f"server{i}.com",
                "port": 22,
                "username": "testuser",
                "auth_method": AuthMethod.PASSWORD,
                "password": "secret123",
            }
            conn_info = await connection_manager.connect(conn_request)
            connections.append(conn_info.connection_id)

        assert len(connection_manager.connections) == 3

        # Cleanup all connections
        await connection_manager.cleanup()

        assert len(connection_manager.connections) == 0
        assert connection_manager.ssh_client.close.call_count == 3


class TestSSHTools:
    """Test SSH MCP tools"""

    @pytest.fixture
    def mock_connection_manager(self):
        """Mock connection manager for tool testing"""
        manager = Mock()
        manager.connect = AsyncMock()
        manager.disconnect = AsyncMock()
        manager.execute_command = AsyncMock()
        manager.list_directory = AsyncMock()
        manager.upload_file = AsyncMock()
        manager.download_file = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_ssh_connect_tool(self, mock_connection_manager):
        """Test ssh_connect MCP tool"""
        # Mock successful connection
        mock_connection_info = ConnectionInfo(
            host="example.com",
            username="testuser",
            auth_method=AuthMethod.PASSWORD,
            connection_id="conn-123",
        )
        mock_connection_manager.connect.return_value = mock_connection_info

        with patch(
            "src.tools.connection.get_connection_manager",
            return_value=mock_connection_manager,
        ):
            from src.tools.connection import ssh_connect

            result = await ssh_connect(
                host="example.com",
                username="testuser",
                auth_method="password",
                password="secret123",
            )

            assert result["connection_id"] == "conn-123"
            assert result["host"] == "example.com"
            assert result["status"] == "connected"

    @pytest.mark.asyncio
    async def test_ssh_execute_tool(self, mock_connection_manager):
        """Test ssh_execute MCP tool"""
        # Mock command result
        mock_command_result = CommandResult(
            connection_id="conn-123",
            command="ls -la",
            stdout="total 0\n",
            stderr="",
            exit_code=0,
            execution_time=0.1,
        )
        mock_connection_manager.execute_command.return_value = mock_command_result

        with patch(
            "src.tools.execution.get_connection_manager",
            return_value=mock_connection_manager,
        ):
            from src.tools.execution import ssh_execute

            result = await ssh_execute(connection_id="conn-123", command="ls -la")

            assert result["stdout"] == "total 0\n"
            assert result["exit_code"] == 0
            assert result["command"] == "ls -la"

    @pytest.mark.asyncio
    async def test_ssh_list_tool(self, mock_connection_manager):
        """Test ssh_list MCP tool"""
        # Mock directory listing
        mock_files = [
            FileInfo(
                path="/home/user/file1.txt",
                name="file1.txt",
                type=FileType.FILE,
                size=100,
                permissions="rw-r--r--",
            ),
            FileInfo(
                path="/home/user/dir1",
                name="dir1",
                type=FileType.DIRECTORY,
                size=0,
                permissions="rwxr-xr-x",
            ),
        ]
        mock_connection_manager.list_directory.return_value = mock_files

        with patch(
            "src.tools.file_ops.get_connection_manager",
            return_value=mock_connection_manager,
        ):
            from src.tools.file_ops import ssh_list

            result = await ssh_list(
                connection_id="conn-123", path="/home/user", detailed=True
            )

            assert len(result["files"]) == 2
            assert result["files"][0]["name"] == "file1.txt"
            assert result["files"][1]["name"] == "dir1"
            assert result["total_count"] == 2


class TestSSHAuthentication:
    """Test SSH authentication methods"""

    @pytest.mark.asyncio
    async def test_password_authentication(self):
        """Test password-based authentication"""
        with patch("src.ssh_manager.SSHClient") as mock_ssh_class:
            mock_client = Mock()
            mock_ssh_class.return_value = mock_client

            from src.ssh_manager import SSHConnectionManager

            manager = SSHConnectionManager()

            conn_request = {
                "host": "example.com",
                "username": "testuser",
                "auth_method": AuthMethod.PASSWORD,
                "password": "secret123",
            }

            await manager.connect(conn_request)

            mock_client.connect.assert_called_once()
            call_args = mock_client.connect.call_args
            assert call_args[1]["hostname"] == "example.com"
            assert call_args[1]["username"] == "testuser"
            assert call_args[1]["password"] == "secret123"

    @pytest.mark.asyncio
    async def test_key_authentication(self):
        """Test key-based authentication"""
        with patch("src.ssh_manager.SSHClient") as mock_ssh_class:
            mock_client = Mock()
            mock_ssh_class.return_value = mock_client

            from src.ssh_manager import SSHConnectionManager

            manager = SSHConnectionManager()

            conn_request = {
                "host": "example.com",
                "username": "testuser",
                "auth_method": AuthMethod.KEY,
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...",
            }

            await manager.connect(conn_request)

            mock_client.connect.assert_called_once()
            call_args = mock_client.connect.call_args
            assert call_args[1]["hostname"] == "example.com"
            assert call_args[1]["username"] == "testuser"
            assert "pkey" in call_args[1]


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test connection timeout handling"""
        with patch("src.ssh_manager.SSHClient") as mock_ssh_class:
            mock_client = Mock()
            mock_client.connect.side_effect = asyncio.TimeoutError("Connection timeout")
            mock_ssh_class.return_value = mock_client

            from src.ssh_manager import SSHConnectionManager

            manager = SSHConnectionManager()

            conn_request = {
                "host": "slow-server.com",
                "username": "testuser",
                "auth_method": AuthMethod.PASSWORD,
                "password": "secret123",
                "timeout": 5,
            }

            with pytest.raises(asyncio.TimeoutError):
                await manager.connect(conn_request)

    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """Test authentication failure handling"""
        with patch("src.ssh_manager.SSHClient") as mock_ssh_class:
            mock_client = Mock()
            mock_client.connect.side_effect = Exception("Authentication failed")
            mock_ssh_class.return_value = mock_client

            from src.ssh_manager import SSHConnectionManager

            manager = SSHConnectionManager()

            conn_request = {
                "host": "example.com",
                "username": "testuser",
                "auth_method": AuthMethod.PASSWORD,
                "password": "wrongpassword",
            }

            with pytest.raises(Exception, match="Authentication failed"):
                await manager.connect(conn_request)

    @pytest.mark.asyncio
    async def test_command_execution_failure(self):
        """Test command execution failure"""
        with patch("src.ssh_manager.SSHClient") as mock_ssh_class:
            mock_client = Mock()
            mock_client.exec_command.side_effect = Exception("Command execution failed")
            mock_ssh_class.return_value = mock_client

            from src.ssh_manager import SSHConnectionManager

            manager = SSHConnectionManager()

            # Add a mock connection
            conn_info = ConnectionInfo(
                host="example.com", username="testuser", auth_method=AuthMethod.PASSWORD
            )
            manager.connections[conn_info.connection_id] = conn_info
            manager.ssh_client = mock_client

            with pytest.raises(Exception, match="Command execution failed"):
                await manager.execute_command(conn_info.connection_id, "ls -la")


if __name__ == "__main__":
    pytest.main([__file__])
