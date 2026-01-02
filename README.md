# pyRheem

A Python library and CLI for controlling Rheem water heaters via the EcoNet API.

## Installation

### From PyPI

```bash
pip install pyrheem
```

### From Source

```bash
git clone https://github.com/ril3y/pyrheem.git
cd pyrheem
pip install -e .
```

## Configuration

Set your Rheem EcoNet credentials using environment variables or a `.env` file:

```bash
export RHEEM_EMAIL="your_email@example.com"
export RHEEM_PASSWORD="your_password"
```

Or create a `.env` file in your working directory:

```
RHEEM_EMAIL=your_email@example.com
RHEEM_PASSWORD=your_password
```

## CLI Usage

### List Devices

```bash
rheem --list
```

Output:
```
Locations and Devices:
============================================================

[Location 0] My Home
  ID: abc12345-6789-def0-1234-567890abcdef
  Address: Springfield, IL

  [Device 0] Electric Water Heater
    Serial: XX-XX-XX-XX-XX-XX-XXX
    Setpoint: 120F (range: 110-130)
    Mode: Energy Saver
    Status: Running | Connected
```

### Get Status (JSON)

```bash
rheem --status
```

### Set Temperature

```bash
# Set first device
rheem --temp 120

# Specify location and device by index
rheem --location 0 --device 0 --temp 125

# Specify by name (partial match)
rheem --location "My Home" --device "Electric" --temp 120
```

### Set Mode

```bash
rheem --mode energy       # Energy Saver mode
rheem --mode performance  # Performance mode
```

### Enable/Disable

```bash
rheem --enable
rheem --disable
```

### Interactive Mode

```bash
rheem
```

Commands in interactive mode:
- `list` - List locations and devices
- `use <location> <device>` - Select a device
- `temp <temperature>` - Set temperature
- `mode <energy|performance>` - Set mode
- `enable` / `disable` - Enable/disable device
- `status` - Show current device status
- `refresh` - Refresh data from server
- `quit` - Exit

### All CLI Options

```
usage: rheem [-h] [--email EMAIL] [--password PASSWORD] [--location LOCATION]
             [--device DEVICE] [--list] [--status] [--temp TEMP]
             [--mode {energy,performance}] [--enable] [--disable] [--quiet]
             [--interactive]

Options:
  --email           Rheem account email
  --password        Rheem account password
  --location, -L    Location index or name (default: 0)
  --device, -d      Device index, serial, or name (default: 0)
  --list, -l        List all locations and devices
  --status, -s      Get all device status as JSON
  --temp, -t        Set temperature in Fahrenheit
  --mode, -m        Set mode: energy or performance
  --enable          Enable the water heater
  --disable         Disable the water heater
  --quiet, -q       Quiet mode (JSON output only)
  --interactive, -i Force interactive mode
```

## Library Usage

```python
from pyrheem import RheemEcoNetAPI

# Initialize and login
api = RheemEcoNetAPI("email@example.com", "password")

if api.login() and api.get_all_data():
    # List all water heaters
    for serial, heater in api.water_heaters.items():
        print(f"{heater.display_name}: {heater.setpoint}F")

    # Get first water heater
    heater = list(api.water_heaters.values())[0]

    # Set temperature
    api.set_temperature(heater, 120)

    # Set mode
    api.set_mode(heater, "energy")  # or "performance"

    # Enable/disable
    api.set_enabled(heater, True)

    # Cleanup
    api.disconnect()
```

### Available Classes

- `RheemEcoNetAPI` - Main API client
- `WaterHeater` - Water heater device model
- `Location` - Location (home) model
- `RheemSession` - Session information

### RheemEcoNetAPI Methods

| Method | Description |
|--------|-------------|
| `login()` | Authenticate with Rheem API |
| `get_all_data()` | Fetch all locations and devices |
| `get_locations_list()` | Get list of locations |
| `get_location(identifier)` | Get location by index, ID, or name |
| `get_device(location, device_id)` | Get device by index, serial, or name |
| `connect_mqtt()` | Connect to MQTT for real-time control |
| `set_temperature(heater, temp)` | Set water heater temperature |
| `set_mode(heater, mode)` | Set mode ("energy" or "performance") |
| `set_enabled(heater, enabled)` | Enable or disable water heater |
| `disconnect()` | Disconnect from MQTT |

### WaterHeater Properties

| Property | Type | Description |
|----------|------|-------------|
| `serial_number` | str | Device serial number |
| `display_name` | str | Friendly device name |
| `setpoint` | int | Current temperature setpoint (F) |
| `setpoint_min` | int | Minimum allowed temperature |
| `setpoint_max` | int | Maximum allowed temperature |
| `mode` | str | Current mode (e.g., "Energy Saver") |
| `running` | str | Running status |
| `connected` | bool | Connection status |
| `enabled` | bool | Whether device is enabled |

## Requirements

- Python 3.8+
- requests
- paho-mqtt

## License

MIT License
