import asyncio
import logging
from typing import Optional, Tuple

from mcp.server.fastmcp import Context

from .config import DeviceConfig
from .devices import NoDevicesConfiguredError, device_manager
from .mikrotik_ssh_client import MikroTikSSHClient

logger = logging.getLogger(__name__)


def _resolve_device(device: Optional[DeviceConfig]) -> Tuple[str, DeviceConfig]:
    if device is not None:
        return device.host, device
    return device_manager.get_active()


def _get_client(device: DeviceConfig) -> MikroTikSSHClient:
    """Create a new SSH client instance for the given device."""
    return MikroTikSSHClient(
        host=device.host,
        username=device.username,
        password=device.password,
        key_filename=device.key_filename,
        port=device.port,
    )


def _execute_sync(command: str, device: Optional[DeviceConfig] = None) -> str:
    """Execute a MikroTik command via SSH and return the output (blocking)."""
    try:
        name, target = _resolve_device(device)
    except NoDevicesConfiguredError as e:
        return f"Error: {e}"

    logger.info(f"Executing MikroTik command on '{name}': {command}")

    ssh_client = _get_client(target)
    try:
        if not ssh_client.connect():
            return (
                f"Error: Failed to connect to MikroTik device "
                f"'{name}' ({target.host}:{target.port})"
            )

        result = ssh_client.execute_command(command)
        logger.info(f"Command result: {repr(result[:200])}")
        return result
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        logger.error(error_msg)
        return error_msg
    finally:
        ssh_client.disconnect()


def _sftp_read_sync(remote_path: str, device: Optional[DeviceConfig] = None) -> bytes:
    """Read a file from MikroTik via SFTP (blocking)."""
    name, target = _resolve_device(device)
    logger.info(f"SFTP reading from '{name}': {remote_path}")

    ssh_client = _get_client(target)
    try:
        if not ssh_client.connect():
            raise Exception(
                f"Failed to connect to MikroTik device '{name}' "
                f"({target.host}:{target.port})"
            )
        return ssh_client.sftp_read(remote_path)
    finally:
        ssh_client.disconnect()


def _sftp_write_sync(
    remote_path: str, data: bytes, device: Optional[DeviceConfig] = None
) -> None:
    """Write a file to MikroTik via SFTP (blocking)."""
    name, target = _resolve_device(device)
    logger.info(f"SFTP writing to '{name}': {remote_path} ({len(data)} bytes)")

    ssh_client = _get_client(target)
    try:
        if not ssh_client.connect():
            raise Exception(
                f"Failed to connect to MikroTik device '{name}' "
                f"({target.host}:{target.port})"
            )
        ssh_client.sftp_write(remote_path, data)
    finally:
        ssh_client.disconnect()


async def execute_mikrotik_command(
    command: str, ctx: Context, device: Optional[DeviceConfig] = None
) -> str:
    """Execute a MikroTik command on the active (or given) device via SSH."""
    await ctx.info(f"Executing MikroTik command: {command}")
    result = await asyncio.to_thread(_execute_sync, command, device)
    if result.startswith("Error"):
        await ctx.error(result)
    return result


async def sftp_read_file(
    remote_path: str, ctx: Context, device: Optional[DeviceConfig] = None
) -> bytes:
    """Read a file from MikroTik device via SFTP."""
    await ctx.info(f"SFTP reading: {remote_path}")
    return await asyncio.to_thread(_sftp_read_sync, remote_path, device)


async def sftp_write_file(
    remote_path: str, data: bytes, ctx: Context, device: Optional[DeviceConfig] = None
) -> None:
    """Write a file to MikroTik device via SFTP."""
    await ctx.info(f"SFTP writing: {remote_path}")
    await asyncio.to_thread(_sftp_write_sync, remote_path, data, device)
