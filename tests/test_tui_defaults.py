import socket

import pytest
from textual.app import App
from textual.widgets import Select

from bt_switch.tui import AddDefaultScreen, BtSwitchApp, DefaultsView


@pytest.fixture
def mock_config_service(mocker):
    svc = mocker.MagicMock()
    
    d1 = mocker.Mock(mac="00:11")
    d1.name = "headphones"
    svc.list_devices.return_value = {"h-alias": d1}
    
    h1 = mocker.Mock(address="1.1", user="u", protocol="ssh", driver_type="bluez")
    svc.list_hosts.return_value = {"host-alias": h1}
    
    def_obj = mocker.Mock()
    def_obj.default_device = "h-alias"
    def_obj.default_target = "host-alias"
    svc.list_defaults.return_value = {"some-host": def_obj}
    
    return svc


@pytest.mark.asyncio
async def test_defaults_view_compose(mock_config_service):
    view = DefaultsView(mock_config_service)
    app = App()
    async with app.run_test():
        await app.mount(view)
        assert app.query_one("DefaultsView")
        assert app.query_one("#defaults-table")
        assert app.query_one("#defaults-add")
        assert app.query_one("#defaults-remove")


@pytest.mark.asyncio
async def test_add_default_flow(mock_config_service):
    app = BtSwitchApp()
    app.config_service = mock_config_service
    
    async with app.run_test() as pilot:
        tabs = app.query_one("TabbedContent")
        tabs.active = "tab-defaults"
        await pilot.pause()
        
        await pilot.click("#defaults-add")
        await pilot.pause()
        
        assert isinstance(app.screen, AddDefaultScreen)
        
        # Set values directly to be more robust in tests
        app.screen.query_one("#select-hostname", Select).value = socket.gethostname()
        app.screen.query_one("#select-device", Select).value = "h-alias"
        app.screen.query_one("#select-target", Select).value = "host-alias"
        await pilot.pause()
        
        # Verify values are set
        assert app.screen.query_one("#select-hostname", Select).value == socket.gethostname()
        assert app.screen.query_one("#select-device", Select).value == "h-alias"
        assert app.screen.query_one("#select-target", Select).value == "host-alias"
        
        await pilot.click("#btn-submit")
        await pilot.pause()
        await pilot.pause() # Extra pause for dismissal processing
        
        hostname = socket.gethostname()
        mock_config_service.set_default.assert_called_with(
            hostname, 
            default_device="h-alias", 
            default_target="host-alias"
        )


@pytest.mark.asyncio
async def test_remove_default_flow(mock_config_service):
    app = BtSwitchApp()
    app.config_service = mock_config_service
    
    async with app.run_test() as pilot:
        tabs = app.query_one("TabbedContent")
        tabs.active = "tab-defaults"
        await pilot.pause()
        
        view = app.query_one(DefaultsView)
        # Set selected_row directly
        view.selected_row = "some-host"
        
        await pilot.click("#defaults-remove")
        await pilot.pause()
        
        mock_config_service.remove_default.assert_called_with("some-host")
