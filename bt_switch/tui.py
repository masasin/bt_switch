import socket

from loguru import logger
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    TabbedContent,
    TabPane,
)

from .config import get_config_path
from .config_service import ConfigService
from .driver import DriverFactory
from .models import Host
from .service import SwitchService


class TextualLogger:
    def __init__(self, rich_log: RichLog):
        self.rich_log = rich_log

    def write(self, message):
        self.rich_log.write(message)

    def flush(self):
        pass


class DeviceSelectorMixin:
    def _refresh_devices_table(self, table: DataTable, config_service: ConfigService) -> str | None:
        table.clear(columns=True)
        table.add_columns("Alias", "Name", "MAC")
        table.cursor_type = "row"
        
        hostname = socket.gethostname()
        defaults_map = config_service.list_defaults()
        local_defaults = defaults_map.get(hostname)
        default_device_alias = local_defaults.default_device if local_defaults else None
        
        devices = config_service.list_devices()
        device_items = list(devices.items())
        default_row_index = -1

        for i, (alias, dev) in enumerate(device_items):
            name_display = dev.name
            if default_device_alias and default_device_alias == alias:
                name_display = f"{dev.name} [bold green](Default)[/]"
                default_row_index = i
            
            table.add_row(alias, name_display, dev.mac, key=alias)

        if default_row_index != -1:
            table.move_cursor(row=default_row_index)
            return default_device_alias
        
        if device_items:
            return device_items[0][0]

        return None


class Dashboard(Container, DeviceSelectorMixin):
    def __init__(self, config_service: ConfigService):
        super().__init__()
        self.config_service = config_service
        self.selected_target = None
        self.selected_device = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="controls"):
            with Vertical(classes="column"):
                yield Label("Devices", classes="section-title")
                yield DataTable(id="dashboard-devices")
            
            with Vertical(classes="column"):
                yield Label("Target Host", classes="section-title")
                yield Select([], id="target-select", prompt="Select Target")
                
                yield Label("Actions", classes="section-title")
                yield Button("Switch", id="btn-switch", variant="primary")
                yield Button("Push", id="btn-push", variant="warning")
                yield Button("Pull", id="btn-pull", variant="success")

        yield Label("Logs", classes="section-title")
        yield RichLog(id="logs", highlight=True, markup=True)

    def on_mount(self):
        self.refresh_data()
        
        log_widget = self.query_one("#logs", RichLog)
        logger.remove()
        logger.add(TextualLogger(log_widget), format="{time:HH:mm:ss} | {level} | {message}")

    def refresh_data(self):
        hostname = socket.gethostname()
        defaults_map = self.config_service.list_defaults()
        local_defaults = defaults_map.get(hostname)

        table = self.query_one("#dashboard-devices", DataTable)
        self.selected_device = self._refresh_devices_table(table, self.config_service)

        select = self.query_one("#target-select", Select)
        hosts = self.config_service.list_hosts()
        options = [(f"{alias} ({h.address})", alias) for alias, h in hosts.items()]
        select.set_options(options)
        
        if local_defaults and local_defaults.default_target:
             select.value = local_defaults.default_target

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if event.data_table.id == "dashboard-devices":
            self.selected_device = event.row_key.value

    def on_select_changed(self, event: Select.Changed):
        self.selected_target = event.value

    @work(exclusive=True, thread=True)
    def run_switch_operation(self, operation: str):
        log = self.query_one("#logs", RichLog)

        if not self.selected_device:
            self.app.call_from_thread(log.write, "[bold red]No device selected![/]")
            return
        
        if not self.selected_target:
            self.app.call_from_thread(log.write, "[bold red]No target host selected![/]")
            return
            
        try:
            self.app.call_from_thread(log.write, f"[bold blue]Starting {operation.upper()}...[/]")
            
            config = self.config_service.load()
            
            device_obj = config.devices[self.selected_device]
            remote_host_cfg = config.hosts[self.selected_target]
            
            local_driver = DriverFactory.create(
                Host(address="localhost", user="", protocol="local", driver_type="bluez"), 
                is_local=True
            )
            remote_driver = DriverFactory.create(
                remote_host_cfg, 
                is_local=False
            )
            
            service = SwitchService(local_driver, remote_driver, device_obj, self.selected_target)
            
            if operation == "switch":
                service.run()
            elif operation == "push":
                service._handle_push()
            elif operation == "pull":
                service._handle_pull()
                
            self.app.call_from_thread(log.write, f"[bold green]{operation.upper()} Complete![/]")
            
        except Exception as e:
            self.app.call_from_thread(log.write, f"[bold red]Error: {e}[/]")
            
    def on_button_pressed(self, event: Button.Pressed):
        op_map = {
            "btn-switch": "switch",
            "btn-push": "push",
            "btn-pull": "pull"
        }
        if event.button.id in op_map:
            self.run_switch_operation(op_map[event.button.id])




