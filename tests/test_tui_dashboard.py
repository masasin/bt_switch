from unittest.mock import MagicMock, patch

import pytest

from bt_switch.models import AppConfig, DefaultSettings, Device, Host
from bt_switch.tui import BtSwitchApp


@pytest.fixture
def mock_config():
    return AppConfig(
        devices={"dev1": Device(name="Device 1", mac="00:11:22:33:44:55")},
        hosts={"host1": Host(address="1.2.3.4", user="user1", protocol="ssh")},
        defaults={"localhost": DefaultSettings(default_device="dev1", default_target="host1")}
    )

@pytest.mark.asyncio
async def test_dashboard_buttons_start_workers(mock_config):
    with patch("bt_switch.tui.ConfigService") as MockService, \
         patch("socket.gethostname", return_value="localhost"):
        service_instance = MockService.return_value
        service_instance.list_devices.return_value = mock_config.devices
        service_instance.list_hosts.return_value = mock_config.hosts
        service_instance.list_defaults.return_value = mock_config.defaults
        service_instance.load.return_value = mock_config

        app = BtSwitchApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            
            dashboard = pilot.app.query_one("Dashboard")
            dashboard.selected_device = "dev1"
            dashboard.selected_target = "host1"
            
            # Click Switch button
            await pilot.click("#btn-switch")
            
            # Wait a bit for worker to start
            import asyncio
            for _ in range(50):
                if pilot.app.workers:
                    break
                await asyncio.sleep(0.01)
                
            assert len(pilot.app.workers) > 0

@pytest.mark.asyncio
async def test_dashboard_buttons_logging(mock_config):
    with patch("bt_switch.tui.ConfigService") as MockService, \
         patch("bt_switch.tui.DriverFactory"), \
         patch("bt_switch.tui.SwitchService"), \
         patch("socket.gethostname", return_value="localhost"):
        
        service_instance = MockService.return_value
        service_instance.list_devices.return_value = mock_config.devices
        service_instance.list_hosts.return_value = mock_config.hosts
        service_instance.list_defaults.return_value = mock_config.defaults
        service_instance.load.return_value = mock_config
        
        app = BtSwitchApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            
            dashboard = pilot.app.query_one("Dashboard")
            log = dashboard.query_one("#logs")
            
            # Mock log.write to capture calls
            log.write = MagicMock()
            
            # Ensure selections
            dashboard.selected_device = "dev1"
            dashboard.selected_target = "host1"
            
            # Click Push
            await pilot.click("#btn-push")
            
            # Wait for worker to start and finish
            import asyncio
            for _ in range(100):
                await asyncio.sleep(0.01)
                if not pilot.app.workers:
                    break
            
            # Verify logs via captured calls
            calls = [call.args[0] for call in log.write.call_args_list]
            log_content = "".join(calls)
            assert "Starting PUSH" in log_content
            assert "PUSH Complete" in log_content
