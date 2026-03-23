from typing import Optional
from mcp.server.fastmcp import Context
from ..app import mcp, READ, WRITE, WRITE_IDEMPOTENT, DESTRUCTIVE
from ..connector import execute_mikrotik_command


# ── BGP ──────────────────────────────────────────────────────────────


@mcp.tool(name="list_bgp_sessions", annotations=READ)
async def mikrotik_list_bgp_sessions(ctx: Context) -> str:
    """Lists all BGP sessions with status."""
    result = await execute_mikrotik_command("/routing bgp session print detail", ctx)
    if not result or not result.strip():
        return "No BGP sessions found."
    return f"BGP SESSIONS:\n\n{result}"


@mcp.tool(name="list_bgp_connections", annotations=READ)
async def mikrotik_list_bgp_connections(ctx: Context) -> str:
    """Lists all BGP connection configurations."""
    result = await execute_mikrotik_command("/routing bgp connection print detail", ctx)
    if not result or not result.strip():
        return "No BGP connections configured."
    return f"BGP CONNECTIONS:\n\n{result}"


@mcp.tool(name="list_bgp_templates", annotations=READ)
async def mikrotik_list_bgp_templates(ctx: Context) -> str:
    """Lists all BGP templates."""
    result = await execute_mikrotik_command("/routing bgp template print detail", ctx)
    if not result or not result.strip():
        return "No BGP templates configured."
    return f"BGP TEMPLATES:\n\n{result}"


@mcp.tool(name="list_bgp_instances", annotations=READ)
async def mikrotik_list_bgp_instances(ctx: Context) -> str:
    """Lists all BGP instances."""
    result = await execute_mikrotik_command("/routing bgp instance print detail", ctx)
    if not result or not result.strip():
        return "No BGP instances configured."
    return f"BGP INSTANCES:\n\n{result}"


@mcp.tool(name="get_bgp_advertisements", annotations=READ)
async def mikrotik_get_bgp_advertisements(
    ctx: Context,
    session: Optional[str] = None,
) -> str:
    """
    Lists BGP advertisements (received/sent prefixes).

    Args:
        session: Filter by session name (optional)
    """
    cmd = "/routing bgp advertisements print"
    if session:
        cmd += f' where session="{session}"'

    result = await execute_mikrotik_command(cmd, ctx)
    if not result or not result.strip():
        return "No BGP advertisements found."
    return f"BGP ADVERTISEMENTS:\n\n{result}"


@mcp.tool(name="add_bgp_connection", annotations=WRITE)
async def mikrotik_add_bgp_connection(
    ctx: Context,
    name: str,
    remote_address: str,
    remote_as: int,
    instance: str = "default",
    local_role: str = "ebgp",
    routing_table: str = "main",
    templates: Optional[str] = None,
    hold_time: Optional[str] = None,
    keepalive_time: Optional[str] = None,
    multihop: bool = False,
    disabled: bool = False,
    comment: Optional[str] = None,
) -> str:
    """
    Creates a new BGP connection (peer).

    Args:
        name: Connection name
        remote_address: Remote peer address (e.g. '10.0.0.1/32')
        remote_as: Remote AS number
        instance: BGP instance name
        local_role: Local role (ebgp, ibgp)
        routing_table: Routing table for received routes
        templates: BGP template name to apply
        hold_time: Hold time (e.g. '4m', '30s')
        keepalive_time: Keepalive time (e.g. '1m', '10s')
        multihop: Enable multihop
        disabled: Create in disabled state
        comment: Optional comment
    """
    cmd = (
        f"/routing bgp connection add name={name}"
        f" remote.address={remote_address} .as={remote_as}"
        f" local.role={local_role}"
        f" instance={instance}"
        f" routing-table={routing_table}"
    )

    if templates:
        cmd += f" templates={templates}"
    if hold_time:
        cmd += f" hold-time={hold_time}"
    if keepalive_time:
        cmd += f" keepalive-time={keepalive_time}"
    if multihop:
        cmd += " multihop=yes"
    if disabled:
        cmd += " disabled=yes"
    if comment:
        cmd += f' comment="{comment}"'

    result = await execute_mikrotik_command(cmd, ctx)

    details = await execute_mikrotik_command(
        f'/routing bgp connection print detail where name="{name}"', ctx
    )
    if details and details.strip():
        return f"BGP connection created:\n\n{details}"
    return f"BGP connection add result: {result}"


@mcp.tool(name="remove_bgp_connection", annotations=DESTRUCTIVE)
async def mikrotik_remove_bgp_connection(ctx: Context, name: str) -> str:
    """
    Removes a BGP connection by name.

    Args:
        name: BGP connection name to remove
    """
    cmd = f'/routing bgp connection remove [find name="{name}"]'
    result = await execute_mikrotik_command(cmd, ctx)

    if "no such item" in result.lower():
        return f"BGP connection '{name}' not found."
    return f"BGP connection '{name}' removed."


@mcp.tool(name="enable_bgp_connection", annotations=WRITE_IDEMPOTENT)
async def mikrotik_enable_bgp_connection(ctx: Context, name: str) -> str:
    """Enables a BGP connection by name."""
    cmd = f'/routing bgp connection set [find name="{name}"] disabled=no'
    await execute_mikrotik_command(cmd, ctx)
    return f"BGP connection '{name}' enabled."


