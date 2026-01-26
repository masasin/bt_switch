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
    mock_service = mocker.patch("bt_switch.__main__.BatchSwitchService")
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
    
    mocker.patch("socket.gethostname", return_value="localhost")
    
    mock_service = mocker.patch("bt_switch.__main__.BatchSwitchService")
    mocker.patch("bt_switch.__main__.DriverFactory.create")

    # Override target to 'laptop' (which is localhost in sample_config)
    # This hits the "Target is localhost" check
    entry_point(target="laptop")
    
    # Service should NOT run
    mock_service.return_value.run.assert_not_called()

def test_entry_point_custom_device_target(mocker, sample_config):
    mocker.patch("bt_switch.__main__.load_config", return_value=sample_config)
    mocker.patch("socket.gethostname", return_value="laptop")
    
    mock_service = mocker.patch("bt_switch.__main__.BatchSwitchService")
    mocker.patch("bt_switch.__main__.DriverFactory.create")

    entry_point(target="desktop", device="mouse")
    
    # Check that service was initialized with mouse and desktop
    # BatchSwitchService(local, remote, devices_list, target_name)
    args = mock_service.call_args.args
    assert args[2][0].name == "Test Mouse"
    assert args[3] == "desktop"

def test_entry_point_fallback_to_group(mocker, sample_config):
    # Setup a group
    sample_config.groups["mygroup"] = ["headphones", "mouse"]
    
    mocker.patch("bt_switch.__main__.load_config", return_value=sample_config)
    mocker.patch("socket.gethostname", return_value="laptop")
    
    mock_batch_service = mocker.patch("bt_switch.__main__.BatchSwitchService")
    mocker.patch("bt_switch.__main__.DriverFactory.create")

    # Pass 'mygroup' as device, which is NOT in devices, but IS in groups
    entry_point(device="mygroup")
    
    # Check BatchSwitchService used
    mock_batch_service.assert_called()
    args = mock_batch_service.call_args.args
    # args[2] is devices list. Should be 2 distinct device objects
    assert len(args[2]) == 2
    mock_batch_service.return_value.run.assert_called_with("switch")

def test_entry_point_default_group(mocker, sample_config):
    # Setup group and set as default
    sample_config.groups["mygroup"] = ["headphones"]
    sample_config.defaults["laptop"].default_device = "mygroup"
    
    mocker.patch("bt_switch.__main__.load_config", return_value=sample_config)
    mocker.patch("socket.gethostname", return_value="laptop")
    
    mock_batch_service = mocker.patch("bt_switch.__main__.BatchSwitchService")
    mocker.patch("bt_switch.__main__.DriverFactory.create")

    entry_point()
    
    mock_batch_service.assert_called()
    args = mock_batch_service.call_args.args
    assert len(args[2]) == 1
    assert args[2][0].name == "Test Headphones"