class AddDeviceScreen(ModalScreen):
    CSS = """
    AddDeviceScreen {
        align: center middle;
    }
    
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: auto;
        padding: 0 1;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        column-span: 2;
        height: 1;
        width: 100%;
        content-align: center middle;
        text-style: bold;
    }
    
    Label {
        column-span: 1;
        height: 3;
        content-align: right middle;
    }
    
    Input {
        column-span: 1;
        width: 100%;
    }
    
    #buttons {
        column-span: 2;
        height: auto;
        align: right bottom;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Add Device", id="title"),
            Label("Alias:"),
            Input(placeholder="e.g. headphones", id="input-alias"),
            Label("MAC:"),
            Input(placeholder="00:11:22:33:44:55", id="input-mac"),
            Label("Name:"),
            Input(placeholder="Friendly Name", id="input-name"),
            Horizontal(
                Button("Cancel", variant="error", id="btn-cancel"),
                Button("Add", variant="success", id="btn-submit"),
                id="buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-submit":
            alias = self.query_one("#input-alias", Input).value
            mac = self.query_one("#input-mac", Input).value
            name = self.query_one("#input-name", Input).value
            
            if alias and mac and name:
                self.dismiss((alias, mac, name))
            else:
                self.notify("All fields are required.", severity="error")
                
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

class AddHostScreen(ModalScreen):
    CSS = """
    AddHostScreen {
        align: center middle;
    }
    
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: auto;
        padding: 0 1;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        column-span: 2;
        height: 1;
        width: 100%;
        content-align: center middle;
        text-style: bold;
    }
    
    Label {
        column-span: 1;
        height: 3;
        content-align: right middle;
    }
    
    Input {
        column-span: 1;
        width: 100%;
    }
    
    #buttons {
        column-span: 2;
        height: auto;
        align: right bottom;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Add Host", id="title"),
            Label("Alias:"),
            Input(placeholder="e.g. desktop", id="input-alias"),
            Label("Address:"),
            Input(placeholder="Hostname or IP", id="input-address"),
            Label("User:"),
            Input(placeholder="Username", id="input-user"),
            Horizontal(
                Button("Cancel", variant="error", id="btn-cancel"),
                Button("Add", variant="success", id="btn-submit"),
                id="buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-submit":
            alias = self.query_one("#input-alias", Input).value
            address = self.query_one("#input-address", Input).value
            user = self.query_one("#input-user", Input).value
            
            if alias and address and user:
                self.dismiss((alias, address, user))
            else:
                self.notify("All fields are required.", severity="error")
                
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


class ConfigView(Container):
    def __init__(self, config_service: ConfigService, id_prefix: str):
        super().__init__()
        self.config_service = config_service
        self.id_prefix = id_prefix
        self.selected_row = None

    def compose_content(self) -> ComposeResult:
        yield Label("Table Base")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title, classes="section-title")
            
            yield DataTable(id=f"{self.id_prefix}-table", cursor_type="row")
            
            with Horizontal(classes="buttons-row"):
                yield Button("Refresh", id=f"{self.id_prefix}-refresh")
                yield Button("Add", id=f"{self.id_prefix}-add", variant="primary")
                yield Button("Remove", id=f"{self.id_prefix}-remove", variant="error")

    def on_mount(self):
        self.refresh_data()

    def refresh_data(self):
        pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if event.data_table.id == f"{self.id_prefix}-table":
            self.selected_row = event.row_key.value

class DevicesView(ConfigView, DeviceSelectorMixin):
    title = "Devices"

    def __init__(self, config_service: ConfigService):
        super().__init__(config_service, "devices")

    def refresh_data(self):
        table = self.query_one("#devices-table", DataTable)
        self.selected_row = self._refresh_devices_table(table, self.config_service)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "devices-refresh":
            self.refresh_data()
        elif event.button.id == "devices-remove":
            if self.selected_row:
                try:
                    self.config_service.remove_device(self.selected_row)
                    self.notify(f"Device '{self.selected_row}' removed")
                    self.refresh_data()
                    self.selected_row = None
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        elif event.button.id == "devices-add":
            def hande_add(result):
                if result:
                    alias, mac, name = result
                    try:
                        self.config_service.add_device(alias, mac, name)
                        self.notify(f"Device '{alias}' added")
                        self.refresh_data()
                    except Exception as e:
                        self.notify(f"Error adding device: {e}", severity="error")
            
            self.app.push_screen(AddDeviceScreen(id="add-device-screen"), hande_add)

class HostsView(ConfigView):
    title = "Hosts"

    def __init__(self, config_service: ConfigService):
        super().__init__(config_service, "hosts")

    def refresh_data(self):
        table = self.query_one("#hosts-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Alias", "Address", "User", "Protocol")
        
        hosts = self.config_service.list_hosts()
        for alias, h in hosts.items():
            table.add_row(alias, h.address, h.user, h.protocol, key=alias)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "hosts-refresh":
            self.refresh_data()
        elif event.button.id == "hosts-remove":
            if self.selected_row:
                try:
                    self.config_service.remove_host(self.selected_row)
                    self.notify(f"Host '{self.selected_row}' removed")
                    self.refresh_data()
                    self.selected_row = None
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        elif event.button.id == "hosts-add":
             def hande_add(result):
                if result:
                    alias, address, user = result
                    try:
                        self.config_service.add_host(alias, address=address, user=user)
                        self.notify(f"Host '{alias}' added")
                        self.refresh_data()
                    except Exception as e:
                        self.notify(f"Error adding host: {e}", severity="error")
            
             self.app.push_screen(AddHostScreen(id="add-host-screen"), hande_add)


