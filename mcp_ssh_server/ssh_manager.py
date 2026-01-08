"""
SSH 连接管理器

管理 SSH 连接的建立、维护、断开等操作，
支持连接池和会话保持。
"""

import paramiko
import threading
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SSHConfig:
    """SSH 连接配置"""

    host: str
    username: str
    port: int = 22
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: int = 30
    keepalive_interval: int = 60


class SSHConnection:
    """SSH 连接封装"""

    def __init__(self, config: SSHConfig):
        self.config = config
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self.last_activity = time.time()
        self.is_connected = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """建立 SSH 连接"""
        try:
            with self._lock:
                if self.is_connected:
                    return True

                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                connect_kwargs = {
                    "hostname": self.config.host,
                    "port": self.config.port,
                    "username": self.config.username,
                    "timeout": self.config.timeout,
                }

                if self.config.password:
                    connect_kwargs["password"] = self.config.password
                elif self.config.key_filename:
                    connect_kwargs["key_filename"] = self.config.key_filename

                self.client.connect(**connect_kwargs)
                self.sftp = self.client.open_sftp()
                self.is_connected = True
                self.last_activity = time.time()

                logger.info(
                    f"SSH 连接建立成功: {self.config.username}@{self.config.host}"
                )
                return True

        except Exception as e:
            logger.error(f"SSH 连接失败: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """断开 SSH 连接"""
        try:
            with self._lock:
                if self.sftp:
                    self.sftp.close()
                    self.sftp = None

                if self.client:
                    self.client.close()
                    self.client = None

                self.is_connected = False
                logger.info(
                    f"SSH 连接已断开: {self.config.username}@{self.config.host}"
                )

        except Exception as e:
            logger.error(f"断开 SSH 连接时出错: {e}")

    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行远程命令"""
        if not self.is_connected or not self.client:
            return {"success": False, "error": "SSH 连接未建立"}

        try:
            with self._lock:
                self.last_activity = time.time()

                stdin, stdout, stderr = self.client.exec_command(
                    command, timeout=timeout
                )

                exit_code = stdout.channel.recv_exit_status()
                stdout_content = stdout.read().decode("utf-8", errors="replace")
                stderr_content = stderr.read().decode("utf-8", errors="replace")

                return {
                    "success": exit_code == 0,
                    "exit_code": exit_code,
                    "stdout": stdout_content,
                    "stderr": stderr_content,
                    "command": command,
                }

        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            return {"success": False, "error": str(e), "command": command}

    def keep_alive(self):
        """保持连接活跃"""
        if self.is_connected and self.client:
            try:
                self.client.exec_command('echo "keepalive"', timeout=5)
                self.last_activity = time.time()
            except Exception as e:
                logger.warning(f"保持连接活跃失败: {e}")
                self.is_connected = False

    def upload_file(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """上传文件到远程服务器"""
        if not self.is_connected or not self.sftp:
            return {"success": False, "error": "SSH 连接未建立"}

        try:
            with self._lock:
                self.last_activity = time.time()
                self.sftp.put(local_path, remote_path)
                logger.info(f"文件上传成功: {local_path} -> {remote_path}")
                return {"success": True, "local_path": local_path, "remote_path": remote_path}
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return {"success": False, "error": str(e), "local_path": local_path, "remote_path": remote_path}

    def download_file(self, remote_path: str, local_path: str) -> Dict[str, Any]:
        """从远程服务器下载文件"""
        if not self.is_connected or not self.sftp:
            return {"success": False, "error": "SSH 连接未建立"}

        try:
            with self._lock:
                self.last_activity = time.time()
                self.sftp.get(remote_path, local_path)
                logger.info(f"文件下载成功: {remote_path} -> {local_path}")
                return {"success": True, "remote_path": remote_path, "local_path": local_path}
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return {"success": False, "error": str(e), "remote_path": remote_path, "local_path": local_path}

    def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """列出远程目录内容"""
        if not self.is_connected or not self.sftp:
            return {"success": False, "error": "SSH 连接未建立"}

        try:
            with self._lock:
                self.last_activity = time.time()
                files = []
                for item in self.sftp.listdir_attr(path):
                    file_info = {
                        "name": item.filename,
                        "type": "directory" if item.st_mode is not None and (item.st_mode & 0o040000) != 0 else "file",
                        "size": item.st_size or 0,
                        "permissions": oct(item.st_mode)[-3:] if item.st_mode else "",
                        "modified": item.st_mtime or 0,
                    }
                    files.append(file_info)
                
                logger.info(f"目录列表获取成功: {path}")
                return {"success": True, "path": path, "files": files}
        except Exception as e:
            logger.error(f"获取目录列表失败: {e}")
            return {"success": False, "error": str(e), "path": path}

    def create_shell(self, term: str = "xterm") -> Dict[str, Any]:
        """创建交互式 shell"""
        if not self.is_connected or not self.client:
            return {"success": False, "error": "SSH 连接未建立"}

        try:
            with self._lock:
                self.last_activity = time.time()
                
                # 创建交互式 shell 会话
                shell = self.client.invoke_shell(term=term)
                
                logger.info(f"交互式 shell 创建成功: {self.config.username}@{self.config.host}")
                return {
                    "success": True,
                    "shell": shell,
                    "term": term,
                    "host": self.config.host,
                    "username": self.config.username
                }
        except Exception as e:
            logger.error(f"创建交互式 shell 失败: {e}")
            return {"success": False, "error": str(e)}

    def send_shell_command(self, shell, command: str) -> Dict[str, Any]:
        """在交互式 shell 中发送命令"""
        if not self.is_connected or not shell:
            return {"success": False, "error": "Shell 未建立"}

        try:
            with self._lock:
                self.last_activity = time.time()
                
                # 发送命令
                shell.send(command + "\n")
                
                # 等待输出
                output = ""
                while not shell.recv_ready():
                    time.sleep(0.1)
                
                # 读取输出
                while shell.recv_ready():
                    output += shell.recv(1024).decode("utf-8", errors="replace")
                    time.sleep(0.1)
                
                logger.info(f"Shell 命令发送成功: {command}")
                return {
                    "success": True,
                    "command": command,
                    "output": output
                }
        except Exception as e:
            logger.error(f"Shell 命令发送失败: {e}")
            return {"success": False, "error": str(e), "command": command}

    def close_shell(self, shell) -> Dict[str, Any]:
        """关闭交互式 shell"""
        try:
            with self._lock:
                if shell:
                    shell.close()
                    logger.info("交互式 shell 已关闭")
                return {"success": True}
        except Exception as e:
            logger.error(f"关闭 shell 失败: {e}")
            return {"success": False, "error": str(e)}


class SSHConnectionManager:
    """SSH 连接管理器"""

    def __init__(self):
        self.connections: Dict[str, SSHConnection] = {}
        self._lock = threading.Lock()
        self._keepalive_thread = None
        self._keepalive_running = False

    def add_connection(self, name: str, config: SSHConfig) -> bool:
        """添加 SSH 连接"""
        try:
            with self._lock:
                if name in self.connections:
                    logger.warning(f"连接 {name} 已存在，先断开旧连接")
                    self.connections[name].disconnect()

                connection = SSHConnection(config)
                if connection.connect():
                    self.connections[name] = connection
                    self._start_keepalive()
                    return True
                else:
                    return False

        except Exception as e:
            logger.error(f"添加连接失败: {e}")
            return False

    def remove_connection(self, name: str):
        """移除 SSH 连接"""
        try:
            with self._lock:
                if name in self.connections:
                    self.connections[name].disconnect()
                    del self.connections[name]
                    logger.info(f"连接 {name} 已移除")

        except Exception as e:
            logger.error(f"移除连接失败: {e}")

    def get_connection(self, name: str) -> Optional[SSHConnection]:
        """获取 SSH 连接"""
        with self._lock:
            return self.connections.get(name)

    def list_connections(self) -> Dict[str, Dict[str, Any]]:
        """列出所有连接状态"""
        with self._lock:
            result = {}
            for name, conn in self.connections.items():
                result[name] = {
                    "host": conn.config.host,
                    "username": conn.config.username,
                    "is_connected": conn.is_connected,
                    "last_activity": conn.last_activity,
                }
            return result

    def execute_command(
        self, connection_name: str, command: str, timeout: int = 30
    ) -> Dict[str, Any]:
        """在指定连接上执行命令"""
        connection = self.get_connection(connection_name)
        if not connection:
            return {"success": False, "error": f"连接 {connection_name} 不存在"}

        return connection.execute_command(command, timeout)

    def upload_file(self, connection_name: str, local_path: str, remote_path: str) -> Dict[str, Any]:
        """上传文件到指定连接"""
        connection = self.get_connection(connection_name)
        if not connection:
            return {"success": False, "error": f"连接 {connection_name} 不存在"}

        return connection.upload_file(local_path, remote_path)

    def download_file(self, connection_name: str, remote_path: str, local_path: str) -> Dict[str, Any]:
        """从指定连接下载文件"""
        connection = self.get_connection(connection_name)
        if not connection:
            return {"success": False, "error": f"连接 {connection_name} 不存在"}

        return connection.download_file(remote_path, local_path)

    def list_directory(self, connection_name: str, path: str = ".") -> Dict[str, Any]:
        """列出指定连接的目录内容"""
        connection = self.get_connection(connection_name)
        if not connection:
            return {"success": False, "error": f"连接 {connection_name} 不存在"}

        return connection.list_directory(path)

    def create_shell(self, connection_name: str, term: str = "xterm") -> Dict[str, Any]:
        """在指定连接上创建交互式 shell"""
        connection = self.get_connection(connection_name)
        if not connection:
            return {"success": False, "error": f"连接 {connection_name} 不存在"}

        return connection.create_shell(term)

    def send_shell_command(self, connection_name: str, shell, command: str) -> Dict[str, Any]:
        """在指定连接的 shell 中发送命令"""
        connection = self.get_connection(connection_name)
        if not connection:
            return {"success": False, "error": f"连接 {connection_name} 不存在"}

        return connection.send_shell_command(shell, command)

    def close_shell(self, connection_name: str, shell) -> Dict[str, Any]:
        """关闭指定连接的 shell"""
        connection = self.get_connection(connection_name)
        if not connection:
            return {"success": False, "error": f"连接 {connection_name} 不存在"}

        return connection.close_shell(shell)

    def _start_keepalive(self):
        """启动保持连接活跃的线程"""
        if not self._keepalive_running:
            self._keepalive_running = True
            self._keepalive_thread = threading.Thread(
                target=self._keepalive_worker, daemon=True
            )
            self._keepalive_thread.start()

    def _keepalive_worker(self):
        """保持连接活跃的工作线程"""
        while self._keepalive_running:
            try:
                with self._lock:
                    for conn in list(self.connections.values()):
                        if conn.is_connected:
                            conn.keep_alive()

                time.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logger.error(f"保持连接活跃时出错: {e}")
                time.sleep(10)

    def shutdown(self):
        """关闭所有连接"""
        self._keepalive_running = False

        with self._lock:
            for conn in self.connections.values():
                conn.disconnect()
            self.connections.clear()

        if self._keepalive_thread and self._keepalive_thread.is_alive():
            self._keepalive_thread.join(timeout=5)

        logger.info("SSH 连接管理器已关闭")
