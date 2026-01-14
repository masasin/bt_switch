import pytest

from bt_switch.config import load_config
from bt_switch.exceptions import ConfigurationError


def test_load_config_not_found(mocker, tmp_path):
    mocker.patch("bt_switch.config.user_config_path", return_value=tmp_path / "nonexistent")
    with pytest.raises(ConfigurationError, match="Config not found"):
        load_config()

def test_load_config_parse_error(mocker, tmp_path):
    config_dir = tmp_path / "bt_switch"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text("invalid toml content [")
    
    mocker.patch("bt_switch.config.user_config_path", return_value=config_dir)
    
    with pytest.raises(ConfigurationError, match="Config parse error"):
        load_config()

def test_load_config_success(mocker, tmp_path):
    config_dir = tmp_path / "bt_switch"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    
    toml_content = """
    [devices.d1]
    mac = "00:11:22:33:44:55"
    name = "Test Device"

    [hosts.h1]
    address = "1.2.3.4"
    user = "u1"

    [defaults.myhost]
    default_device = "d1"
    default_target = "h1"
    """
    config_file.write_text(toml_content)
    
    mocker.patch("bt_switch.config.user_config_path", return_value=config_dir)
    
    config = load_config()
    assert config.devices["d1"].name == "Test Device"
    assert config.hosts["h1"].user == "u1"
