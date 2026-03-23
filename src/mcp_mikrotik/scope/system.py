from typing import Optional
from mcp.server.fastmcp import Context
from ..app import mcp, READ, WRITE, DANGEROUS
from ..connector import execute_mikrotik_command


@mcp.tool(name="run_command", annotations=DANGEROUS)
async def mikrotik_run_command(
    ctx: Context,
    command: str,
) -> str:
    """
    Execute an arbitrary RouterOS CLI command and return the output.

    Use this tool when no dedicated tool exists for the operation you need,
    for example: BGP configuration, routing filters, mangle rules, scripting,
    system commands, or any other RouterOS CLI command.

    Args:
        command: Full RouterOS CLI command to execute
                 (e.g. '/routing bgp session print', '/ip firewall mangle print')

    Returns:
        Raw command output from the device
    """
    await ctx.info(f"Running command: {command}")
    result = await execute_mikrotik_command(command, ctx)

    if not result or not result.strip():
        return "(no output)"

    return result


@mcp.tool(name="run_script", annotations=DANGEROUS)
async def mikrotik_run_script(
    ctx: Context,
    script: str,
) -> str:
    """
    Execute a multi-line RouterOS script.

    Each line is executed as a separate command. Lines starting with '#'
    and empty lines are skipped. Results from all commands are concatenated.

    Args:
        script: Multi-line RouterOS script. Each line is one command.

    Returns:
        Combined output from all commands
    """
    lines = [
        line.strip()
        for line in script.strip().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not lines:
        return "No commands to execute."

    await ctx.info(f"Running script with {len(lines)} commands")

    results = []
    for i, line in enumerate(lines, 1):
        await ctx.info(f"[{i}/{len(lines)}] {line}")
        result = await execute_mikrotik_command(line, ctx)
        output = result.strip() if result else "(no output)"
        results.append(f">>> {line}\n{output}")

    return "\n\n".join(results)


@mcp.tool(name="get_system_info", annotations=READ)
async def mikrotik_get_system_info(ctx: Context) -> str:
    """
    Gets comprehensive system information: identity, resources, routerboard, version.

    Returns:
        Combined system information
    """
    commands = {
        "Identity": "/system identity print",
        "Resources": "/system resource print",
        "RouterBoard": "/system routerboard print",
        "Health": "/system health print",
    }

    results = []
    for label, cmd in commands.items():
        result = await execute_mikrotik_command(cmd, ctx)
        output = result.strip() if result else "(not available)"
        results.append(f"=== {label} ===\n{output}")

    return "\n\n".join(results)
