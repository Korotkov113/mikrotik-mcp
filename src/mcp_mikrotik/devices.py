"""Device registry: holds all configured MikroTik devices and the active one.

Registry sources, merged in order (later wins):
  1. JSON devices file (``--devices-file`` / ``MIKROTIK_DEVICES_FILE``)
  2. ``devices`` from environment/CLI (``MIKROTIK_DEVICES`` JSON)
  3. Legacy single-device flags (``--host``/``--username``/...) as device "default"

The active device is what every tool talks to; it can be switched at runtime
with the ``use_device`` tool without restarting the server.
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import DeviceConfig, MikrotikConfig

logger = logging.getLogger(__name__)

DEFAULT_DEVICES_FILE = Path.home() / ".config" / "mikrotik-mcp" / "devices.json"

LEGACY_FIELDS = ("host", "username", "password", "port", "key_filename")


class NoDevicesConfiguredError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "No MikroTik devices configured. Add one with the add_device tool, "
            "pass --host/--username on startup, or provide a devices file."
        )


class DeviceManager:
    """Thread-safe registry of MikroTik devices plus the active selection."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._devices: Dict[str, DeviceConfig] = {}
        self._active: Optional[str] = None
        self._devices_file: Path = DEFAULT_DEVICES_FILE
        self._file_default: Optional[str] = None
        self._loaded = False

    # -- loading ---------------------------------------------------------

    def load(self, cfg: MikrotikConfig) -> None:
        """Build the registry from config. Called once at startup."""
        with self._lock:
            self._devices = {}
            self._file_default = None
            self._devices_file = (
                Path(cfg.devices_file).expanduser()
                if cfg.devices_file
                else DEFAULT_DEVICES_FILE
            )

            self._load_devices_file()

            for name, device in cfg.devices.items():
                self._devices[name] = device

            # Legacy single-device flags become device "default" when the user
            # set any of them explicitly, or when nothing else is configured —
            # this keeps pre-multi-device setups working unchanged.
            legacy_set = bool(set(cfg.model_fields_set) & set(LEGACY_FIELDS))
            if (legacy_set or not self._devices) and "default" not in self._devices:
                self._devices["default"] = DeviceConfig(
                    host=cfg.host,
                    username=cfg.username,
                    password=cfg.password,
                    port=cfg.port,
                    key_filename=cfg.key_filename,
                    description="from --host/--username startup flags",
                )

            self._active = self._pick_active(cfg.default_device)
            self._loaded = True
            logger.info(
                "Device registry: %s (active: %s)",
                ", ".join(sorted(self._devices)) or "(empty)",
                self._active,
            )

    def _load_devices_file(self) -> None:
        path = self._devices_file
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to read devices file %s: %s", path, e)
            return

        # Two accepted shapes: {"devices": {...}, "default_device": "x"}
        # or a flat {name: {...}} mapping.
        entries = data.get("devices", data) if isinstance(data, dict) else {}
        for name, spec in entries.items():
            try:
                self._devices[name] = DeviceConfig(**spec)
            except Exception as e:
                logger.error("Skipping device %r from %s: %s", name, path, e)

        file_default = data.get("default_device") if isinstance(data, dict) else None
        if isinstance(file_default, str):
            self._file_default = file_default

    def _pick_active(self, cli_default: Optional[str]) -> Optional[str]:
        for candidate in (cli_default, self._file_default, "default"):
            if candidate and candidate in self._devices:
                return candidate
        return next(iter(sorted(self._devices)), None)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            from . import config

            self.load(config.mikrotik_config)

    # -- queries ---------------------------------------------------------

    def list_devices(self) -> List[dict]:
        """Registry contents with secrets masked, for display to the model."""
        with self._lock:
            self._ensure_loaded()
            result = []
            for name in sorted(self._devices):
                d = self._devices[name]
                result.append(
                    {
                        "name": name,
                        "host": d.host,
                        "port": d.port,
                        "username": d.username,
                        "auth": "ssh-key" if d.key_filename else "password",
                        "description": d.description,
                        "active": name == self._active,
                    }
                )
            return result

    def get(self, name: str) -> DeviceConfig:
        with self._lock:
            self._ensure_loaded()
            if name not in self._devices:
                known = ", ".join(sorted(self._devices)) or "(none)"
                raise KeyError(f"Unknown device '{name}'. Known devices: {known}")
            return self._devices[name]

    def get_active(self) -> Tuple[str, DeviceConfig]:
        with self._lock:
            self._ensure_loaded()
            if self._active is None or self._active not in self._devices:
                raise NoDevicesConfiguredError()
            return self._active, self._devices[self._active]

    # -- mutations -------------------------------------------------------

    def set_active(self, name: str) -> DeviceConfig:
        with self._lock:
            device = self.get(name)
            self._active = name
            logger.info("Active device switched to '%s' (%s)", name, device.host)
            return device

    def add(self, name: str, device: DeviceConfig, persist: bool = False) -> None:
        if not name or "/" in name:
            raise ValueError(f"Invalid device name: {name!r}")
        with self._lock:
            self._ensure_loaded()
            self._devices[name] = device
            if self._active is None:
                self._active = name
            if persist:
                self.save_to_file()

    def remove(self, name: str, persist: bool = False) -> None:
        with self._lock:
            self.get(name)  # raises if unknown
            del self._devices[name]
            if self._active == name:
                self._active = next(iter(sorted(self._devices)), None)
            if persist:
                self.save_to_file()

    def save_to_file(self) -> Path:
        """Persist the registry as JSON, readable only by the current user."""
        with self._lock:
            path = self._devices_file
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "default_device": self._active,
                "devices": {
                    name: d.model_dump() for name, d in sorted(self._devices.items())
                },
            }
            path.write_text(json.dumps(payload, indent=2) + "\n")
            os.chmod(path, 0o600)
            logger.info("Saved %d device(s) to %s", len(self._devices), path)
            return path


device_manager = DeviceManager()
