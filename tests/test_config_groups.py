from pathlib import Path

import pytest
from bt_switch.config_service import ConfigService
from bt_switch.exceptions import ConfigurationError

@pytest.fixture
def config_service(tmp_path):
    config_path = tmp_path / "config.toml"
    return ConfigService(config_path)

def test_add_list_remove_group(config_service):
    # Setup devices first
    config_service.add_device("dev1", "00:11:22:33:44:55", "Device 1")
    config_service.add_device("dev2", "AA:BB:CC:DD:EE:FF", "Device 2")
    
    # Add Group
    config_service.add_group("my_group", ["dev1", "dev2"])
    
    # List Groups
    groups = config_service.list_groups()
    assert len(groups) == 1
    assert "my_group" in groups
    assert groups["my_group"] == ["dev1", "dev2"]
    
    # Remove Group
    config_service.remove_group("my_group")
    groups = config_service.list_groups()
    assert len(groups) == 0

def test_add_group_duplicate(config_service):
    config_service.add_device("dev1", "00:11:22:33:44:55", "Device 1")
    config_service.add_group("group1", ["dev1"])
    
    with pytest.raises(ConfigurationError, match="Group 'group1' already exists"):
        config_service.add_group("group1", ["dev1"])

def test_add_group_invalid_device(config_service):
    with pytest.raises(ConfigurationError, match="Device 'fake_dev' not found"):
        config_service.add_group("group1", ["fake_dev"])

def test_remove_group_not_found(config_service):
    with pytest.raises(ConfigurationError, match="Group 'fake_group' not found"):
        config_service.remove_group("fake_group")
