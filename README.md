# MikroTik MCP

> Fork of [jeff-nasseri/mikrotik-mcp](https://github.com/jeff-nasseri/mikrotik-mcp) with extended functionality.

MCP server for managing MikroTik RouterOS devices via AI assistants (Claude Desktop, Claude Code, etc.)

## What's changed (vs upstream)

### New modules

- **`scope/routing.py`** — Full BGP management (sessions, connections, templates, instances, advertisements, routing filters, routing tables)
- **`scope/mangle.py`** — Firewall mangle rules (list, add, remove, enable/disable with full parameter support)

### New tools

| Tool | Module | Description |
|------|--------|-------------|
| `run_command` | `system` | Execute **any** RouterOS CLI command (no dedicated tool needed) |
| `list_bgp_sessions` | `routing` | List BGP sessions with status |
| `list_bgp_connections` | `routing` | List BGP connection configurations |
| `list_bgp_templates` | `routing` | List BGP templates |
| `list_bgp_instances` | `routing` | List BGP instances |
| `get_bgp_advertisements` | `routing` | List BGP advertisements (prefixes) |
| `add_bgp_connection` | `routing` | Create BGP peer (AS, routing-table, multihop, hold-time, etc.) |
| `remove_bgp_connection` | `routing` | Remove BGP connection by name |
| `enable_bgp_connection` | `routing` | Enable BGP connection |
| `disable_bgp_connection` | `routing` | Disable BGP connection |
| `add_bgp_template` | `routing` | Create BGP template (AS, filters, timers) |
| `remove_bgp_template` | `routing` | Remove BGP template |
| `list_routing_filters` | `routing` | List routing filter rules (by chain) |
| `add_routing_filter` | `routing` | Add routing filter rule |
| `remove_routing_filters` | `routing` | Remove all rules in a filter chain |
| `list_routing_tables` | `routing` | List routing tables |
| `add_routing_table` | `routing` | Create routing table |
| `list_mangle_rules` | `mangle` | List mangle rules (filter by chain/action) |
| `list_mangle_rules_detail` | `mangle` | List mangle rules with full detail |
| `add_mangle_rule` | `mangle` | Create mangle rule (mark-routing, mark-connection, etc.) |
| `remove_mangle_rule` | `mangle` | Remove mangle rule by ID |
| `enable_mangle_rule` | `mangle` | Enable mangle rule |
| `disable_mangle_rule` | `mangle` | Disable mangle rule |

### Architecture changes

- **`connector.py`** — Added SFTP read/write support (`sftp_read_file`, `sftp_write_file`) for file operations on the device
- **`app.py`** — Added tool annotation constants (`READ`, `WRITE`, `WRITE_IDEMPOTENT`, `DESTRUCTIVE`, `DANGEROUS`) for MCP tool hints; added `/health` endpoint
- **`mikrotik_ssh_client.py`** — Added `sftp_read()` and `sftp_write()` methods to the SSH client
- All scope modules updated to use tool annotations

### Existing tools (from upstream)

| Category | Tools |
|----------|-------|
| **System** | `get_system_info`, `run_command` |
| **Firewall** | `list_filter_rules`, `get_filter_rule`, `create_filter_rule`, `update_filter_rule`, `remove_filter_rule`, `enable_filter_rule`, `disable_filter_rule`, `move_filter_rule`, `create_basic_firewall_setup` |
| **NAT** | `list_nat_rules`, `get_nat_rule`, `create_nat_rule`, `update_nat_rule`, `remove_nat_rule`, `enable_nat_rule`, `disable_nat_rule`, `move_nat_rule` |
| **DNS** | `get_dns_settings`, `set_dns_servers`, `list_dns_static`, `get_dns_static`, `add_dns_static`, `update_dns_static`, `remove_dns_static`, `enable_dns_static`, `disable_dns_static`, `add_dns_regexp`, `flush_dns_cache`, `get_dns_cache`, `get_dns_cache_statistics`, `test_dns_query`, `export_dns_config` |
| **DHCP** | `list_dhcp_servers`, `get_dhcp_server`, `create_dhcp_server`, `remove_dhcp_server`, `create_dhcp_pool`, `create_dhcp_network` |
| **Routes** | `list_routes`, `get_route`, `add_route`, `add_default_route`, `add_blackhole_route`, `update_route`, `remove_route`, `enable_route`, `disable_route`, `get_route_statistics`, `get_route_cache`, `flush_route_cache`, `check_route_path` |
| **IP Address** | `list_ip_addresses`, `get_ip_address`, `add_ip_address`, `remove_ip_address` |
| **IP Pool** | `list_ip_pools`, `get_ip_pool`, `create_ip_pool`, `update_ip_pool`, `remove_ip_pool`, `expand_ip_pool`, `list_ip_pool_used` |
| **VLAN** | `list_vlan_interfaces`, `get_vlan_interface`, `create_vlan_interface`, `update_vlan_interface`, `remove_vlan_interface` |
| **Wireless** | `check_wireless_support`, `list_wireless_interfaces`, `get_wireless_interface`, `create_wireless_interface`, `update_wireless_interface`, `remove_wireless_interface`, `enable_wireless_interface`, `disable_wireless_interface`, `list_wireless_security_profiles`, `get_wireless_security_profile`, `create_wireless_security_profile`, `set_wireless_security_profile`, `remove_wireless_security_profile`, `list_wireless_access_list`, `create_wireless_access_list`, `remove_wireless_access_list_entry`, `get_wireless_registration_table`, `scan_wireless_networks` |
| **Users** | `list_users`, `get_user`, `add_user`, `update_user`, `remove_user`, `enable_user`, `disable_user`, `disconnect_user`, `get_active_users`, `list_user_groups`, `get_user_group`, `add_user_group`, `update_user_group`, `remove_user_group`, `list_user_ssh_keys`, `set_user_ssh_keys`, `remove_user_ssh_key`, `export_user_config` |
| **Backup** | `create_backup`, `create_export`, `list_backups`, `backup_info`, `restore_backup`, `download_file`, `upload_file`, `remove_file`, `import_configuration`, `export_section`, `run_script` |
| **Logs** | `get_logs`, `get_logs_by_severity`, `get_logs_by_topic`, `search_logs`, `get_security_logs`, `get_system_events`, `get_log_statistics`, `export_logs`, `clear_logs`, `monitor_logs` |

## Installation

```bash
git clone https://github.com/Korotkov113/mikrotik-mcp.git
cd mikrotik-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Configuration

### Claude Desktop / Claude Code

Add to your MCP config (`claude_desktop_config.json` or `.claude/settings.json`):

```json
{
  "mcpServers": {
    "mikrotik": {
      "command": "/path/to/mikrotik-mcp/.venv/bin/mcp-server-mikrotik",
      "args": [
        "--host", "192.168.0.1",
        "--username", "admin",
        "--key-filename", "/path/to/ssh/key",
        "--port", "22"
      ]
    }
  }
}
```

### Environment variables

Alternatively, configure via environment:

```bash
export MIKROTIK_HOST=192.168.0.1
export MIKROTIK_USERNAME=admin
export MIKROTIK_PASSWORD=your_password
export MIKROTIK_PORT=22
```

## Usage examples

### Run arbitrary command
```
> Show me BGP session status
Tool: run_command("/routing bgp session print")
```

### BGP management
```
> Create a BGP connection to antifilter service
Tool: add_bgp_connection(name="antifilter", remote_address="45.148.244.55/32", remote_as=65444, ...)
```

### Mangle rules
```
> Mark traffic from FreeInternet_list users to routing table to_proxy
Tool: add_mangle_rule(chain="prerouting", action="mark-routing", new_routing_mark="to_proxy", src_address_list="FreeInternet_list")
```

## License

MIT License. See [LICENSE](LICENSE).
