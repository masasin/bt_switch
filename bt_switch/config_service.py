from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.toml_document import TOMLDocument

from .exceptions import ConfigurationError
from .models import AppConfig, DefaultSettings, Device, Host


class ConfigService:
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load(self) -> AppConfig:
        doc = self._load_document()
        return AppConfig.model_validate(doc)

    def _load_document(self) -> TOMLDocument:
        if not self.config_path.exists():
            return tomlkit.document()

        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                return tomlkit.load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to load config: {e}")

    def _save_document(self, doc: TOMLDocument) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            tomlkit.dump(doc, f)

    def _ensure_table(self, doc: TOMLDocument, *keys: str) -> Any:
        current = doc
        for key in keys:
            if key not in current:
                current[key] = tomlkit.table()
            current = current[key]
        return current

    # --- Groups ---

    def list_groups(self) -> dict[str, list[str]]:
        doc = self._load_document()
        groups_table = doc.get("groups", {})
        # Convert to standard dict to match AppConfig model
        return {k: [str(i) for i in v] for k, v in groups_table.items()}

    def add_group(self, alias: str, device_aliases: list[str]) -> None:
        doc = self._load_document()
        
        # Validation: check device aliases exist
        devices = doc.get("devices", {})
        for dev_alias in device_aliases:
            if dev_alias not in devices:
                raise ConfigurationError(f"Device '{dev_alias}' not found in configuration")

        groups = self._ensure_table(doc, "groups")
        if alias in groups:
             raise ConfigurationError(f"Group '{alias}' already exists")

        groups[alias] = device_aliases
        self._save_document(doc)

    def remove_group(self, alias: str) -> None:
        doc = self._load_document()
        groups = doc.get("groups")
        if not groups or alias not in groups:
             raise ConfigurationError(f"Group '{alias}' not found")
        
        del groups[alias]
        self._save_document(doc)

    # --- Devices ---

    def list_devices(self) -> dict[str, Device]:
        doc = self._load_document()
        devices_table = doc.get("devices", {})
        result = {}
        for alias, data in devices_table.items():
            result[alias] = Device.model_validate(data)
        return result

    def add_device(self, alias: str, mac: str, name: str) -> None:
        doc = self._load_document()
        devices = self._ensure_table(doc, "devices")
        
        if alias in devices:
            raise ConfigurationError(f"Device '{alias}' already exists")

        device_table = tomlkit.inline_table()
        device_table.update({"mac": mac, "name": name})
        devices[alias] = device_table

        self._save_document(doc)

    def remove_device(self, alias: str) -> None:
        doc = self._load_document()
        devices = doc.get("devices")
        if not devices or alias not in devices:
            raise ConfigurationError(f"Device '{alias}' not found")
        
        del devices[alias]
        self._save_document(doc)

    # --- Hosts ---

    def list_hosts(self) -> dict[str, Host]:
        doc = self._load_document()
        hosts_table = doc.get("hosts", {})
        result = {}
        for alias, data in hosts_table.items():
            result[alias] = Host.model_validate(data)
        return result

    def add_host(
        self,
        alias: str,
        *, 
        address: str, 
        user: str, 
        protocol: str = "ssh", 
        driver_type: str = "bluez"
    ) -> None:
        doc = self._load_document()
        hosts = self._ensure_table(doc, "hosts")
        
        if alias in hosts:
            raise ConfigurationError(f"Host '{alias}' already exists")

        # Validate by creating model (will raise ValidationError if invalid)
        Host(address=address, user=user, protocol=protocol, driver_type=driver_type)

        host_table = tomlkit.inline_table()
        host_table.update({
            "address": address, 
            "user": user,
            "protocol": protocol,
            "driver_type": driver_type
        })
        hosts[alias] = host_table
        
        self._save_document(doc)

    def remove_host(self, alias: str) -> None:
        doc = self._load_document()
        hosts = doc.get("hosts")
        if not hosts or alias not in hosts:
            raise ConfigurationError(f"Host '{alias}' not found")
        
        del hosts[alias]
        self._save_document(doc)

    # --- Defaults ---

    def list_defaults(self) -> dict[str, DefaultSettings]:
        doc = self._load_document()
        defaults_table = doc.get("defaults", {})
        result = {}
        for hostname, data in defaults_table.items():
            result[hostname] = DefaultSettings.model_validate(data)
        return result

    def set_default(self, hostname: str, *, default_device: str, default_target: str) -> None:
        doc = self._load_document()
        
        # Validate references exist (optional, but good practice per plan discussion)
        devices = doc.get("devices", {})
        hosts = doc.get("hosts", {})
        
        if default_device not in devices:
             raise ConfigurationError(f"Device '{default_device}' not found in configuration")
        if default_target not in hosts:
             raise ConfigurationError(f"Host '{default_target}' not found in configuration")

        defaults = self._ensure_table(doc, "defaults")
        
        entry = tomlkit.inline_table()
        entry.update({
            "default_device": default_device,
            "default_target": default_target
        })
        defaults[hostname] = entry
        
        self._save_document(doc)

    def remove_default(self, hostname: str) -> None:
        doc = self._load_document()
        defaults = doc.get("defaults")
        if not defaults or hostname not in defaults:
            raise ConfigurationError(f"Defaults for '{hostname}' not found")
        
        del defaults[hostname]
        self._save_document(doc)
