from unittest.mock import MagicMock, call
import pytest

from bt_switch.models import Device, Host
from bt_switch.service import BatchSwitchService
from bt_switch.exceptions import ExecutionError

@pytest.fixture
def mock_drivers():
    local = MagicMock()
    remote = MagicMock()
    local.is_local = True
    remote.is_local = False
    return local, remote

@pytest.fixture
def devices():
    return [
        Device(mac="AA:AA:AA:AA:AA:AA", name="Dev1"),
        Device(mac="BB:BB:BB:BB:BB:BB", name="Dev2"),
    ]

def test_batch_smart_any_local_means_push(mock_drivers, devices):
    local, remote = mock_drivers
    
    # Dev1 is local, Dev2 is remote (indeterminate state)
    local.is_connected.side_effect = lambda mac: mac == "AA:AA:AA:AA:AA:AA"
    
    svc = BatchSwitchService(local, remote, devices, "target_host")
    svc.run("switch")
    
    # Expectation: Consensus PUSH
    # Dev1 (Local) -> Disconnect Local, Connect Remote
    # Dev2 (Remote) -> Disconnect Local, Connect Remote (Idempotent pusing)
    
    # Check connect remote calls
    assert remote.connect.call_count == 2
    remote.connect.assert_has_calls([
        call("AA:AA:AA:AA:AA:AA"), 
        call("BB:BB:BB:BB:BB:BB")
    ], any_order=True)

def test_batch_smart_all_remote_means_pull(mock_drivers, devices):
    local, remote = mock_drivers
    
    # Neither connected locally
    local.is_connected.return_value = False
    
    svc = BatchSwitchService(local, remote, devices, "target_host")
    svc.run("switch")
    
    # Expectation: Consensus PULL
    # Disconnect Remote, Connect Local
    
    # Check connect local calls
    assert local.connect.call_count == 2
    local.connect.assert_has_calls([
        call("AA:AA:AA:AA:AA:AA"), 
        call("BB:BB:BB:BB:BB:BB")
    ], any_order=True)

def test_batch_explicit_push(mock_drivers, devices):
    local, remote = mock_drivers
    local.is_connected.return_value = False # Even if none are local
    
    svc = BatchSwitchService(local, remote, devices, "target_host")
    svc.run("push")
    
    # Expect PUSH despite no local connections
    assert remote.connect.call_count == 2

def test_batch_continue_on_error(mock_drivers, devices):
    local, remote = mock_drivers
    local.is_connected.return_value = False
    
    # First device fails to disconnect remote (Pull scenario)
    remote.disconnect.side_effect = [ExecutionError(["disconnect"], "Fail"), None]
    
    svc = BatchSwitchService(local, remote, devices, "target_host")
    svc.run("pull")
    
    # Should still try to connect local for both (as per pull logic: best effort disconnect, then connect local)
    assert local.connect.call_count == 2
