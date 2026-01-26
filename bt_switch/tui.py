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
    SelectionList,
    TabbedContent,
    TabPane,
)

from .config import get_config_path
from .config_service import ConfigService
from .driver import DriverFactory
from .models import Host
from .service import BatchSwitchService, SwitchService


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
        
        show_checks = (table.id == "dashboard-devices")
        if show_checks:
            table.add_column("Sel", width=3)
            
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
            
            row = [alias, name_display, dev.mac]
            if show_checks:
                is_selected = getattr(self, "selected_devices", set()) and alias in self.selected_devices
                check = "[x]" if is_selected else "[ ]"
                row.insert(0, check)

            table.add_row(*row, key=alias)

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
        self.selected_group = None
        self.selected_devices: set[str] = set()

    def compose(self) -> ComposeResult:
        with Horizontal(id="controls"):
            with Vertical(classes="column"):
                yield Label("Groups", classes="section-title")
                yield Select([], id="dashboard-groups", prompt="Select Group (Optional)")

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

        # Refresh Devices
        table = self.query_one("#dashboard-devices", DataTable)
        default_alias = self._refresh_devices_table(table, self.config_service)
        
        # Pre-select default device if nothing selected yet
        if not self.selected_devices and default_alias:
            self.selected_devices.add(default_alias)
            self.selected_device = default_alias
            # Re-refresh table to show checkbox
            self._refresh_devices_table(table, self.config_service)

        # Refresh Groups
        group_select = self.query_one("#dashboard-groups", Select)
        groups = self.config_service.list_groups()
        group_options = [(f"{alias} ({len(members)} devices)", alias) for alias, members in groups.items()]
        group_options.insert(0, ("(None)", "")) 
        group_select.set_options(group_options)
        
        # If the default is a group, handle it
        if not self.selected_target and local_defaults and local_defaults.default_device in groups:
             group_alias = local_defaults.default_device
             group_select.value = group_alias
             self.selected_group = group_alias
             self.selected_device = group_alias
             self.selected_devices = set(groups[group_alias])
             self._refresh_devices_table(table, self.config_service)
        else:
             group_select.value = Select.BLANK 
             self.selected_group = None
        # Refresh Hosts
        select = self.query_one("#target-select", Select)
        hosts = self.config_service.list_hosts()
        options = [(f"{alias} ({h.address})", alias) for alias, h in hosts.items()]
        select.set_options(options)
        
        if local_defaults and local_defaults.default_target:
             select.value = local_defaults.default_target

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if event.data_table.id == "dashboard-devices":
            alias = event.row_key.value
            
            if alias in self.selected_devices:
                self.selected_devices.remove(alias)
                if self.selected_device == alias:
                    self.selected_device = next(iter(self.selected_devices)) if self.selected_devices else None
            else:
                self.selected_devices.add(alias)
                self.selected_device = alias
            
            # Update visual row without full refresh to preserve cursor
            check = "[x]" if alias in self.selected_devices else "[ ]"
            event.data_table.update_cell(event.row_key, "Sel", check)

            # Deselect group in dropdown if manually interacting
            # We don't null self.selected_group because multiple devices might still match it,
            # but we clear the visual dropdown state.
            self.query_one("#dashboard-groups", Select).value = Select.BLANK

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "target-select":
            self.selected_target = event.value
        elif event.select.id == "dashboard-groups":
            val = event.value
            if val:
                self.selected_group = val
                # Select all members
                groups = self.config_service.list_groups()
                if val in groups:
                     self.selected_devices = set(groups[val])
                     # Filter only existing devices?
                     devices = self.config_service.list_devices()
                     self.selected_devices = {d for d in self.selected_devices if d in devices}
                
                # Refresh table visuals
                table = self.query_one("#dashboard-devices", DataTable)
                self._refresh_devices_table(table, self.config_service)
            else:
                self.selected_group = None
                # Clear selection? Or keep manual? 
                # "Remove the toast when a group is selected" -> Toast removed. 
                # If clearing group, maybe clear select?
                # User didn't specify behavior on deselect logic clearly, but implies Group Select -> Selects All.
                # If I select None, I'll clear.
                self.selected_devices = set()
                table = self.query_one("#dashboard-devices", DataTable)
                self._refresh_devices_table(table, self.config_service)

    @work(exclusive=True, thread=True)
    def run_switch_operation(self, operation: str):
        log = self.query_one("#logs", RichLog)

        if not self.selected_devices:
            self.app.call_from_thread(log.write, "[bold red]No devices selected![/]")
            return
        
        if not self.selected_target:
            self.app.call_from_thread(log.write, "[bold red]No target host selected![/]")
            return
            
        try:
            target_str = self.selected_target
            
            config = self.config_service.load()
            remote_host_cfg = config.hosts[target_str]
            
            # Setup Drivers
            local_driver = DriverFactory.create(
                Host(address="localhost", user="", protocol="local", driver_type="bluez"), 
                is_local=True
            )
            remote_driver = DriverFactory.create(
                remote_host_cfg, 
                is_local=False
            )

            devices = []
            for alias in self.selected_devices:
                if alias in config.devices:
                    devices.append(config.devices[alias])
            
            self.app.call_from_thread(log.write, f"[bold blue]Starting {operation.upper()} on {len(devices)} devices...[/]")
            
            service = BatchSwitchService(local_driver, remote_driver, devices, target_str)
            service.run(operation)

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


