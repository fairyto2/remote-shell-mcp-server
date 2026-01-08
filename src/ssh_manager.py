import asyncio
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
import paramiko
from io import StringIO

from .models.connection import (
    ConnectionInfo,
    AuthMethod,
    ConnectionStatus,
    ConnectionRequest,
)
from .models.command import CommandResult, ExecutionMode, StreamChunk
from .models.file import FileInfo, FileType, ListDirectoryResult


class SSHConnectionManager:
    """Manages SSH connections and command execution"""

    def __init__(self, max_connections: int = 10):
        self.connections: Dict[str, ConnectionInfo] = {}
        self.ssh_clients: Dict[str, paramiko.SSHClient] = {}
        self.shell_sessions: Dict[str, paramiko.Channel] = {}
        self.max_connections = max_connections
        self.logger = logging.getLogger(__name__)

    async def connect(self, request: ConnectionRequest) -> ConnectionInfo:
        """Establish SSH connection to remote server"""
        if len(self.connections) >= self.max_connections:
            raise ValueError(
                f"Maximum connections limit reached: {self.max_connections}"
            )

        connection_info = ConnectionInfo(
            host=request.host,
            port=request.port,
            username=request.username,
            auth_method=request.auth_method,
        )

        try:
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Prepare authentication
            auth_kwargs = {
                "hostname": request.host,
                "port": request.port,
                "username": request.username,
                "timeout": request.timeout,
            }

            if request.auth_method == AuthMethod.PASSWORD and request.password:
                auth_kwargs["password"] = request.password
            elif request.auth_method == AuthMethod.KEY:
                if request.private_key:
                    # Handle private key
                    key_file = StringIO(request.private_key)
                    if request.key_passphrase:
                        private_key = paramiko.RSAKey.from_private_key(
                            key_file, password=request.key_passphrase
                        )
                    else:
                        private_key = paramiko.RSAKey.from_private_key(key_file)
                    auth_kwargs["pkey"] = private_key
                else:
                    # Try to use default SSH agent
                    auth_kwargs["look_for_keys"] = True
                    auth_kwargs["allow_agent"] = True
            elif request.auth_method == AuthMethod.AGENT:
                auth_kwargs["look_for_keys"] = True
                auth_kwargs["allow_agent"] = True

            # Connect in thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, client.connect, **auth_kwargs
            )

            # Store connection
            connection_info.status = ConnectionStatus.CONNECTED
            connection_info.session_id = str(id(client))
            self.connections[connection_info.connection_id] = connection_info
            self.ssh_clients[connection_info.connection_id] = client

            self.logger.info(
                f"Connected to {request.host}:{request.port} as {request.username}"
            )
            return connection_info

        except Exception as e:
            connection_info.status = ConnectionStatus.ERROR
            self.logger.error(f"Failed to connect to {request.host}: {e}")
            raise ConnectionError(f"SSH connection failed: {e}")

    async def disconnect(self, connection_id: str) -> bool:
        """Close SSH connection"""
        if connection_id not in self.connections:
            return False

        try:
            # Close SSH client
            client = self.ssh_clients.get(connection_id)
            if client:
                await asyncio.get_event_loop().run_in_executor(None, client.close)

            # Clean up shell sessions
            if connection_id in self.shell_sessions:
                shell = self.shell_sessions[connection_id]
                await asyncio.get_event_loop().run_in_executor(None, shell.close)
                del self.shell_sessions[connection_id]

            # Remove from storage
            del self.connections[connection_id]
            if connection_id in self.ssh_clients:
                del self.ssh_clients[connection_id]

            self.logger.info(f"Disconnected connection {connection_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error disconnecting {connection_id}: {e}")
            return False

    async def execute_command(
        self,
        connection_id: str,
        command: str,
        mode: ExecutionMode = ExecutionMode.SYNC,
        timeout: int = 300,
        working_directory: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        shell: str = "/bin/bash",
    ) -> CommandResult:
        """Execute command on remote server"""
        if connection_id not in self.connections:
            raise ValueError(f"Connection not found: {connection_id}")

        client = self.ssh_clients[connection_id]
        connection_info = self.connections[connection_id]

        # Prepare command with environment and directory
        full_command = command
        if working_directory:
            full_command = f"cd {working_directory} && {command}"

        if environment:
            env_exports = " ".join([f"{k}='{v}'" for k, v in environment.items()])
            full_command = f"export {env_exports} && {full_command}"

        start_time = datetime.now()

        try:
            if mode == ExecutionMode.SYNC:
                # Synchronous execution
                stdin, stdout, stderr = await asyncio.get_event_loop().run_in_executor(
                    None, client.exec_command, full_command, timeout
                )

                # Read output
                stdout_data = await asyncio.get_event_loop().run_in_executor(
                    None, stdout.read
                )
                stderr_data = await asyncio.get_event_loop().run_in_executor(
                    None, stderr.read
                )

                exit_code = stdout.channel.recv_exit_status()

                execution_time = (datetime.now() - start_time).total_seconds()

                # Update connection activity
                connection_info.last_activity = datetime.now()

                return CommandResult(
                    connection_id=connection_id,
                    command=command,
                    stdout=stdout_data.decode("utf-8", errors="ignore"),
                    stderr=stderr_data.decode("utf-8", errors="ignore"),
                    exit_code=exit_code,
                    execution_time=execution_time,
                    mode=mode,
                )

            else:
                # For async/interactive modes, we'll implement streaming
                # This is a placeholder for now
                raise NotImplementedError(f"Execution mode {mode} not yet implemented")

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Command execution failed: {e}")
            return CommandResult(
                connection_id=connection_id,
                command=command,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=execution_time,
                mode=mode,
            )

    async def start_shell(
        self, connection_id: str, shell_type: str = "/bin/bash"
    ) -> str:
        """Start interactive shell session"""
        if connection_id not in self.connections:
            raise ValueError(f"Connection not found: {connection_id}")

        client = self.ssh_clients[connection_id]

        try:
            # Create shell channel
            channel = await asyncio.get_event_loop().run_in_executor(
                None, client.invoke_shell
            )

            # Send initial shell command
            await asyncio.get_event_loop().run_in_executor(
                None, channel.send, f"{shell_type}\n"
            )

            session_id = f"{connection_id}_shell_{len(self.shell_sessions)}"
            self.shell_sessions[session_id] = channel

            self.logger.info(f"Started shell session {session_id}")
            return session_id

        except Exception as e:
            self.logger.error(f"Failed to start shell: {e}")
            raise RuntimeError(f"Shell session failed: {e}")

    async def send_shell_command(self, session_id: str, command: str) -> str:
        """Send command to interactive shell session"""
        if session_id not in self.shell_sessions:
            raise ValueError(f"Shell session not found: {session_id}")

        channel = self.shell_sessions[session_id]

        try:
            # Send command
            await asyncio.get_event_loop().run_in_executor(
                None, channel.send, f"{command}\n"
            )

            # Wait for response (simple implementation)
            await asyncio.sleep(0.1)

            # Read response
            response = ""
            while channel.recv_ready():
                data = await asyncio.get_event_loop().run_in_executor(
                    None, channel.recv, 4096
                )
                response += data.decode("utf-8", errors="ignore")

            return response

        except Exception as e:
            self.logger.error(f"Shell command failed: {e}")
            raise RuntimeError(f"Shell command failed: {e}")

    async def list_directory(
        self,
        connection_id: str,
        path: str = ".",
        detailed: bool = True,
        hidden: bool = False,
        max_depth: int = 1,
    ) -> ListDirectoryResult:
        """List directory contents"""
        if connection_id not in self.connections:
            raise ValueError(f"Connection not found: {connection_id}")

        try:
            # Build ls command
            ls_cmd = "ls"
            if detailed:
                ls_cmd += " -la"
            else:
                ls_cmd += " -1"

            if not hidden:
                ls_cmd += " | grep -v '^\\.'"

            full_command = f"{ls_cmd} {path}"

            # Execute command
            result = await self.execute_command(connection_id, full_command)

            if result.exit_code != 0:
                raise RuntimeError(f"Failed to list directory: {result.stderr}")

            # Parse output
            files = []
            lines = result.stdout.strip().split("\n")

            for line in lines:
                if not line.strip():
                    continue

                if detailed:
                    # Parse detailed ls output
                    file_info = self._parse_ls_line(line, path)
                    if file_info:
                        files.append(file_info)
                else:
                    # Simple filename list
                    file_info = FileInfo(
                        path=f"{path.rstrip('/')}/{line}",
                        name=line,
                        type=FileType.FILE,  # Default, would need additional commands to determine
                        size=0,
                    )
                    files.append(file_info)

            return ListDirectoryResult(
                connection_id=connection_id,
                path=path,
                files=files,
                total_count=len(files),
                execution_time=result.execution_time,
            )

        except Exception as e:
            self.logger.error(f"Directory listing failed: {e}")
            raise RuntimeError(f"Directory listing failed: {e}")

    def _parse_ls_line(self, line: str, base_path: str) -> Optional[FileInfo]:
        """Parse a line from ls -la output"""
        try:
            parts = line.split()
            if len(parts) < 9:
                return None

            permissions = parts[0]
            owner = parts[2]
            group = parts[3]
            size = int(parts[4])

            # Handle dates (various formats)
            date_parts = parts[5:8]
            if len(date_parts) == 3:
                date_str = " ".join(date_parts)
            else:
                date_str = parts[5]

            # Filename (handle spaces in names)
            name = " ".join(parts[8:])

            # Determine file type
            file_type = FileType.FILE
            if permissions.startswith("d"):
                file_type = FileType.DIRECTORY
            elif permissions.startswith("l"):
                file_type = FileType.LINK
            elif permissions.startswith("c"):
                file_type = FileType.CHARACTER_DEVICE
            elif permissions.startswith("b"):
                file_type = FileType.BLOCK_DEVICE
            elif permissions.startswith("s"):
                file_type = FileType.SOCKET
            elif permissions.startswith("p"):
                file_type = FileType.FIFO

            # Handle symbolic links
            symlink_target = None
            if file_type == FileType.LINK and " -> " in name:
                name, symlink_target = name.split(" -> ", 1)

            return FileInfo(
                path=f"{base_path.rstrip('/')}/{name}",
                name=name,
                type=file_type,
                size=size,
                permissions=permissions,
                owner=owner,
                group=group,
                is_symlink=(file_type == FileType.LINK),
                symlink_target=symlink_target,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse ls line: {line} - {e}")
            return None

    async def cleanup(self):
        """Clean up all connections"""
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)

        self.logger.info("All connections cleaned up")

    def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection info by ID"""
        return self.connections.get(connection_id)

    def list_connections(self) -> List[ConnectionInfo]:
        """List all active connections"""
        return list(self.connections.values())


# Global connection manager instance
_connection_manager: Optional[SSHConnectionManager] = None


def get_connection_manager() -> SSHConnectionManager:
    """Get global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = SSHConnectionManager()
    return _connection_manager
