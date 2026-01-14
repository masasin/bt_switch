import socket
import sys

from cyclopts import App
from loguru import logger

from .config import load_config
from .driver import DriverFactory
from .exceptions import BtSwitchError, ConfigurationError
from .models import Host
from .service import SwitchService

app = App(name="bt-switch")

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
    except Exception as e:
        logger.exception("Unexpected error")
        sys.exit(1)

if __name__ == "__main__":
    app()
