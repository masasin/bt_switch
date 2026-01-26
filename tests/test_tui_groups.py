import pytest
from textual.pilot import Pilot
from unittest.mock import MagicMock, patch

from bt_switch.tui import BtSwitchApp, GroupsView, AddGroupScreen
from bt_switch.config_service import ConfigService

@pytest.fixture
def mock_config_service():
    svc = MagicMock(spec=ConfigService)
    svc.list_groups.return_value = {"group1": ["dev1", "dev2"]}
    svc.list_devices.return_value = {"dev1": MagicMock(), "dev2": MagicMock()}
    svc.list_defaults.return_value = {}
    svc.list_hosts.return_value = {}
    return svc

@pytest.mark.asyncio
async def test_groups_view_render(mock_config_service):
    app = BtSwitchApp()
    app.config_service = mock_config_service
    
    async with app.run_test() as pilot:
        # Switch to Groups tab
        await pilot.click("#tab-groups")
        
        # Check table
        table = app.query_one("GroupsView DataTable")
        assert table.row_count == 1
        assert "group1" in table.rows

@pytest.mark.asyncio
async def test_add_group_screen(mock_config_service):
    app = BtSwitchApp()
    app.config_service = mock_config_service
    
    async with app.run_test() as pilot:
        await pilot.click("#tab-groups")
        await pilot.click("#groups-add")
        
        # Screen should be up
        assert isinstance(app.screen, AddGroupScreen)
        
        # Fill form
        await pilot.click("#input-alias")
        await pilot.press(*"new_group")
        await pilot.click("#input-devices")
        await pilot.press(*"dev1,dev2")
        
        await pilot.click("#btn-submit")
        
        # Check call
        mock_config_service.add_group.assert_called_with("new_group", ["dev1", "dev2"])

