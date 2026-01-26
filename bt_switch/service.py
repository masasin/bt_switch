from loguru import logger

from .driver import BluetoothDriver
from .exceptions import ExecutionError
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


class BatchSwitchService:
    def __init__(
        self, 
        local_driver: BluetoothDriver, 
        remote_driver: BluetoothDriver, 
        devices: list[Device], 
        target_name: str
    ):
        self.local = local_driver
        self.remote = remote_driver
        self.devices = devices
        self.target_name = target_name

    def run(self, operation: str = "switch"):
        """
        Run batch operation.
        operation: "switch" | "push" | "pull"
        """
        # 1. Determine direction if 'switch'
        if operation == "switch":
            operation = self._determine_smart_direction()
        
        logger.info(f"Batch Operation: {operation.upper()} on {len(self.devices)} devices.")

        # 2. Execute
        for i, device in enumerate(self.devices, 1):
            logger.info(f"[{i}/{len(self.devices)}] Processing {device.name}...")
            svc = SwitchService(self.local, self.remote, device, self.target_name)
            try:
                if operation == "push":
                    svc._handle_push()
                elif operation == "pull":
                    svc._handle_pull()
            except Exception as e:
                logger.error(f"Failed to process {device.name}: {e}")
                # Continue to next device

    def _determine_smart_direction(self) -> str:
        """
        Consensus Logic:
        - If ANY device is connected locally, assume user wants to PUSH ALL to target.
        - If ALL devices are NOT connected locally, assume user wants to PULL ALL to local.
        """
        any_local = False
        for device in self.devices:
            if self.local.is_connected(device.mac):
                any_local = True
                break
        
        if any_local:
            logger.info("Smart Switch: Detected local connection(s). Deciding to PUSH ALL.")
            return "push"
        else:
            logger.info("Smart Switch: No local connections detected. Deciding to PULL ALL.")
            return "pull"