class AddDefaultScreen(ModalScreen):
    CSS = """
    AddDefaultScreen {
        align: center middle;
    }
    
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: auto;
        padding: 0 1;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        column-span: 2;
        height: 1;
        width: 100%;
        content-align: center middle;
        text-style: bold;
    }
    
    Label {
        column-span: 1;
        height: 3;
        content-align: right middle;
    }
    
    Input, Select {
        column-span: 1;
        width: 100%;
    }
    
    #buttons {
        column-span: 2;
        height: auto;
        align: right bottom;
        margin-top: 1;
    }
    """

    def __init__(self, config_service: ConfigService, initial_hostname: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config_service = config_service
        self.initial_hostname = initial_hostname

    def compose(self) -> ComposeResult:
        devices = self.config_service.list_devices()
        device_options = [(f"{d.name} ({alias})", alias) for alias, d in devices.items()]
        
        hosts = self.config_service.list_hosts()
        host_options = [(alias, alias) for alias in hosts.keys()]

        defaults = self.config_service.list_defaults()
        unique_hostnames = {socket.gethostname()} | set(defaults.keys())
        hostname_options = [(h, h) for h in sorted(list(unique_hostnames))]

        # Pre-select based on initial_hostname if provided, otherwise current hostname
        default_hostname = self.initial_hostname or socket.gethostname()
        
        # Pre-fetch existing values if editing
        initial_device = Select.BLANK
        initial_target = Select.BLANK
        if self.initial_hostname and self.initial_hostname in defaults:
            initial_device = defaults[self.initial_hostname].default_device
            initial_target = defaults[self.initial_hostname].default_target

        yield Grid(
            Label("Add/Edit Default Settings", id="title"),
            Label("Hostname:"),
            Select(hostname_options, value=default_hostname, id="select-hostname"),
            Label("Device:"),
            Select(device_options, value=initial_device, prompt="Choose Device", id="select-device"),
            Label("Target:"),
            Select(host_options, value=initial_target, prompt="Choose Target", id="select-target"),
            Horizontal(
                Button("Cancel", variant="error", id="btn-cancel"),
                Button("Add/Edit", variant="success", id="btn-submit"),
                id="buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-submit":
            hostname = self.query_one("#select-hostname", Select).value
            device = self.query_one("#select-device", Select).value
            target = self.query_one("#select-target", Select).value
            
            if hostname != Select.BLANK and device != Select.BLANK and target != Select.BLANK:
                self.dismiss((hostname, device, target))
            else:
                self.notify("All fields are required.", severity="error")
                
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


class DefaultsView(ConfigView):
    title = "Defaults"

    def __init__(self, config_service: ConfigService):
        super().__init__(config_service, "defaults")

    def on_mount(self):
        super().on_mount()
        self.query_one("#defaults-add", Button).label = "Add/Edit"

    def refresh_data(self):
        table = self.query_one("#defaults-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Hostname", "Default Device", "Default Target")
        
        defaults_map = self.config_service.list_defaults()
        for host, settings in defaults_map.items():
            table.add_row(host, settings.default_device, settings.default_target, key=host)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "defaults-refresh":
            self.refresh_data()
        elif event.button.id == "defaults-remove":
            if self.selected_row:
                try:
                    self.config_service.remove_default(self.selected_row)
                    self.notify(f"Defaults for '{self.selected_row}' removed")
                    self.refresh_data()
                    self.selected_row = None
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        elif event.button.id == "defaults-add":
            def handle_add(result):
                if result:
                    hostname, device, target = result
                    try:
                        self.config_service.set_default(
                            hostname, 
                            default_device=device, 
                            default_target=target
                        )
                        self.notify("Defaults updated")
                        self.refresh_data()
                    except Exception as e:
                        self.notify(f"Error updating defaults: {e}", severity="error")
            
            self.app.push_screen(AddDefaultScreen(self.config_service, initial_hostname=self.selected_row), handle_add)

class BtSwitchApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    
    .section-title {
        text-style: bold;
        margin: 1 0;
    }
    
    #controls {
        height: auto;
        margin-bottom: 2;
    }
    
    .column {
        width: 1fr;
        padding: 1;
    }
    
    #logs {
        height: 1fr;
        border: solid gray;
        background: $surface;
    }
    
    .buttons-row {
        height: auto;
        align: right middle;
    }
    """
    
    TITLE = "bt-switch"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def __init__(self):
        super().__init__()
        self.config_service = ConfigService(get_config_path())

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Dashboard", id="tab-dashboard"):
                yield Dashboard(self.config_service)
            
            with TabPane("Devices", id="tab-devices"):
                yield DevicesView(self.config_service)
                
            with TabPane("Hosts", id="tab-hosts"):
                yield HostsView(self.config_service)

            with TabPane("Defaults", id="tab-defaults"):
                 yield DefaultsView(self.config_service)

        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark
