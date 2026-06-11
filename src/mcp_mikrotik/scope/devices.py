from typing import Optional

from mcp.server.fastmcp import Context

from ..app import mcp, READ, WRITE, WRITE_IDEMPOTENT, DESTRUCTIVE
from ..config import DeviceConfig
from ..connector import execute_mikrotik_command
from ..devices import device_manager


def _format_device_line(d: dict) -> str:
    marker = "*" if d["active"] else " "
    desc = f" — {d['description']}" if d["description"] else ""
    return (
        f"{marker} {d['name']}: {d['username']}@{d['host']}:{d['port']} "
        f"[{d['auth']}]{desc}"
    )


@mcp.tool(name="list_devices", annotations=READ)
async def mikrotik_list_devices(ctx: Context) -> str:
    """
    List all configured MikroTik devices in the registry.

    The device marked with '*' is the active one — all other tools
    target it. Switch with use_device, add new ones with add_device.

    Returns:
        One device per line: name, user@host:port, auth method, description
    """
    devices = device_manager.list_devices()
    if not devices:
        return (
            "No devices configured. Add one with add_device "
            "(name, host, username, password or key_filename)."
        )
    return "\n".join(_format_device_line(d) for d in devices)


@mcp.tool(name="use_device", annotations=WRITE_IDEMPOTENT)
async def mikrotik_use_device(ctx: Context, name: str) -> str:
    """
    Switch the active MikroTik device. All subsequent tool calls
    (firewall, DNS, routes, backups, etc.) will target this device.

    Args:
        name: Device name as shown by list_devices

    Returns:
        Confirmation with the device's connection details
    """
    try:
        device = device_manager.set_active(name)
    except KeyError as e:
        return f"Error: {e.args[0]}"

    await ctx.info(f"Active device switched to '{name}'")
    return (
        f"Active device is now '{name}' "
        f"({device.username}@{device.host}:{device.port})"
    )


@mcp.tool(name="add_device", annotations=WRITE)
async def mikrotik_add_device(
    ctx: Context,
    name: str,
    host: str,
    username: str = "admin",
    password: str = "",
    port: int = 22,
    key_filename: Optional[str] = None,
    description: str = "",
    make_active: bool = False,
    save: bool = False,
) -> str:
    """
    Register a MikroTik device in the registry so tools can target it.

    Args:
        name: Short unique name for the device (e.g. 'office', 'home')
        host: IP address or hostname
        username: SSH username (default: admin)
        password: SSH password (omit when using key_filename)
        port: SSH port (default: 22)
        key_filename: Path to an SSH private key on the server machine
        description: Optional human-readable note
        make_active: Switch to this device immediately
        save: Persist the registry to the devices file so the device
              survives server restarts

    Returns:
        Confirmation message
    """
    device = DeviceConfig(
        host=host,
        username=username,
        password=password,
        port=port,
        key_filename=key_filename,
        description=description,
    )
    try:
        device_manager.add(name, device, persist=save)
    except ValueError as e:
        return f"Error: {e}"

    if make_active:
        device_manager.set_active(name)

    await ctx.info(f"Device '{name}' added ({host}:{port})")
    parts = [f"Device '{name}' added ({username}@{host}:{port})"]
    if make_active:
        parts.append("and set as active")
    if save:
        parts.append("(saved to devices file)")
    return " ".join(parts)


@mcp.tool(name="remove_device", annotations=DESTRUCTIVE)
async def mikrotik_remove_device(ctx: Context, name: str, save: bool = False) -> str:
    """
    Remove a device from the registry. Does not touch the device itself.

    Args:
        name: Device name as shown by list_devices
        save: Also persist the removal to the devices file

    Returns:
        Confirmation message; if the removed device was active, the new
        active device is reported
    """
    try:
        device_manager.remove(name, persist=save)
    except KeyError as e:
        return f"Error: {e.args[0]}"

    await ctx.info(f"Device '{name}' removed")
    try:
        active, _ = device_manager.get_active()
        return f"Device '{name}' removed. Active device: '{active}'"
    except Exception:
        return f"Device '{name}' removed. No devices left in the registry."


@mcp.tool(name="test_device_connection", annotations=READ)
async def mikrotik_test_device_connection(
    ctx: Context, name: Optional[str] = None
) -> str:
    """
    Test SSH connectivity to a device and return its identity and version.
    Does not change the active device.

    Args:
        name: Device to test (default: the active device)

    Returns:
        Device identity and RouterOS resource summary, or the connection error
    """
    if name is not None:
        try:
            device = device_manager.get(name)
        except KeyError as e:
            return f"Error: {e.args[0]}"
        label = name
    else:
        try:
            label, device = device_manager.get_active()
        except Exception as e:
            return f"Error: {e}"

    await ctx.info(f"Testing connection to '{label}' ({device.host}:{device.port})")

    identity = await execute_mikrotik_command("/system identity print", ctx, device)
    if identity.startswith("Error"):
        return f"Connection to '{label}' FAILED: {identity}"

    resource = await execute_mikrotik_command("/system resource print", ctx, device)
    return (
        f"Connection to '{label}' ({device.host}:{device.port}) OK\n\n"
        f"=== Identity ===\n{identity.strip()}\n\n"
        f"=== Resources ===\n{resource.strip()}"
    )
