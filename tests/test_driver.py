from unittest.mock import Mock

import pytest

from bt_switch.driver import BluezDriver, DriverFactory
from bt_switch.exceptions import ConfigurationError, ExecutionError
from bt_switch.models import Host


@pytest.fixture
def mock_executor():
    return Mock()

def test_bluez_is_connected_true(mock_executor):
    mock_executor.run.return_value = "Device FF:FF:FF:FF:FF:FF\n\tName: Dev\n\tConnected: yes\n"
    driver = BluezDriver(mock_executor)
    assert driver.is_connected("FF:FF:FF:FF:FF:FF") is True

def test_bluez_is_connected_false(mock_executor):
    mock_executor.run.return_value = "Device FF:FF:FF:FF:FF:FF\n\tName: Dev\n\tConnected: no\n"
    driver = BluezDriver(mock_executor)
    assert driver.is_connected("FF:FF:FF:FF:FF:FF") is False

def test_bluez_is_connected_error(mock_executor):
    mock_executor.run.side_effect = ExecutionError(["cmd"], "error")
    driver = BluezDriver(mock_executor)
    assert driver.is_connected("FF:FF:FF:FF:FF:FF") is False

def test_bluez_connect(mock_executor):
    driver = BluezDriver(mock_executor)
    driver.connect("FF:FF:FF:FF:FF:FF")
    mock_executor.run.assert_called_with(["bluetoothctl", "connect", "FF:FF:FF:FF:FF:FF"], timeout=15)

def test_bluez_disconnect_success(mock_executor):
    driver = BluezDriver(mock_executor)
    driver.disconnect("FF:FF:FF:FF:FF:FF")
    mock_executor.run.assert_called_with(["bluetoothctl", "disconnect", "FF:FF:FF:FF:FF:FF"], timeout=8)

def test_bluez_disconnect_not_available_ignored(mock_executor):
    mock_executor.run.side_effect = ExecutionError(["cmd"], "Failed to disconnect: org.bluez.Error.Failed Not available")
    driver = BluezDriver(mock_executor)
    # Should not raise
    driver.disconnect("FF:FF:FF:FF:FF:FF")

def test_bluez_disconnect_other_error(mock_executor):
    mock_executor.run.side_effect = ExecutionError(["cmd"], "Other error")
    driver = BluezDriver(mock_executor)
    with pytest.raises(ExecutionError):
        driver.disconnect("FF:FF:FF:FF:FF:FF")

def test_driver_factory_create():
    host = Host(address="1.2.3.4", user="u", protocol="ssh", driver_type="bluez")
    driver = DriverFactory.create(host, is_local=False)
    assert isinstance(driver, BluezDriver)

def test_driver_factory_unsupported_protocol():
    host = Host(address="1.2.3.4", user="u", protocol="ssh", driver_type="bluez")
    # Manually hack protocol for test as strict validation prevents it
    host.protocol = "unsupported" # type: ignore
    with pytest.raises(ConfigurationError, match="Unsupported protocol"):
        DriverFactory.create(host, is_local=False)
