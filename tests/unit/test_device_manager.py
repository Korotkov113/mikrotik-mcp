"""Unit tests for the multi-device registry (mcp_mikrotik.devices)."""

import json
import os
import stat

import pytest

from mcp_mikrotik.config import DeviceConfig, MikrotikConfig
from mcp_mikrotik.devices import DeviceManager, NoDevicesConfiguredError


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Keep MIKROTIK_* env vars of the host machine out of the tests."""
    for key in list(os.environ):
        if key.startswith("MIKROTIK_"):
            monkeypatch.delenv(key)


@pytest.fixture
def devices_file(tmp_path):
    return tmp_path / "devices.json"


def make_manager(cfg: MikrotikConfig) -> DeviceManager:
    manager = DeviceManager()
    manager.load(cfg)
    return manager


class TestLegacySingleDevice:
    def test_legacy_flags_become_default_device(self, devices_file):
        cfg = MikrotikConfig(
            host="192.168.0.1",
            username="korotkov",
            port=2222,
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)

        name, device = manager.get_active()
        assert name == "default"
        assert device.host == "192.168.0.1"
        assert device.username == "korotkov"
        assert device.port == 2222

    def test_empty_config_still_registers_default(self, devices_file):
        cfg = MikrotikConfig(devices_file=str(devices_file))
        manager = make_manager(cfg)

        name, device = manager.get_active()
        assert name == "default"
        assert device.host == "127.0.0.1"


class TestMultiDevice:
    def test_devices_from_config(self, devices_file):
        cfg = MikrotikConfig(
            devices={
                "office": DeviceConfig(host="10.0.0.1"),
                "home": DeviceConfig(host="192.168.88.1"),
            },
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)

        names = [d["name"] for d in manager.list_devices()]
        # No junk "default" device when legacy flags were not set
        assert names == ["home", "office"]

    def test_default_device_selects_active(self, devices_file):
        cfg = MikrotikConfig(
            devices={
                "office": DeviceConfig(host="10.0.0.1"),
                "home": DeviceConfig(host="192.168.88.1"),
            },
            default_device="office",
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)

        name, device = manager.get_active()
        assert name == "office"
        assert device.host == "10.0.0.1"

    def test_legacy_and_devices_coexist(self, devices_file):
        cfg = MikrotikConfig(
            host="192.168.0.1",
            devices={"office": DeviceConfig(host="10.0.0.1")},
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)

        names = [d["name"] for d in manager.list_devices()]
        assert names == ["default", "office"]
        assert manager.get_active()[0] == "default"

    def test_switch_active(self, devices_file):
        cfg = MikrotikConfig(
            devices={
                "office": DeviceConfig(host="10.0.0.1"),
                "home": DeviceConfig(host="192.168.88.1"),
            },
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)

        manager.set_active("office")
        assert manager.get_active()[0] == "office"

    def test_switch_to_unknown_raises(self, devices_file):
        cfg = MikrotikConfig(devices_file=str(devices_file))
        manager = make_manager(cfg)

        with pytest.raises(KeyError, match="Unknown device 'nope'"):
            manager.set_active("nope")


class TestDevicesFile:
    def test_load_structured_file(self, devices_file):
        devices_file.write_text(
            json.dumps(
                {
                    "default_device": "lab",
                    "devices": {
                        "lab": {"host": "172.16.0.1", "username": "test"},
                        "edge": {"host": "172.16.0.2", "port": 2222},
                    },
                }
            )
        )
        cfg = MikrotikConfig(devices_file=str(devices_file))
        manager = make_manager(cfg)

        name, device = manager.get_active()
        assert name == "lab"
        assert device.username == "test"
        assert manager.get("edge").port == 2222

    def test_load_flat_file(self, devices_file):
        devices_file.write_text(
            json.dumps({"router1": {"host": "10.1.1.1"}})
        )
        cfg = MikrotikConfig(devices_file=str(devices_file))
        manager = make_manager(cfg)

        assert manager.get("router1").host == "10.1.1.1"

    def test_config_devices_override_file(self, devices_file):
        devices_file.write_text(
            json.dumps({"router1": {"host": "10.1.1.1"}})
        )
        cfg = MikrotikConfig(
            devices={"router1": DeviceConfig(host="10.9.9.9")},
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)

        assert manager.get("router1").host == "10.9.9.9"

    def test_invalid_file_is_ignored(self, devices_file):
        devices_file.write_text("{not json")
        cfg = MikrotikConfig(host="10.0.0.5", devices_file=str(devices_file))
        manager = make_manager(cfg)

        assert manager.get_active()[1].host == "10.0.0.5"

    def test_save_roundtrip(self, devices_file):
        cfg = MikrotikConfig(
            devices={"office": DeviceConfig(host="10.0.0.1", password="s3cret")},
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)
        manager.add("home", DeviceConfig(host="192.168.88.1"), persist=True)

        assert devices_file.is_file()
        mode = stat.S_IMODE(devices_file.stat().st_mode)
        assert mode == 0o600

        reloaded = make_manager(
            MikrotikConfig(devices_file=str(devices_file))
        )
        names = [d["name"] for d in reloaded.list_devices()]
        assert names == ["home", "office"]
        assert reloaded.get("office").password == "s3cret"


class TestMutations:
    def test_add_and_remove(self, devices_file):
        cfg = MikrotikConfig(host="10.0.0.1", devices_file=str(devices_file))
        manager = make_manager(cfg)

        manager.add("spare", DeviceConfig(host="10.0.0.2"))
        assert manager.get("spare").host == "10.0.0.2"

        manager.remove("spare")
        with pytest.raises(KeyError):
            manager.get("spare")

    def test_remove_active_reassigns(self, devices_file):
        cfg = MikrotikConfig(
            devices={
                "a": DeviceConfig(host="10.0.0.1"),
                "b": DeviceConfig(host="10.0.0.2"),
            },
            default_device="b",
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)

        manager.remove("b")
        assert manager.get_active()[0] == "a"

    def test_remove_last_device_then_get_active_raises(self, devices_file):
        cfg = MikrotikConfig(host="10.0.0.1", devices_file=str(devices_file))
        manager = make_manager(cfg)

        manager.remove("default")
        with pytest.raises(NoDevicesConfiguredError):
            manager.get_active()

    def test_invalid_name_rejected(self, devices_file):
        cfg = MikrotikConfig(devices_file=str(devices_file))
        manager = make_manager(cfg)

        with pytest.raises(ValueError):
            manager.add("bad/name", DeviceConfig(host="10.0.0.3"))


class TestListing:
    def test_list_masks_secrets(self, devices_file):
        cfg = MikrotikConfig(
            devices={
                "office": DeviceConfig(host="10.0.0.1", password="hunter2"),
                "home": DeviceConfig(host="192.168.88.1", key_filename="/k"),
            },
            devices_file=str(devices_file),
        )
        manager = make_manager(cfg)

        listing = manager.list_devices()
        assert "hunter2" not in json.dumps(listing)
        by_name = {d["name"]: d for d in listing}
        assert by_name["office"]["auth"] == "password"
        assert by_name["home"]["auth"] == "ssh-key"
        assert by_name["home"]["active"] or by_name["office"]["active"]
