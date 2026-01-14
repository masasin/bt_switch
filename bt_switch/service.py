from loguru import logger
from .exceptions import ExecutionError
from .driver import BluetoothDriver
from .models import Device

class SwitchService:
    def __init__(self, local_driver: BluetoothDriver, remote_driver: BluetoothDriver, device: Device, target_name: str):
        self.local = local_driver
        self.remote = remote_driver
        self.device = device
        self.target_name = target_name

    def run(self):
        logger.info(f"Checking connection status for {self.device.name} ({self.device.mac})...")
        
        if self.local.is_connected(self.device.mac):
            self._handle_push()
        else:
            self._handle_pull()

    def _handle_push(self):
        logger.info("Device connected locally. Initiating PUSH.")
        
        logger.info("Disconnecting local...")
        self.local.disconnect(self.device.mac)
        
        try:
            logger.info(f"Connecting remote ({self.target_name})...")
            self.remote.connect(self.device.mac)
            logger.success(f"Successfully pushed to {self.target_name}")
        except ExecutionError as e:
            logger.error(f"Failed to connect remote: {e.stderr}")
            logger.warning("Reverting local connection...")
            self.local.connect(self.device.mac)

    def _handle_pull(self):
        logger.info(f"Device not local. Initiating PULL from {self.target_name}.")
        
        try:
            logger.debug(f"Ensuring disconnect on {self.target_name}...")
            self.remote.disconnect(self.device.mac)
        except ExecutionError:
            logger.warning(f"Could not verify disconnect on {self.target_name}, proceeding anyway.")

        logger.info("Connecting local...")
        self.local.connect(self.device.mac)
        logger.success("Successfully pulled to local machine")
