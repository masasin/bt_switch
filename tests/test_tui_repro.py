import pytest
from textual.app import App
from bt_switch.tui import BtSwitchApp, Dashboard, DefaultsView

@pytest.mark.asyncio
async def test_app_crash_repro():
    """
    Regression test for the crash where Dashboard tried to query #defaults-table 
    which was not in its hierarchy.
    """
    app = BtSwitchApp()
    async with app.run_test() as pilot:
        # Check that both main tabs are present
        assert pilot.app.query_one("Dashboard")
        # DefaultsView might be lazy loaded or just present in the DOM
        # We navigate to it to ensure it mounts and refreshes data
        
        # Note: TabbedContent switches usually require interaction or programmatically setting active
        tabs = pilot.app.query_one("TabbedContent")
        tabs.active = "tab-defaults"
        await pilot.pause() # Allow events to process
        
        assert pilot.app.query_one("DefaultsView")
        assert pilot.app.query_one("#defaults-table")
        
        # Switch back
        tabs.active = "tab-dashboard"
        await pilot.pause()
        assert pilot.app.query_one("Dashboard")

