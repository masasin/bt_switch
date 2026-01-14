import pytest
from textual.app import App
from bt_switch.tui import BtSwitchApp, DevicesView, HostsView

@pytest.fixture
def mock_config_service(mocker):
    svc = mocker.MagicMock()
    d1 = mocker.Mock(mac="00:11")
    d1.name = "Dev1"
    svc.list_devices.return_value = {"d1": d1}
    
    h1 = mocker.Mock(address="1.1", user="u", protocol="ssh", driver_type="bluez")
    h1.name = "h1" 
    svc.list_hosts.return_value = {"h1": h1}
    
    defaults_obj = mocker.Mock()
    defaults_obj.default_target = None 
    defaults_obj.default_device = None
    svc.list_defaults.return_value = {"jean-lenovo": defaults_obj}
    
    return svc

@pytest.mark.asyncio
async def test_devices_view_compose(mock_config_service):
    view = DevicesView(mock_config_service)
    app = App()
    async with app.run_test() as pilot:
        await app.mount(view)
        assert app.query_one("DevicesView")
        assert app.query_one("#devices-table")
        assert app.query_one("#devices-add")
        assert app.query_one("#devices-remove")

@pytest.mark.asyncio
async def test_hosts_view_compose(mock_config_service):
    view = HostsView(mock_config_service)
    app = App()
    async with app.run_test() as pilot:
        await app.mount(view)
        assert app.query_one("HostsView")
        assert app.query_one("#hosts-table")

@pytest.mark.asyncio
async def test_add_device_flow(mock_config_service):
    app = BtSwitchApp()
    app.config_service = mock_config_service
    
    async with app.run_test() as pilot:
        tabs = app.query_one("TabbedContent")
        tabs.active = "tab-devices"
        await pilot.pause()
        
        await pilot.click("#devices-add")
        await pilot.pause()
        
        assert app.screen.id == "add-device-screen"
        
        await pilot.click("#input-alias")
        await pilot.press(*"new-dev")
        
        await pilot.click("#input-mac")
        await pilot.press(*"AA:BB")
        
        await pilot.click("#input-name")
        await pilot.press(*"New Device")
        
        await pilot.click("#btn-submit")
        await pilot.pause()
        
        mock_config_service.add_device.assert_called_with("new-dev", "AA:BB", "New Device")
        
