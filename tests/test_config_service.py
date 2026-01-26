import pytest

from bt_switch.config_service import ConfigService
from bt_switch.exceptions import ConfigurationError


@pytest.fixture
def config_file(tmp_path):
    f = tmp_path / "config.toml"
    return f

@pytest.fixture
def service(config_file):
    return ConfigService(config_path=config_file)

def test_empty_config(service):
    assert service.list_devices() == {}
    assert service.list_hosts() == {}
    assert service.list_defaults() == {}

# --- Devices ---

def test_add_device(service, config_file):
    service.add_device("headphones", "00:11:22:33:44:55", "My Headphones")
    
    devices = service.list_devices()
    assert "headphones" in devices
    assert devices["headphones"].mac == "00:11:22:33:44:55"
    assert devices["headphones"].name == "My Headphones"

    # Verify file content
    content = config_file.read_text()
    assert 'mac = "00:11:22:33:44:55"' in content

def test_add_device_duplicate(service):
    service.add_device("d1", "aa", "n1")
    with pytest.raises(ConfigurationError, match="already exists"):
        service.add_device("d1", "bb", "n2")

def test_remove_device(service):
    service.add_device("d1", "aa", "n1")
    service.remove_device("d1")
    assert "d1" not in service.list_devices()

def test_remove_device_not_found(service):
    with pytest.raises(ConfigurationError, match="not found"):
        service.remove_device("nonexistent")

# --- Hosts ---

def test_add_host(service):
    service.add_host("h1", address="1.2.3.4", user="root", protocol="ssh")
    
    hosts = service.list_hosts()
    assert "h1" in hosts
    assert hosts["h1"].address == "1.2.3.4"
    assert hosts["h1"].protocol == "ssh"

def test_add_host_duplicate(service):
    service.add_host("h1", address="1.1.1.1", user="u")
    with pytest.raises(ConfigurationError, match="already exists"):
        service.add_host("h1", address="2.2.2.2", user="u")

def test_remove_host(service):
    service.add_host("h1", address="1.1.1.1", user="u")
    service.remove_host("h1")
    assert "h1" not in service.list_hosts()

# --- Defaults ---

def test_set_default(service):
    # Setup deps
    service.add_device("d1", "aa", "n1")
    service.add_host("h1", address="1.1", user="u")
    
    service.set_default("myhost", default_device="d1", default_target="h1")
    
    defaults = service.list_defaults()
    assert "myhost" in defaults
    assert defaults["myhost"].default_device == "d1"
    assert defaults["myhost"].default_target == "h1"

def test_set_default_invalid_refs(service):
    with pytest.raises(ConfigurationError, match="Device or Group 'd1' not found"):
        service.set_default("host", default_device="d1", default_target="h1")

    service.add_device("d1", "aa", "n1")
    with pytest.raises(ConfigurationError, match="Host 'h1' not found"):
        service.set_default("host", default_device="d1", default_target="h1")

def test_remove_default(service):
    service.add_device("d1", "aa", "n1")
    service.add_host("h1", address="1.1", user="u")
    service.set_default("myhost", default_device="d1", default_target="h1")
    
    service.remove_default("myhost")
    assert "myhost" not in service.list_defaults()

def test_preserves_comments(config_file):
    # Create file with comments
    initial = """
    # This is a comment
    [devices.d1] # Inline comment
    mac = "aa" 
    name = "n1"
    """
    config_file.write_text(initial)
    
    svc = ConfigService(config_file)
    svc.add_device("d2", "bb", "n2") # Add new item
    
    content = config_file.read_text()
    assert "# This is a comment" in content
    assert "# Inline comment" in content
    assert "mac = \"bb\"" in content

def test_add_device_conflict_with_group(service):
    service.add_device("d1", "aa", "n1")
    service.add_group("g1", ["d1"])
    
    with pytest.raises(ConfigurationError, match="Group 'g1' already exists"):
        service.add_device("g1", "bb", "n2")

def test_add_group_conflict_with_device(service):
    service.add_device("d1", "aa", "n1")
    
    with pytest.raises(ConfigurationError, match="Device 'd1' already exists"):
        service.add_group("d1", ["d1"])

def test_set_default_with_group(service):
    service.add_device("d1", "aa", "n1")
    service.add_group("g1", ["d1"])
    service.add_host("h1", address="1.1", user="u")
    
    # Should succeed for a group
    service.set_default("myhost", default_device="g1", default_target="h1")
    
    defaults = service.list_defaults()
    assert defaults["myhost"].default_device == "g1"

def test_set_default_invalid_device_or_group(service):
    service.add_host("h1", address="1.1", user="u")
    with pytest.raises(ConfigurationError, match="Device or Group 'foo' not found"):
        service.set_default("myhost", default_device="foo", default_target="h1")

