import pytest
import asyncio
from datetime import datetime
from src.models.connection import (
    ConnectionInfo,
    AuthMethod,
    ConnectionStatus,
    ConnectionRequest,
)
from src.models.command import (
    CommandResult,
    ExecutionMode,
    ExecuteRequest,
    ShellSession,
    StreamChunk,
)
from src.models.file import (
    FileInfo,
    FileType,
    FileOperation,
    ListDirectoryRequest,
    FileTransferRequest,
)


class TestConnectionModels:
    """Test connection-related data models"""

    def test_connection_info_creation(self):
        """Test ConnectionInfo model creation"""
        conn_info = ConnectionInfo(
            host="example.com",
            port=22,
            username="testuser",
            auth_method=AuthMethod.PASSWORD,
        )

        assert conn_info.host == "example.com"
        assert conn_info.port == 22
        assert conn_info.username == "testuser"
        assert conn_info.auth_method == AuthMethod.PASSWORD
        assert conn_info.status == ConnectionStatus.DISCONNECTED
        assert conn_info.connection_id is not None
        assert isinstance(conn_info.created_at, datetime)
        assert isinstance(conn_info.last_activity, datetime)

    def test_connection_request_validation(self):
        """Test ConnectionRequest model validation"""
        # Valid request
        request = ConnectionRequest(
            host="example.com",
            username="testuser",
            auth_method=AuthMethod.PASSWORD,
            password="secret123",
        )

        assert request.host == "example.com"
        assert request.password == "secret123"

        # Invalid request (missing required fields)
        with pytest.raises(ValueError):
            ConnectionRequest(
                host="example.com",  # Add required field
                auth_method=AuthMethod.PASSWORD,
            )

        assert result.connection_id == "conn-123"
        assert result.command == "ls -la"
        assert result.exit_code == 0
        assert result.execution_time == 0.5
        assert result.mode == ExecutionMode.SYNC

    def test_execute_request_validation(self):
        """Test ExecuteRequest model validation"""
        request = ExecuteRequest(
            connection_id="conn-123",
            command="echo 'hello world'",
            mode=ExecutionMode.ASYNC,
            timeout=60,
        )

        assert request.connection_id == "conn-123"
        assert request.command == "echo 'hello world'"
        assert request.mode == ExecutionMode.ASYNC
        assert request.timeout == 60

    def test_stream_chunk_model(self):
        """Test StreamChunk model"""
        chunk = StreamChunk(content="hello world\n", stream_type="stdout", sequence=1)

        assert chunk.content == "hello world\n"
        assert chunk.stream_type == "stdout"
        assert chunk.sequence == 1
        assert isinstance(chunk.timestamp, datetime)

    def test_shell_session_model(self):
        """Test ShellSession model"""
        session = ShellSession(
            session_id="session-123",
            connection_id="conn-123",
            shell_type="/bin/bash",
            working_directory="/home/user",
        )

        assert session.session_id == "session-123"
        assert session.connection_id == "conn-123"
        assert session.shell_type == "/bin/bash"
        assert session.working_directory == "/home/user"
        assert session.is_active is True
        assert isinstance(session.created_at, datetime)

    def test_execution_mode_enum(self):
        """Test ExecutionMode enum values"""
        assert ExecutionMode.SYNC == "sync"
        assert ExecutionMode.ASYNC == "async"
        assert ExecutionMode.INTERACTIVE == "interactive"


class TestFileModels:
    """Test file operation data models"""

    def test_file_info_creation(self):
        """Test FileInfo model creation"""
        file_info = FileInfo(
            path="/home/user/test.txt",
            name="test.txt",
            type=FileType.FILE,
            size=1024,
            permissions="rw-r--r--",
            owner="user",
            group="user",
        )

        assert file_info.path == "/home/user/test.txt"
        assert file_info.name == "test.txt"
        assert file_info.type == FileType.FILE
        assert file_info.size == 1024
        assert file_info.permissions == "rw-r--r--"
        assert file_info.owner == "user"
        assert file_info.group == "user"
        assert file_info.is_symlink is False

    def test_symlink_file_info(self):
        """Test FileInfo with symbolic link"""
        file_info = FileInfo(
            path="/home/user/link.txt",
            name="link.txt",
            type=FileType.LINK,
            is_symlink=True,
            symlink_target="/home/user/target.txt",
        )

        assert file_info.type == FileType.LINK
        assert file_info.is_symlink is True
        assert file_info.symlink_target == "/home/user/target.txt"

    def test_list_directory_request(self):
        """Test ListDirectoryRequest model"""
        request = ListDirectoryRequest(
            connection_id="conn-123",
            path="/home/user",
            detailed=True,
            hidden=True,
            recursive=False,
            max_depth=1,
        )

        assert request.connection_id == "conn-123"
        assert request.path == "/home/user"
        assert request.detailed is True
        assert request.hidden is True
        assert request.recursive is False
        assert request.max_depth == 1

    def test_file_transfer_request(self):
        """Test FileTransferRequest model"""
        request = FileTransferRequest(
            connection_id="conn-123",
            local_path="/local/file.txt",
            remote_path="/remote/file.txt",
            permissions="644",
            overwrite=True,
            preserve_timestamps=False,
        )

        assert request.connection_id == "conn-123"
        assert request.local_path == "/local/file.txt"
        assert request.remote_path == "/remote/file.txt"
        assert request.permissions == "644"
        assert request.overwrite is True
        assert request.preserve_timestamps is False

    def test_file_type_enum(self):
        """Test FileType enum values"""
        assert FileType.FILE == "file"
        assert FileType.DIRECTORY == "directory"
        assert FileType.LINK == "link"
        assert FileType.SOCKET == "socket"
        assert FileType.BLOCK_DEVICE == "block_device"
        assert FileType.CHARACTER_DEVICE == "character_device"
        assert FileType.FIFO == "fifo"

    def test_file_operation_enum(self):
        """Test FileOperation enum values"""
        assert FileOperation.UPLOAD == "upload"
        assert FileOperation.DOWNLOAD == "download"
        assert FileOperation.LIST == "list"
        assert FileOperation.READ == "read"
        assert FileOperation.WRITE == "write"
        assert FileOperation.DELETE == "delete"
        assert FileOperation.MKDIR == "mkdir"
        assert FileOperation.CHMOD == "chmod"
        assert FileOperation.CHOWN == "chown"


class TestModelIntegration:
    """Test integration between different models"""

    def test_connection_to_command_flow(self):
        """Test flow from connection to command execution"""
        # Create connection
        conn_info = ConnectionInfo(
            host="example.com", username="testuser", auth_method=AuthMethod.KEY
        )

        # Execute command
        command_result = CommandResult(
            connection_id=conn_info.connection_id,
            command="whoami",
            stdout="testuser\n",
            stderr="",
            exit_code=0,
            execution_time=0.1,
        )

        assert command_result.connection_id == conn_info.connection_id

    def test_command_to_shell_session_flow(self):
        """Test flow from command to shell session"""
        shell_session = ShellSession(session_id="session-123", connection_id="conn-123")

        # Execute command in shell context
        command_result = CommandResult(
            connection_id=shell_session.connection_id,
            command="pwd",
            stdout="/home/user\n",
            stderr="",
            exit_code=0,
            execution_time=0.05,
        )

        assert command_result.connection_id == shell_session.connection_id


if __name__ == "__main__":
    pytest.main([__file__])
