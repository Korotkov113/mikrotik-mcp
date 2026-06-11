from typing import Dict, Literal, Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class McpServerSettings(BaseModel):
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    host: str = "0.0.0.0"
    port: int = 8000


class DeviceConfig(BaseModel):
    """Connection settings for a single MikroTik device."""

    host: str
    username: str = "admin"
    password: str = ""
    port: int = 22
    key_filename: Optional[str] = None
    description: str = ""


class MikrotikConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MIKROTIK_",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
        cli_prog_name="mcp-server-mikrotik",
        cli_kebab_case=True,
    )

    # Single-device settings (registered in the device registry as "default")
    host: str = "127.0.0.1"
    username: str = "admin"
    password: str = ""
    port: int = 22
    key_filename: Optional[str] = None

    # Multi-device settings:
    # MIKROTIK_DEVICES='{"office": {"host": "10.0.0.1", "username": "admin"}}'
    # or --devices '{"office": {...}}' on the CLI
    devices: Dict[str, DeviceConfig] = {}
    # JSON file with the device registry (see docs); also where add_device
    # persists devices when save=True. Default: ~/.config/mikrotik-mcp/devices.json
    devices_file: Optional[str] = None
    # Name of the device that is active at startup
    default_device: Optional[str] = None

    mcp: McpServerSettings = McpServerSettings()


mikrotik_config = MikrotikConfig()