@mcp.tool(name="disable_bgp_connection", annotations=WRITE_IDEMPOTENT)
async def mikrotik_disable_bgp_connection(ctx: Context, name: str) -> str:
    """Disables a BGP connection by name."""
    cmd = f'/routing bgp connection set [find name="{name}"] disabled=yes'
    await execute_mikrotik_command(cmd, ctx)
    return f"BGP connection '{name}' disabled."


@mcp.tool(name="add_bgp_template", annotations=WRITE)
async def mikrotik_add_bgp_template(
    ctx: Context,
    name: str,
    as_number: int,
    routing_table: str = "main",
    input_filter: Optional[str] = None,
    output_filter: Optional[str] = None,
    hold_time: Optional[str] = None,
    keepalive_time: Optional[str] = None,
    multihop: bool = False,
) -> str:
    """
    Creates a new BGP template.

    Args:
        name: Template name
        as_number: AS number
        routing_table: Routing table
        input_filter: Input routing filter chain name
        output_filter: Output routing filter chain name
        hold_time: Hold time
        keepalive_time: Keepalive time
        multihop: Enable multihop
    """
    cmd = f"/routing bgp template add name={name} as={as_number} routing-table={routing_table}"

    if input_filter:
        cmd += f" input.filter={input_filter}"
    if output_filter:
        cmd += f" output.filter={output_filter}"
    if hold_time:
        cmd += f" hold-time={hold_time}"
    if keepalive_time:
        cmd += f" keepalive-time={keepalive_time}"
    if multihop:
        cmd += " multihop=yes"

    result = await execute_mikrotik_command(cmd, ctx)

    details = await execute_mikrotik_command(
        f'/routing bgp template print detail where name="{name}"', ctx
    )
    if details and details.strip():
        return f"BGP template created:\n\n{details}"
    return f"BGP template add result: {result}"


@mcp.tool(name="remove_bgp_template", annotations=DESTRUCTIVE)
async def mikrotik_remove_bgp_template(ctx: Context, name: str) -> str:
    """Removes a BGP template by name."""
    cmd = f'/routing bgp template remove [find name="{name}"]'
    result = await execute_mikrotik_command(cmd, ctx)

    if "no such item" in result.lower():
        return f"BGP template '{name}' not found."
    return f"BGP template '{name}' removed."


# ── Routing Filter Rules ─────────────────────────────────────────────


@mcp.tool(name="list_routing_filters", annotations=READ)
async def mikrotik_list_routing_filters(
    ctx: Context,
    chain: Optional[str] = None,
) -> str:
    """
    Lists routing filter rules.

    Args:
        chain: Filter by chain name (optional)
    """
    cmd = "/routing filter rule print detail"
    if chain:
        cmd += f' where chain="{chain}"'

    result = await execute_mikrotik_command(cmd, ctx)
    if not result or not result.strip():
        return "No routing filter rules found."
    return f"ROUTING FILTER RULES:\n\n{result}"


@mcp.tool(name="add_routing_filter", annotations=WRITE)
async def mikrotik_add_routing_filter(
    ctx: Context,
    chain: str,
    rule: str,
    disabled: bool = False,
    comment: Optional[str] = None,
) -> str:
    """
    Adds a routing filter rule.

    Args:
        chain: Filter chain name (e.g. 'bgp_in', 'ospf_out')
        rule: RouterOS filter rule expression
              (e.g. 'set gw 10.0.7.4; accept;' or 'if (dst == 1.2.3.0/24) { reject }')
        disabled: Create disabled
        comment: Optional comment
    """
    cmd = f'/routing filter rule add chain={chain} rule="{rule}"'
    if disabled:
        cmd += " disabled=yes"
    if comment:
        cmd += f' comment="{comment}"'

    result = await execute_mikrotik_command(cmd, ctx)

    details = await execute_mikrotik_command(
        f'/routing filter rule print detail where chain="{chain}"', ctx
    )
    if details and details.strip():
        return f"Routing filter rule added:\n\n{details}"
    return f"Routing filter rule add result: {result}"


@mcp.tool(name="remove_routing_filters", annotations=DESTRUCTIVE)
async def mikrotik_remove_routing_filters(
    ctx: Context,
    chain: str,
) -> str:
    """
    Removes all routing filter rules in a chain.

    Args:
        chain: Chain name to remove all rules from
    """
    cmd = f'/routing filter rule remove [find chain="{chain}"]'
    result = await execute_mikrotik_command(cmd, ctx)

    if "no such item" in result.lower():
        return f"No routing filter rules found in chain '{chain}'."
    return f"All routing filter rules in chain '{chain}' removed."


# ── Routing Tables ───────────────────────────────────────────────────


@mcp.tool(name="list_routing_tables", annotations=READ)
async def mikrotik_list_routing_tables(ctx: Context) -> str:
    """Lists all routing tables."""
    result = await execute_mikrotik_command("/routing table print detail", ctx)
    if not result or not result.strip():
        return "No routing tables configured (only main)."
    return f"ROUTING TABLES:\n\n{result}"


@mcp.tool(name="add_routing_table", annotations=WRITE)
async def mikrotik_add_routing_table(
    ctx: Context,
    name: str,
    fib: bool = True,
) -> str:
    """
    Creates a new routing table.

    Args:
        name: Table name
        fib: Create FIB for this table (required for actual forwarding)
    """
    cmd = f"/routing table add name={name}"
    if fib:
        cmd += " fib"

    result = await execute_mikrotik_command(cmd, ctx)

    details = await execute_mikrotik_command(
        f'/routing table print detail where name="{name}"', ctx
    )
    if details and details.strip():
        return f"Routing table created:\n\n{details}"
    return f"Routing table add result: {result}"
