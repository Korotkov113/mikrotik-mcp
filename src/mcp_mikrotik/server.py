import logging
import sys

from mcp_mikrotik import config
from mcp_mikrotik.app import mcp
from mcp_mikrotik.config import MikrotikConfig
from mcp_mikrotik.devices import device_manager


def main():
    """
    Entry point for the MCP MikroTik server when run as a command-line program.
    """
    config.mikrotik_config = MikrotikConfig(_cli_parse_args=True)

    logger = logging.getLogger(__name__)

    logger.info("Starting MCP MikroTik server")
    device_manager.load(config.mikrotik_config)
    try:
        active_name, active = device_manager.get_active()
        logger.info(f"Active device: {active_name} ({active.host}:{active.port})")
        logger.info(f"Using username: {active.username}")
        if active.key_filename:
            logger.info(f"Using key from: {active.key_filename}")
    except Exception:
        logger.warning("No devices configured; add one with the add_device tool")

    try:
        mcp.settings.host = config.mikrotik_config.mcp.host
        mcp.settings.port = config.mikrotik_config.mcp.port
        mcp.run(transport=config.mikrotik_config.mcp.transport)
    except KeyboardInterrupt:
        logger.info("MCP MikroTik server stopped by user")
    except Exception as e:
        logger.error(f"Error running MCP MikroTik server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
