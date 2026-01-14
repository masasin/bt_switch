from unittest.mock import Mock

import pytest

from bt_switch.exceptions import ExecutionError
from bt_switch.models import Device
from bt_switch.service import SwitchService


@pytest.fixture
def mock_driver():
    return Mock()

@pytest.fixture
def device():
    return Device(mac="AA:BB:CC", name="Dev")

def test_service_run_push(mock_driver, device):
    local = mock_driver
    remote = Mock()
    
    local.is_connected.return_value = True
    
    service = SwitchService(local, remote, device, "remote_host")
    service.run()
    
    # Should disconnect local and connect remote
    local.disconnect.assert_called_with("AA:BB:CC")
    remote.connect.assert_called_with("AA:BB:CC")

def test_service_run_push_rollback(mock_driver, device):
    local = mock_driver
    remote = Mock()
    
    local.is_connected.return_value = True
    remote.connect.side_effect = ExecutionError(["cmd"], "Failed")
    
    service = SwitchService(local, remote, device, "remote_host")
    service.run()
    
    # Verify rollback: connect local again
    local.connect.assert_called_with("AA:BB:CC")

def test_service_run_pull(mock_driver, device):
    local = mock_driver
    remote = Mock()
    
    local.is_connected.return_value = False
    
    service = SwitchService(local, remote, device, "remote_host")
    service.run()
    
    # Should disconnect remote and connect local
    remote.disconnect.assert_called_with("AA:BB:CC")
    local.connect.assert_called_with("AA:BB:CC")

def test_service_run_pull_disconnect_fail_ignored(mock_driver, device):
    local = mock_driver
    remote = Mock()
    
    local.is_connected.return_value = False
    remote.disconnect.side_effect = ExecutionError(["cmd"], "Failed")
    
    service = SwitchService(local, remote, device, "remote_host")
    service.run()
    
    # Should proceed to connect local even if remote disconnect verification fails
    local.connect.assert_called_with("AA:BB:CC")
