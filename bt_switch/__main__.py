import socket
import sys

from cyclopts import App
from loguru import logger

from .config import get_config_path, load_config
from .config_service import ConfigService
from .driver import DriverFactory
from .exceptions import BtSwitchError, ConfigurationError
from .models import Host
from .service import SwitchService

app = App(name="bt-switch")

devices_app = App(name="devices", help="Manage bluetooth devices.")
hosts_app = App(name="hosts", help="Manage remote hosts.")
defaults_app = App(name="defaults", help="Manage default settings.")

app.command(devices_app)
app.command(hosts_app)
app.command(defaults_app)

@devices_app.command(name="list")
def list_devices():
    """List configured devices."""
    svc = ConfigService(get_config_path())
    devices = svc.list_devices()
    if not devices:
        print("No devices configured.")
        return
    
    print(f"{'ALIAS':<15} {'MAC':<20} {'NAME'}")
    print("-" * 50)
    for alias, dev in devices.items():
        print(f"{alias:<15} {dev.mac:<20} {dev.name}")

@devices_app.command(name="add")
def add_device(alias: str, mac: str, name: str):
    """Add a new device."""
    svc = ConfigService(get_config_path())
    try:
        svc.add_device(alias, mac, name)
        print(f"Device '{alias}' added.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

@devices_app.command(name="remove")
def remove_device(alias: str):
    """Remove a device."""
    svc = ConfigService(get_config_path())
    try:
        svc.remove_device(alias)
        print(f"Device '{alias}' removed.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

@hosts_app.command(name="list")
def list_hosts():
    """List configured hosts."""
    svc = ConfigService(get_config_path())
    hosts = svc.list_hosts()
    if not hosts:
        print("No hosts configured.")
        return

    print(f"{'ALIAS':<15} {'ADDRESS':<20} {'USER':<10} {'PROTO':<8} {'DRIVER'}")
    print("-" * 65)
    for alias, host in hosts.items():
        print(f"{alias:<15} {host.address:<20} {host.user:<10} {host.protocol:<8} {host.driver_type}")

@hosts_app.command(name="add")
def add_host(
    alias: str, 
    address: str, 
    user: str, 
    protocol: str = "ssh", 
    driver_type: str = "bluez"
):
    """Add a new host."""
    svc = ConfigService(get_config_path())
    try:
        svc.add_host(alias, address=address, user=user, protocol=protocol, driver_type=driver_type)
        print(f"Host '{alias}' added.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

@hosts_app.command(name="remove")
def remove_host(alias: str):
    """Remove a host."""
    svc = ConfigService(get_config_path())
    try:
        svc.remove_host(alias)
        print(f"Host '{alias}' removed.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

@defaults_app.command(name="list")
def list_defaults():
    """List default settings per host."""
    svc = ConfigService(get_config_path())
    defaults = svc.list_defaults()
    if not defaults:
        print("No defaults configured.")
        return

    print(f"{'HOSTNAME':<20} {'DEVICE':<15} {'TARGET'}")
    print("-" * 50)
    for hostname, settings in defaults.items():
        print(f"{hostname:<20} {settings.default_device:<15} {settings.default_target}")

@defaults_app.command(name="set")
def set_default(hostname: str, device: str, target: str):
    """Set default device and target for a hostname."""
    svc = ConfigService(get_config_path())
    try:
        svc.set_default(hostname, default_device=device, default_target=target)
        print(f"Defaults set for '{hostname}'.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

@defaults_app.command(name="remove")
def remove_default(hostname: str):
    """Remove defaults for a hostname."""
    svc = ConfigService(get_config_path())
    try:
        svc.remove_default(hostname)
        print(f"Defaults removed for '{hostname}'.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


@app.default
def entry_point(target: str | None = None, device: str | None = None):
    try:
        config = load_config()
        hostname = socket.gethostname()

        if hostname not in config.defaults:
            raise ConfigurationError(f"Hostname '{hostname}' not in [defaults]")
        
        defaults = config.defaults[hostname]
        target_alias = target or defaults.default_target
        device_alias = device or defaults.default_device

        if target_alias not in config.hosts:
            raise ConfigurationError(f"Target '{target_alias}' not in [hosts]")
        if device_alias not in config.devices:
            raise ConfigurationError(f"Device '{device_alias}' not in [devices]")

        device_obj = config.devices[device_alias]
        remote_host_cfg = config.hosts[target_alias]
        
        # Self-targeting check
        if remote_host_cfg.address == hostname: 
             # Logic could support switching between adapters on same host, 
             # but for now we treat 'target=self' as invalid or no-op
             logger.warning("Target is localhost. Nothing to switch.")
             return

        local_driver = DriverFactory.create(
            Host(address="localhost", user="", protocol="local", driver_type="bluez"), 
            is_local=True
        )
        remote_driver = DriverFactory.create(
            remote_host_cfg, 
            is_local=False
        )

        service = SwitchService(local_driver, remote_driver, device_obj, target_alias)
        service.run()

    except BtSwitchError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)

@app.command(name="tui")
def tui():
    """Launch the Terminal User Interface."""
    from .tui import BtSwitchApp
    app = BtSwitchApp()
    app.run()

if __name__ == "__main__":
    app()
