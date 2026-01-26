import pytest
from textual.pilot import Pilot
from bt_switch.tui import BtSwitchApp, AddDeviceScreen, AddHostScreen
from unittest.mock import MagicMock

@pytest.fixture
def mock_config_service():
    svc = MagicMock()
    svc.list_devices.return_value = {}
    svc.list_hosts.return_value = {}
    svc.list_defaults.return_value = {}
    svc.list_groups.return_value = {}
    return svc

@pytest.mark.asyncio
async def test_add_device_screen_logic(mock_config_service):
    app = BtSwitchApp()
    app.config_service = mock_config_service
    
    async with app.run_test() as pilot:
        # Manually push screen to test it in isolation
        screen = AddDeviceScreen()
        await app.push_screen(screen)
        await pilot.pause()
        
        # Check inputs
        assert app.query_one("#input-alias")
        assert app.query_one("#input-mac")
        assert app.query_one("#input-name")
        
        # Fill and submit
        app.query_one("#input-alias").value = "test-dev"
        app.query_one("#input-mac").value = "00:00:00:00:00:00"
        app.query_one("#input-name").value = "Test Name"
        
        # Pilot click button
        await pilot.click("#btn-submit")
        await pilot.pause()
        
        # Screen should be dismissed
        assert not isinstance(app.screen, AddDeviceScreen)

@pytest.mark.asyncio
async def test_add_host_screen_logic(mock_config_service):
    app = BtSwitchApp()
    app.config_service = mock_config_service
    
    async with app.run_test() as pilot:
        screen = AddHostScreen()
        await app.push_screen(screen)
        await pilot.pause()
        
        assert app.query_one("#input-alias")
        assert app.query_one("#input-address")
        assert app.query_one("#input-user")
        
        app.query_one("#input-alias").value = "test-host"
        app.query_one("#input-address").value = "1.2.3.4"
        app.query_one("#input-user").value = "test-user"
        
        await pilot.click("#btn-submit")
        await pilot.pause()
        
        assert not isinstance(app.screen, AddHostScreen)
