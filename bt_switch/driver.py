import abc
from .exceptions import ExecutionError, ConfigurationError
from .executor import Executor, LocalExecutor, SshExecutor
from .models import Host

class BluetoothDriver(abc.ABC):
    def __init__(self, executor: Executor):
        self.executor = executor

    @abc.abstractmethod
    def is_connected(self, mac: str) -> bool:
        pass

    @abc.abstractmethod
    def connect(self, mac: str) -> None:
        pass

    @abc.abstractmethod
    def disconnect(self, mac: str) -> None:
        pass

class BluezDriver(BluetoothDriver):
    def is_connected(self, mac: str) -> bool:
        try:
            output = self.executor.run(["bluetoothctl", "info", mac], timeout=5)
            return "Connected: yes" in output
        except ExecutionError:
            return False

    def connect(self, mac: str) -> None:
        self.executor.run(["bluetoothctl", "connect", mac], timeout=15)

    def disconnect(self, mac: str) -> None:
        try:
            self.executor.run(["bluetoothctl", "disconnect", mac], timeout=8)
        except ExecutionError as e:
            if "not available" in e.stderr.lower():
                return
            raise

class DriverFactory:
    @staticmethod
    def create(host_config: Host, is_local: bool) -> BluetoothDriver:
        executor: Executor
        if is_local:
            executor = LocalExecutor()
        elif host_config.protocol == "ssh":
            executor = SshExecutor(host_config)
        else:
            raise ConfigurationError(f"Unsupported protocol: {host_config.protocol}")

        if host_config.driver_type == "bluez":
            return BluezDriver(executor)
        
        raise ConfigurationError(f"Unsupported driver: {host_config.driver_type}")
