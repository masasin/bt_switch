from pydantic import ValidationError
import pytest
from bt_switch.models import Device, Host, DefaultSettings, AppConfig

def test_device_model_valid():
    d = Device(mac="00:00:00:00:00:00", name="Test Device")
    assert d.mac == "00:00:00:00:00:00"
    assert d.name == "Test Device"

def test_device_model_missing_fields():
    with pytest.raises(ValidationError):
        Device(mac="00:00") # type: ignore

def test_host_model_defaults():
    h = Host(address="1.2.3.4", user="user")
    assert h.protocol == "ssh"
    assert h.driver_type == "bluez"

def test_host_model_invalid_protocol():
    with pytest.raises(ValidationError):
        Host(address="1.2.3.4", user="user", protocol="ftp") # type: ignore

def test_app_config_structure():
    config = AppConfig(
        devices={},
        hosts={},
        defaults={}
    )
    assert config.devices == {}
