import pytest
from textual.app import App
from bt_switch.tui import BtSwitchApp, DevicesView, HostsView, Dashboard
from unittest.mock import MagicMock, Mock


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

@pytest.fixture
def mock_config_service_with_defaults(mocker):
    svc = MagicMock()
    
    d1 = Mock(mac="00:11", name="headphones")
    d2 = Mock(mac="00:22", name="speaker")
    d3 = Mock(mac="00:33", name="car")
    
    devices = {
        "headphones-alias": d1,
        "speaker-alias": d2,
        "car-alias": d3,
    }
    svc.list_devices.return_value = devices
    
    h1 = Mock(address="1.1", user="u", protocol="ssh", driver_type="bluez", name="h1")
    h2 = Mock(address="2.2", user="u2", protocol="ssh", driver_type="bluez", name="h2")
    hosts = {"h1": h1, "h2": h2}
    svc.list_hosts.return_value = hosts
    
    defaults_obj = Mock()
    defaults_obj.default_device = "speaker-alias"
    defaults_obj.default_target = "h2"
    
    import socket
    hostname = socket.gethostname()
    svc.list_defaults.return_value = {hostname: defaults_obj}
    
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

@pytest.mark.asyncio
async def test_default_device_selected_on_load(mock_config_service_with_defaults):
    app = BtSwitchApp()
    app.config_service = mock_config_service_with_defaults
    
    async with app.run_test() as pilot:
        dashboard = app.query_one(Dashboard)
        devices_table = dashboard.query_one("#dashboard-devices")
        
        expected_row_index = 1
        
        assert devices_table.cursor_row == expected_row_index
        
        assert dashboard.selected_device == "speaker-alias"
        

@pytest.mark.asyncio
async def test_default_device_selected_on_devices_tab(mock_config_service_with_defaults):
    app = BtSwitchApp()
    app.config_service = mock_config_service_with_defaults
    
    async with app.run_test() as pilot:
        tabs = app.query_one("TabbedContent")
        tabs.active = "tab-devices"
        await pilot.pause()

        devices_view = app.query_one(DevicesView)
        devices_table = devices_view.query_one("#devices-table")
        
        expected_row_index = 1
        
        assert devices_table.cursor_row == expected_row_index
        
        assert devices_view.selected_row == "speaker-alias"
