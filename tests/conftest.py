import pytest

from bt_switch.models import AppConfig, DefaultSettings, Device, Host


@pytest.fixture
def mock_subprocess(mocker):
    """Mocks subprocess.run for all tests."""
    return mocker.patch("subprocess.run")

@pytest.fixture
def sample_config():
    """Returns a valid AppConfig object for testing."""
    return AppConfig(
        devices={
            "headphones": Device(mac="00:11:22:33:44:55", name="Test Headphones"),
            "mouse": Device(mac="AA:BB:CC:DD:EE:FF", name="Test Mouse"),
        },
        hosts={
            "desktop": Host(address="192.168.1.10", user="jean", protocol="ssh"),
            "laptop": Host(address="localhost", user="jean", protocol="local"),
        },
        defaults={
            "laptop": DefaultSettings(default_device="headphones", default_target="desktop"),
        },
    )
