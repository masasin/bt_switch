# bt-switch

`bt-switch` is a CLI tool designed to seamlessly switch a Bluetooth device (like headphones or a mouse) between your local machine and a remote host. It handles the disconnection on one side and connection on the other, automating the "push" and "pull" logic.

## Features

- **Automated Switching**: Detects where the device is currently connected and moves it to the other side.
- **SSH Integration**: Controls remote Bluetooth stacks via SSH.
- **Configurable**: Define multiple devices and hosts in a simple TOML configuration.
- **Smart Defaults**: Per-host default settings based on your machine's hostname.

## Installation

Ensure you have [uv](https://github.com/astral-sh/uv) installed, then:

```bash
git clone https://github.com/youruser/bt_switch.git
cd bt_switch
uv sync
```

To install the tool globally in your environment:

```bash
uv tool install .
```

## Requirements

- **Linux**: The tool currently uses `bluetoothctl` (BlueZ) for Bluetooth management.
- **SSH**: Passwordless SSH access to remote hosts is required for remote operations.

## Configuration

The configuration file is located at `~/.config/bt_switch/config.toml` (or the equivalent on your OS).

### Example Configuration

```toml
# Define your Bluetooth devices
[devices.headphones]
mac = "00:11:22:33:44:55"
name = "Sony WH-1000XM4"

[devices.mouse]
mac = "AA:BB:CC:DD:EE:FF"
name = "Logitech MX Master"

# Define your hosts
[hosts.desktop]
address = "jean-desktop"  # Or an IP address
user = "jean"
protocol = "ssh"

[hosts.laptop]
address = "jean-laptop"  # Or an IP address
user = "jean"
protocol = "ssh"

# Default settings based on local hostname
[defaults.laptop]
default_device = "headphones"
default_target = "desktop"

[defaults.desktop]
default_device = "headphones"
default_target = "laptop"
```

## Usage

Run the tool without arguments to use your hostname's defaults:

```bash
bt-switch
```

Override the target or device:

```bash
# Switch default device to a specific target
bt-switch desktop

# Switch a specific device to a specific target
bt-switch desktop mouse
```

### How it works

1. **Detection**: The tool checks if the device is currently connected to the local machine.
2. **Push**: If connected locally, it disconnects locally and then tells the remote host to connect.
3. **Pull**: If not connected locally, it tells the remote host to disconnect and then connects locally.
