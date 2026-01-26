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
         patch("bt_switch.tui.DriverFactory") as MockFactory, \
         patch("bt_switch.tui.BatchSwitchService") as MockBatchService, \
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
            dashboard.selected_devices.add("dev1")
            dashboard.selected_target = "host1"

            # Click Switch button
            await pilot.click("#btn-switch")

            # Wait for worker
            await pilot.pause() 
            await pilot.pause()
            
            # Verify instantiation
            assert MockBatchService.call_count == 1
            MockBatchService.return_value.run.assert_called_with("switch")

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
            dashboard.selected_devices.add("dev1")
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

@pytest.mark.asyncio
async def test_dashboard_multi_select_logic(mock_config):
    # Setup mock config with a group
    mock_config.groups = {"g1": ["dev1"]}
    
    with patch("bt_switch.tui.ConfigService") as MockService, \
         patch("socket.gethostname", return_value="localhost"):
        service_instance = MockService.return_value
        service_instance.list_devices.return_value = mock_config.devices
        service_instance.list_hosts.return_value = mock_config.hosts
        service_instance.list_defaults.return_value = mock_config.defaults
        service_instance.list_groups.return_value = mock_config.groups
        service_instance.load.return_value = mock_config

        app = BtSwitchApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            
            dashboard = pilot.app.query_one("Dashboard")
            table = dashboard.query_one("#dashboard-devices")
            
            # Simulate clicking the row for 'dev1'
            # Note: TUI table clicks rely on coordinates, but we can simulate the event handler logic 
            # or use pilot.click if we know the selector.
            # Row keys are aliases.
            
            # Programmatic check first:
            # The dashboard should have an attribute for selected_devices
            # But the attribute doesn't exist yet in the code, so this test will fail until implemented.
            # We assume the implementation will add 'selected_devices' set.
            
            # Trigger row selection
            # Mock event structure: DataTable.RowSelected(table, row_key)
            # Textual's DataTable.RowKey is a class or string wrapper often.
            # But we can just call the handler directly with a mocked event object to avoid constructor issues.
            
            mock_event = MagicMock()
            mock_event.data_table = table
            mock_event.row_key = MagicMock()
            mock_event.row_key.value = "dev1"
            
            dashboard.on_data_table_row_selected(mock_event)
            
            # Expect dev1 to be in selected_devices
            assert "dev1" in dashboard.selected_devices
            
            # Select again to toggle off
            dashboard.on_data_table_row_selected(mock_event)
            assert "dev1" not in dashboard.selected_devices

@pytest.mark.asyncio
async def test_dashboard_group_select_logic(mock_config):
    mock_config.groups = {"g1": ["dev1"]}
    mock_config.devices["dev2"] = Device(name="Device 2", mac="XX")
    mock_config.groups["g2"] = ["dev1", "dev2"]

    with patch("bt_switch.tui.ConfigService") as MockService, \
         patch("socket.gethostname", return_value="localhost"):
        service_instance = MockService.return_value
        service_instance.list_devices.return_value = mock_config.devices
        service_instance.list_hosts.return_value = mock_config.hosts
        service_instance.list_defaults.return_value = mock_config.defaults
        service_instance.list_groups.return_value = mock_config.groups
        
        app = BtSwitchApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            
            dashboard = pilot.app.query_one("Dashboard")
            group_select = dashboard.query_one("#dashboard-groups")
            
            # Simulate selecting group g2
            # Set value directly to trigger event if possible, or call handler
            group_select.value = "g2"
            
            # Wait for event? Textual events are async.
            await pilot.pause()
            
            # Check selected devices
            assert "dev1" in dashboard.selected_devices
            assert "dev2" in dashboard.selected_devices

