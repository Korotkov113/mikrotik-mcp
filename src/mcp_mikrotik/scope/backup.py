import base64
import time
from typing import Literal, Optional

from mcp.server.fastmcp import Context

from ..app import mcp, READ, WRITE, DANGEROUS
from ..connector import execute_mikrotik_command, sftp_read_file, sftp_write_file


@mcp.tool(name="create_backup", annotations=WRITE)
async def mikrotik_create_backup(
    ctx: Context,
    name: Optional[str] = None,
    dont_encrypt: bool = False,
) -> str:
    """
    Creates a system backup on MikroTik device.

    Args:
        name: Backup filename (without extension). If not specified, uses timestamp
        dont_encrypt: Don't encrypt the backup file

    Returns:
        Command output or error message
    """
    if not name:
        name = f"backup_{int(time.time())}"

    await ctx.info(f"Creating backup: name={name}")

    cmd = f"/system backup save name={name}"
    if dont_encrypt:
        cmd += " dont-encrypt=yes"
    else:
        cmd += ' password=""'

    result = await execute_mikrotik_command(cmd, ctx)

    file_cmd = f"/file print detail where name={name}.backup"
    file_details = await execute_mikrotik_command(file_cmd, ctx)

    if file_details and file_details.strip():
        return f"Backup created successfully:\n\n{file_details}"
    return f"Backup '{name}.backup' created. Output: {result}"


@mcp.tool(name="list_backups", annotations=READ)
async def mikrotik_list_backups(
    ctx: Context,
    name_filter: Optional[str] = None,
    include_exports: bool = False,
) -> str:
    """
    Lists backup files on MikroTik device.

    Args:
        name_filter: Filter by filename (partial match)
        include_exports: Also list export (.rsc) files

    Returns:
        List of backup files
    """
    if include_exports:
        cmd = "/file print where (type=backup or type=script)"
    else:
        cmd = "/file print where type=backup"

    if name_filter:
        if include_exports:
            cmd = f'/file print where (type=backup or type=script) and name~"{name_filter}"'
        else:
            cmd = f'/file print where type=backup and name~"{name_filter}"'

    result = await execute_mikrotik_command(cmd, ctx)

    if not result or result.strip() == "" or "no such item" in result.lower():
        return "No backup files found."

    return f"BACKUP FILES:\n\n{result}"


@mcp.tool(name="create_export", annotations=READ)
async def mikrotik_create_export(
    ctx: Context,
    name: Optional[str] = None,
    compact: bool = False,
    verbose: bool = False,
    hide_sensitive: bool = True,
) -> str:
    """
    Creates a full configuration export on MikroTik device.

    Args:
        name: Export filename (without extension). If not specified, uses timestamp
        compact: Use compact export format
        verbose: Include default values in export
        hide_sensitive: Hide sensitive information

    Returns:
        Command output or error message
    """
    if not name:
        name = f"export_{int(time.time())}"

    cmd = f"/export file={name}"
    if verbose:
        cmd += " verbose"
    if compact:
        cmd += " compact"
    if not hide_sensitive:
        cmd += " show-sensitive"

    await execute_mikrotik_command(cmd, ctx)

    file_cmd = f"/file print detail where name={name}.rsc"
    file_details = await execute_mikrotik_command(file_cmd, ctx)

    if file_details and file_details.strip():
        return f"Export created successfully:\n\n{file_details}"
    return f"Export '{name}.rsc' created successfully."


@mcp.tool(name="export_section", annotations=READ)
async def mikrotik_export_section(
    ctx: Context,
    section: str,
    compact: bool = False,
    hide_sensitive: bool = True,
) -> str:
    """
    Exports a specific configuration section and returns its content inline.

    Args:
        section: Section path (e.g. 'ip address', 'ip firewall mangle',
                 'routing bgp', 'interface', 'system')
        compact: Use compact export format
        hide_sensitive: Hide sensitive information

    Returns:
        Section configuration content
    """
    clean_section = section.replace(" ", "_").replace("/", "_")
    name = f"export_{clean_section}_{int(time.time())}"

    cmd = f"/{section} export file={name}"
    if compact:
        cmd += " compact"
    if not hide_sensitive:
        cmd += " show-sensitive"

    await execute_mikrotik_command(cmd, ctx)

    # Read the file content back via SFTP
    remote_path = f"{name}.rsc"
    try:
        content_bytes = await sftp_read_file(remote_path, ctx)
        content = content_bytes.decode("utf-8")

        # Clean up the export file
        await execute_mikrotik_command(f"/file remove {remote_path}", ctx)

        if content.strip():
            return content
        return f"Section '{section}' is empty or has only defaults."
    except Exception as e:
        # Fallback: return file metadata
        file_cmd = f"/file print detail where name={remote_path}"
        file_details = await execute_mikrotik_command(file_cmd, ctx)
        return (
            f"Section exported to '{remote_path}' but could not read content "
            f"({e}).\n\nFile details:\n{file_details}"
        )


