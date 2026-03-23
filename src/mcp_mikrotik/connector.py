import asyncio
import logging

from mcp.server.fastmcp import Context

from . import config
from .mikrotik_ssh_client import MikroTikSSHClient

logger = logging.getLogger(__name__)


def _get_client() -> MikroTikSSHClient:
    """Create a new SSH client instance with current config."""
    return MikroTikSSHClient(
        host=config.mikrotik_config.host,
        username=config.mikrotik_config.username,
        password=config.mikrotik_config.password,
        key_filename=config.mikrotik_config.key_filename,
        port=config.mikrotik_config.port,
    )


def _execute_sync(command: str) -> str:
    """Execute a MikroTik command via SSH and return the output (blocking)."""
    logger.info(f"Executing MikroTik command: {command}")

    ssh_client = _get_client()
    try:
        if not ssh_client.connect():
            return "Error: Failed to connect to MikroTik device"

        result = ssh_client.execute_command(command)
        logger.info(f"Command result: {repr(result[:200])}")
        return result
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        logger.error(error_msg)
        return error_msg
    finally:
        ssh_client.disconnect()


def _sftp_read_sync(remote_path: str) -> bytes:
    """Read a file from MikroTik via SFTP (blocking)."""
    logger.info(f"SFTP reading: {remote_path}")

    ssh_client = _get_client()
    try:
        if not ssh_client.connect():
            raise Exception("Failed to connect to MikroTik device")
        return ssh_client.sftp_read(remote_path)
    finally:
        ssh_client.disconnect()


def _sftp_write_sync(remote_path: str, data: bytes) -> None:
    """Write a file to MikroTik via SFTP (blocking)."""
    logger.info(f"SFTP writing: {remote_path} ({len(data)} bytes)")

    ssh_client = _get_client()
    try:
        if not ssh_client.connect():
            raise Exception("Failed to connect to MikroTik device")
        ssh_client.sftp_write(remote_path, data)
    finally:
        ssh_client.disconnect()


async def execute_mikrotik_command(command: str, ctx: Context) -> str:
    """Execute a MikroTik command via SSH and return the output."""
    await ctx.info(f"Executing MikroTik command: {command}")
    result = await asyncio.to_thread(_execute_sync, command)
    if result.startswith("Error"):
        await ctx.error(result)
    return result


async def sftp_read_file(remote_path: str, ctx: Context) -> bytes:
    """Read a file from MikroTik device via SFTP."""
    await ctx.info(f"SFTP reading: {remote_path}")
    return await asyncio.to_thread(_sftp_read_sync, remote_path)


async def sftp_write_file(remote_path: str, data: bytes, ctx: Context) -> None:
    """Write a file to MikroTik device via SFTP."""
    await ctx.info(f"SFTP writing: {remote_path}")
    await asyncio.to_thread(_sftp_write_sync, remote_path, data)
