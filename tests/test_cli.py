from unittest.mock import Mock
import pytest
from bt_switch.__main__ import entry_point
from bt_switch.exceptions import ConfigurationError

def test_entry_point_config_error(mocker):
    # Mock load_config to raise
    mocker.patch("bt_switch.__main__.load_config", side_effect=ConfigurationError("Fail"))
    mock_exit = mocker.patch("sys.exit")
    
    entry_point(None, None)
    
    mock_exit.assert_called_with(1)

def test_entry_point_success(mocker, sample_config):
    mocker.patch("bt_switch.__main__.load_config", return_value=sample_config)
    mocker.patch("socket.gethostname", return_value="laptop")
    
    # Mock everything down stream to ensure end-to-end wiring works
    mock_service = mocker.patch("bt_switch.__main__.SwitchService")
    mock_factory = mocker.patch("bt_switch.__main__.DriverFactory.create")
    
    entry_point()
    
    # Should resolve defaults: device='headphones', target='desktop'
    # Check that service was initialized with correct objects
    assert mock_factory.call_count == 2 # Local and Remote
    mock_service.assert_called()
    mock_service.return_value.run.assert_called_once()

def test_entry_point_cli_override(mocker, sample_config):
    # Setup sample_config to have localhost in defaults
    sample_config.defaults["localhost"] = sample_config.defaults["laptop"]
    
    mocker.patch("bt_switch.__main__.load_config", return_value=sample_config)
    mocker.patch("socket.gethostname", return_value="localhost")
    
    mock_service = mocker.patch("bt_switch.__main__.SwitchService")
    mocker.patch("bt_switch.__main__.DriverFactory.create")

    # Override target to 'laptop' (which is localhost in sample_config)
    # This hits the "Target is localhost" check
    entry_point(target="laptop")
    
    # Service should NOT run
    mock_service.return_value.run.assert_not_called()

def test_entry_point_custom_device_target(mocker, sample_config):
    mocker.patch("bt_switch.__main__.load_config", return_value=sample_config)
    mocker.patch("socket.gethostname", return_value="laptop")
    
    mock_service = mocker.patch("bt_switch.__main__.SwitchService")
    mocker.patch("bt_switch.__main__.DriverFactory.create")

    entry_point(target="desktop", device="mouse")
    
    # Check that service was initialized with mouse and desktop
    _, kwargs = mock_service.call_args
    # Or args depending on call signature...
    # SwitchService(local, remote, device, target_name)
    args = mock_service.call_args.args
    assert args[2].name == "Test Mouse"
    assert args[3] == "desktop"