@mcp.tool(name="download_file", annotations=READ)
async def mikrotik_download_file(
    ctx: Context,
    filename: str,
) -> str:
    """
    Downloads a file from MikroTik device via SFTP.

    Args:
        filename: Name of the file to download

    Returns:
        Base64-encoded file content prefixed with FILE_CONTENT_BASE64:
    """
    # Check if file exists
    check_cmd = f'/file print count-only where name="{filename}"'
    count = await execute_mikrotik_command(check_cmd, ctx)

    if count.strip() == "0":
        return f"File '{filename}' not found."

    try:
        data = await sftp_read_file(filename, ctx)
        encoded = base64.b64encode(data).decode("utf-8")
        return f"FILE_CONTENT_BASE64:{encoded}"
    except Exception as e:
        return f"Failed to download file '{filename}': {e}"


@mcp.tool(name="upload_file", annotations=WRITE)
async def mikrotik_upload_file(
    ctx: Context,
    filename: str,
    content_base64: str,
) -> str:
    """
    Uploads a file to MikroTik device via SFTP.

    Args:
        filename: Name for the uploaded file
        content_base64: Base64-encoded file content

    Returns:
        Upload result
    """
    try:
        data = base64.b64decode(content_base64)
    except Exception as e:
        return f"Failed to decode base64 content: {e}"

    try:
        await sftp_write_file(filename, data, ctx)
    except Exception as e:
        return f"Failed to upload file '{filename}': {e}"

    # Verify the file exists
    check_cmd = f'/file print detail where name="{filename}"'
    file_details = await execute_mikrotik_command(check_cmd, ctx)

    if file_details and file_details.strip():
        return f"File '{filename}' uploaded successfully:\n\n{file_details}"
    return f"File '{filename}' uploaded successfully ({len(data)} bytes)."


@mcp.tool(name="import_configuration", annotations=DANGEROUS)
async def mikrotik_import_configuration(
    ctx: Context,
    filename: str,
    verbose: bool = False,
) -> str:
    """
    Imports a configuration script (.rsc file).

    Args:
        filename: Script filename to import
        verbose: Show verbose output during import

    Returns:
        Import result
    """
    check_cmd = f'/file print count-only where name="{filename}"'
    count = await execute_mikrotik_command(check_cmd, ctx)

    if count.strip() == "0":
        return f"Configuration file '{filename}' not found."

    cmd = f"/import file={filename}"
    if verbose:
        cmd += " verbose=yes"

    result = await execute_mikrotik_command(cmd, ctx)

    if not result.strip() or "successfully" in result.lower():
        return f"Configuration '{filename}' imported successfully."
    return f"Import result:\n{result}"


@mcp.tool(name="restore_backup", annotations=DANGEROUS)
async def mikrotik_restore_backup(
    ctx: Context,
    filename: str,
    password: Optional[str] = None,
) -> str:
    """
    Restores a system backup on MikroTik device. Device will reboot.

    Args:
        filename: Backup filename to restore
        password: Password for encrypted backup

    Returns:
        Restore result
    """
    check_cmd = f'/file print count-only where name="{filename}"'
    count = await execute_mikrotik_command(check_cmd, ctx)

    if count.strip() == "0":
        return f"Backup file '{filename}' not found."

    cmd = f"/system backup load name={filename}"
    if password:
        cmd += f' password="{password}"'

    result = await execute_mikrotik_command(cmd, ctx)

    if "Restoring" in result or not result.strip():
        return f"Backup '{filename}' restored. System will reboot."
    return f"Failed to restore backup: {result}"


@mcp.tool(name="remove_file", annotations=DANGEROUS)
async def mikrotik_remove_file(ctx: Context, filename: str) -> str:
    """
    Removes a file from MikroTik device.

    Args:
        filename: Name of the file to remove

    Returns:
        Removal result
    """
    check_cmd = f'/file print count-only where name="{filename}"'
    count = await execute_mikrotik_command(check_cmd, ctx)

    if count.strip() == "0":
        return f"File '{filename}' not found."

    cmd = f"/file remove {filename}"
    result = await execute_mikrotik_command(cmd, ctx)

    if not result.strip():
        return f"File '{filename}' removed successfully."
    return f"Failed to remove file: {result}"


@mcp.tool(name="backup_info", annotations=READ)
async def mikrotik_backup_info(ctx: Context, filename: str) -> str:
    """
    Gets detailed information about a backup file.

    Args:
        filename: Backup filename

    Returns:
        File details
    """
    cmd = f'/file print detail where name="{filename}"'
    result = await execute_mikrotik_command(cmd, ctx)

    if not result or not result.strip():
        return f"Backup file '{filename}' not found."

    return f"BACKUP FILE DETAILS:\n\n{result}"