class AddDeviceScreen(ModalScreen):
    CSS = """
    AddDeviceScreen {
        align: center middle;
    }
    
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: auto;
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        column-span: 2;
        height: 3;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }
    
    Label {
        width: 100%;
        height: 3;
        content-align: right middle;
    }
    
    Input {
        width: 100%;
    }
    
    #buttons {
        column-span: 2;
        height: 5;
        align: right middle;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Add Device", id="title"),
            Label("Alias:"),
            Input(placeholder="e.g. headphones", id="input-alias"),
            Label("MAC:"),
            Input(placeholder="e.g. AA:BB:CC:DD:EE:FF", id="input-mac"),
            Label("Name:"),
            Input(placeholder="e.g. Sony WH-1000XM4", id="input-name"),
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
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        column-span: 2;
        height: 3;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }
    
    Label {
        width: 100%;
        height: 3;
        content-align: right middle;
    }
    
    Input {
        width: 100%;
    }
    
    #buttons {
        column-span: 2;
        height: 5;
        align: right middle;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Add Host", id="title"),
            Label("Alias:"),
            Input(placeholder="e.g. desktop", id="input-alias"),
            Label("Address:"),
            Input(placeholder="e.g. 192.168.1.10 or workstation.local", id="input-address"),
            Label("User:"),
            Input(placeholder="e.g. jean", id="input-user"),
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

class AddDefaultScreen(ModalScreen):
    CSS = """
    AddDefaultScreen {
        align: center middle;
    }
    
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: auto;
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        column-span: 2;
        height: 3;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }
    
    Label {
        width: 100%;
        height: 3;
        content-align: right middle;
    }
    
    Select {
        width: 100%;
    }
    
    #buttons {
        column-span: 2;
        height: 5;
        align: right middle;
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
        
        groups = self.config_service.list_groups()
        for alias, members in groups.items():
            device_options.append((f"{alias} (Group: {len(members)})", alias))
        
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

