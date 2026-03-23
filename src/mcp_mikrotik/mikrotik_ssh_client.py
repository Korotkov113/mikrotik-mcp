import io
import logging
from typing import Optional

import paramiko

logger = logging.getLogger(__name__)


class MikroTikSSHClient:
    """SSH client for MikroTik devices with command execution and SFTP support."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        key_filename: Optional[str],
        port: int = 22,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client: Optional[paramiko.SSHClient] = None
        self.key_filename = key_filename

    def connect(self) -> bool:
        """Establish SSH connection to MikroTik device."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                key_filename=self.key_filename,
                look_for_keys=False,
                allow_agent=False,
                timeout=10,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MikroTik: {e}")
            return False

    def execute_command(self, command: str) -> str:
        """Execute a command on MikroTik device."""
        if not self.client:
            raise Exception("Not connected to MikroTik device")

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)

            output = stdout.read().decode("utf-8")
            error = stderr.read().decode("utf-8")

            if error and not output:
                return error

            return output
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            raise

    def sftp_read(self, remote_path: str) -> bytes:
        """Read a file from the device via SFTP."""
        if not self.client:
            raise Exception("Not connected to MikroTik device")

        sftp = self.client.open_sftp()
        try:
            with sftp.open(remote_path, "rb") as f:
                return f.read()
        finally:
            sftp.close()

    def sftp_write(self, remote_path: str, data: bytes) -> None:
        """Write a file to the device via SFTP."""
        if not self.client:
            raise Exception("Not connected to MikroTik device")

        sftp = self.client.open_sftp()
        try:
            with sftp.open(remote_path, "wb") as f:
                f.write(data)
        finally:
            sftp.close()

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None
