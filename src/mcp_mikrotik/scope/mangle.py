from typing import Optional
from mcp.server.fastmcp import Context
from ..app import mcp, READ, WRITE, WRITE_IDEMPOTENT, DESTRUCTIVE
from ..connector import execute_mikrotik_command


@mcp.tool(name="list_mangle_rules", annotations=READ)
async def mikrotik_list_mangle_rules(
    ctx: Context,
    chain: Optional[str] = None,
    action: Optional[str] = None,
    disabled_only: bool = False,
) -> str:
    """
    Lists firewall mangle rules.

    Args:
        chain: Filter by chain (prerouting, input, forward, output, postrouting)
        action: Filter by action (mark-routing, mark-connection, mark-packet, etc.)
        disabled_only: Show only disabled rules
    """
    cmd = "/ip firewall mangle print"

    filters = []
    if chain:
        filters.append(f"chain={chain}")
    if action:
        filters.append(f"action={action}")
    if disabled_only:
        filters.append("disabled=yes")

    if filters:
        cmd += " where " + " ".join(filters)

    result = await execute_mikrotik_command(cmd, ctx)
    if not result or not result.strip() or "no such item" in result.lower():
        return "No mangle rules found."
    return f"MANGLE RULES:\n\n{result}"


@mcp.tool(name="list_mangle_rules_detail", annotations=READ)
async def mikrotik_list_mangle_rules_detail(
    ctx: Context,
    chain: Optional[str] = None,
) -> str:
    """
    Lists firewall mangle rules with full detail.

    Args:
        chain: Filter by chain (optional)
    """
    cmd = "/ip firewall mangle print detail"
    if chain:
        cmd += f" where chain={chain}"

    result = await execute_mikrotik_command(cmd, ctx)
    if not result or not result.strip():
        return "No mangle rules found."
    return f"MANGLE RULES (detail):\n\n{result}"


@mcp.tool(name="add_mangle_rule", annotations=WRITE)
async def mikrotik_add_mangle_rule(
    ctx: Context,
    chain: str,
    action: str,
    new_routing_mark: Optional[str] = None,
    new_connection_mark: Optional[str] = None,
    new_packet_mark: Optional[str] = None,
    src_address: Optional[str] = None,
    dst_address: Optional[str] = None,
    src_address_list: Optional[str] = None,
    dst_address_list: Optional[str] = None,
    src_port: Optional[str] = None,
    dst_port: Optional[str] = None,
    protocol: Optional[str] = None,
    in_interface: Optional[str] = None,
    out_interface: Optional[str] = None,
    connection_mark: Optional[str] = None,
    routing_mark: Optional[str] = None,
    passthrough: Optional[bool] = None,
    comment: Optional[str] = None,
    disabled: bool = False,
    place_before: Optional[str] = None,
) -> str:
    """
    Creates a firewall mangle rule.

    Args:
        chain: Chain (prerouting, input, forward, output, postrouting)
        action: Action (mark-routing, mark-connection, mark-packet, accept, jump, etc.)
        new_routing_mark: New routing mark to set
        new_connection_mark: New connection mark to set
        new_packet_mark: New packet mark to set
        src_address: Source address
        dst_address: Destination address
        src_address_list: Source address list
        dst_address_list: Destination address list
        src_port: Source port
        dst_port: Destination port
        protocol: Protocol
        in_interface: Input interface
        out_interface: Output interface
        connection_mark: Match connection mark
        routing_mark: Match routing mark
        passthrough: Pass to next rule after matching
        comment: Comment
        disabled: Create disabled
        place_before: Place before rule number
    """
    cmd = f"/ip firewall mangle add chain={chain} action={action}"

    if new_routing_mark:
        cmd += f" new-routing-mark={new_routing_mark}"
    if new_connection_mark:
        cmd += f" new-connection-mark={new_connection_mark}"
    if new_packet_mark:
        cmd += f" new-packet-mark={new_packet_mark}"
    if src_address:
        cmd += f" src-address={src_address}"
    if dst_address:
        cmd += f" dst-address={dst_address}"
    if src_address_list:
        cmd += f' src-address-list="{src_address_list}"'
    if dst_address_list:
        cmd += f' dst-address-list="{dst_address_list}"'
    if src_port:
        cmd += f" src-port={src_port}"
    if dst_port:
        cmd += f" dst-port={dst_port}"
    if protocol:
        cmd += f" protocol={protocol}"
    if in_interface:
        cmd += f' in-interface="{in_interface}"'
    if out_interface:
        cmd += f' out-interface="{out_interface}"'
    if connection_mark:
        cmd += f" connection-mark={connection_mark}"
    if routing_mark:
        cmd += f" routing-mark={routing_mark}"
    if passthrough is not None:
        cmd += f' passthrough={"yes" if passthrough else "no"}'
    if comment:
        cmd += f' comment="{comment}"'
    if disabled:
        cmd += " disabled=yes"
    if place_before:
        cmd += f" place-before={place_before}"

    result = await execute_mikrotik_command(cmd, ctx)

    if result.strip() and ("*" in result or result.strip().isdigit()):
        rule_id = result.strip()
        details = await execute_mikrotik_command(
            f"/ip firewall mangle print detail where .id={rule_id}", ctx
        )
        if details and details.strip():
            return f"Mangle rule created:\n\n{details}"
        return f"Mangle rule created with ID: {rule_id}"

    if result.strip() and "failure" in result.lower():
        return f"Failed to create mangle rule: {result}"

    return f"Mangle rule created. Output: {result if result.strip() else '(ok)'}"


@mcp.tool(name="remove_mangle_rule", annotations=DESTRUCTIVE)
async def mikrotik_remove_mangle_rule(ctx: Context, rule_id: str) -> str:
    """
    Removes a mangle rule by ID.

    Args:
        rule_id: Rule ID (e.g. '*1' or '0')
    """
    check = await execute_mikrotik_command(
        f"/ip firewall mangle print count-only where .id={rule_id}", ctx
    )
    if check.strip() == "0":
        return f"Mangle rule '{rule_id}' not found."

    await execute_mikrotik_command(f"/ip firewall mangle remove {rule_id}", ctx)
    return f"Mangle rule '{rule_id}' removed."


@mcp.tool(name="enable_mangle_rule", annotations=WRITE_IDEMPOTENT)
async def mikrotik_enable_mangle_rule(ctx: Context, rule_id: str) -> str:
    """Enables a mangle rule by ID."""
    await execute_mikrotik_command(
        f"/ip firewall mangle set {rule_id} disabled=no", ctx
    )
    return f"Mangle rule '{rule_id}' enabled."


@mcp.tool(name="disable_mangle_rule", annotations=WRITE_IDEMPOTENT)
async def mikrotik_disable_mangle_rule(ctx: Context, rule_id: str) -> str:
    """Disables a mangle rule by ID."""
    await execute_mikrotik_command(
        f"/ip firewall mangle set {rule_id} disabled=yes", ctx
    )
    return f"Mangle rule '{rule_id}' disabled."