class AddGroupScreen(ModalScreen):
    CSS = """
    AddGroupScreen {
        align: center middle;
    }
    
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: auto;
        padding: 1 2;
        width: 70;
        max-height: 80vh;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        column-span: 2;
        height: 3;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: $text;
        margin-bottom: 1;
    }
    
    Label {
        width: 100%;
        height: 3;
        content-align: right middle;
    }
    
    Input {
        width: 100%;
    }
    
    SelectionList {
        column-span: 2;
        height: 10;
        border: solid $accent;
        margin: 1 0;
    }
    
    #buttons {
        column-span: 2;
        height: 5;
        align: right middle;
        margin-top: 1;
    }
    """

    def __init__(self, config_service: ConfigService, initial_alias: str | None = None, initial_members: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config_service = config_service
        self.initial_alias = initial_alias
        self.initial_members = set(initial_members) if initial_members else set()

    def compose(self) -> ComposeResult:
        devices = self.config_service.list_devices()
        
        # Build selection list
        selections = []
        for alias, dev in devices.items():
            label = f"{dev.name} ({alias})"
            is_selected = alias in self.initial_members
            selections.append((label, alias, is_selected))
        
        title = "Edit Group" if self.initial_alias else "Add Group"
        btn_label = "Update" if self.initial_alias else "Add"

        yield Grid(
            Label(title, id="title"),
            Label("Group Alias:"),
            Input(placeholder="e.g. desk", id="input-alias", value=self.initial_alias or ""),
            Label("Devices:"),
            SelectionList(*selections, id="input-devices"),
            Horizontal(
                Button("Cancel", variant="error", id="btn-cancel"),
                Button(btn_label, variant="success", id="btn-submit"),
                id="buttons"
            ),
            id="dialog"
        )
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-submit":
            alias = self.query_one("#input-alias", Input).value
            selected = self.query_one("#input-devices", SelectionList).selected
            
            if alias and selected:
                self.dismiss((alias, selected))
            else:
                self.notify("Alias and at least one device are required.", severity="error")
                
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

class GroupsView(ConfigView):
    title = "Groups"

    def __init__(self, config_service: ConfigService):
        super().__init__(config_service, "groups")

    def refresh_data(self):
        table = self.query_one("#groups-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Alias", "Devices")
        
        groups = self.config_service.list_groups()
        for alias, members in groups.items():
            table.add_row(alias, ", ".join(members), key=alias)

    def compose_content(self) -> ComposeResult:
        # Override to add Edit button? No, ConfigView structure is strict.
        # I need to edit ConfigView or override compose in GroupsView.
        # Let's override compose.
        pass

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title, classes="section-title")
            
            yield DataTable(id=f"{self.id_prefix}-table", cursor_type="row")
            
            with Horizontal(classes="buttons-row"):
                yield Button("Refresh", id=f"{self.id_prefix}-refresh")
                yield Button("Add", id=f"{self.id_prefix}-add", variant="primary")
                yield Button("Edit", id=f"{self.id_prefix}-edit", variant="warning")
                yield Button("Remove", id=f"{self.id_prefix}-remove", variant="error")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "groups-refresh":
            self.refresh_data()
        elif event.button.id == "groups-remove":
            if self.selected_row:
                try:
                    self.config_service.remove_group(self.selected_row)
                    self.notify(f"Group '{self.selected_row}' removed")
                    self.refresh_data()
                    self.selected_row = None
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
        elif event.button.id == "groups-edit":
            if self.selected_row:
                # Fetch members
                groups = self.config_service.list_groups()
                members = groups.get(self.selected_row, [])
                
                def handle_edit(result):
                    if result:
                        alias, devices = result
                        try:
                            # If alias changed, remove old and add new? 
                            # Simplification: Don't allow alias change or handle it.
                            # The screen allows alias edit.
                            
                            if alias != self.selected_row:
                                self.config_service.add_group(alias, devices)
                                self.config_service.remove_group(self.selected_row)
                                self.notify(f"Group '{self.selected_row}' renamed to '{alias}' and updated")
                            else:
                                # Start fresh? config service doesn't have update_group. 
                                # Remove and Re-add is safest atomic-ish op if no constraint failure.
                                # But if we remove first, and add fails, we lost it.
                                # If we add first, it fails "exists".
                                # Need update_group in service? Or just Remove then Add.
                                # Since we are in TUI, we can try to facilitate.
                                
                                # Hack: Remove then Add.
                                self.config_service.remove_group(self.selected_row)
                                try:
                                    self.config_service.add_group(alias, devices)
                                    self.notify(f"Group '{alias}' updated")
                                except Exception as e_add:
                                    # Restore?
                                    self.config_service.add_group(self.selected_row, members) 
                                    raise e_add

                            self.refresh_data()
                            self.selected_row = None
                        except Exception as e:
                            self.notify(f"Error updating group: {e}", severity="error")

                self.app.push_screen(
                    AddGroupScreen(self.config_service, initial_alias=self.selected_row, initial_members=members), 
                    handle_edit
                )
            else:
                self.notify("Please select a group to edit", severity="warning")
        elif event.button.id == "groups-add":
            def handle_add(result):
                if result:
                    alias, devices = result
                    try:
                        self.config_service.add_group(alias, devices)
                        self.notify(f"Group '{alias}' added")
                        self.refresh_data()
                    except Exception as e:
                        self.notify(f"Error adding group: {e}", severity="error")
            
            self.app.push_screen(AddGroupScreen(self.config_service), handle_add)

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
            
            with TabPane("Groups", id="tab-groups"):
                 yield GroupsView(self.config_service)
                
            with TabPane("Hosts", id="tab-hosts"):
                yield HostsView(self.config_service)

            with TabPane("Defaults", id="tab-defaults"):
                 yield DefaultsView(self.config_service)

        yield Footer()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark
