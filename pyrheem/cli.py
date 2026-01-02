"""Command-line interface for pyrheem"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Load .env file
try:
    from dotenv import load_dotenv

    load_dotenv(Path.cwd() / ".env")
    load_dotenv()
except ImportError:
    pass

from .api import RheemEcoNetAPI
from .models import WaterHeater


def print_device_list(api: RheemEcoNetAPI):
    """Print formatted list of locations and devices"""
    locations = api.get_locations_list()

    if not locations:
        print("No locations found")
        return

    print("\nLocations and Devices:")
    print("=" * 60)

    for loc_idx, location in enumerate(locations):
        print(f"\n[Location {loc_idx}] {location.name}")
        print(f"  ID: {location.location_id}")
        if location.address:
            print(f"  Address: {location.address}")

        if not location.devices:
            print("  (No water heaters)")
            continue

        for dev_idx, device in enumerate(location.devices):
            status = "Connected" if device.connected else "Disconnected"
            print(f"\n  [Device {dev_idx}] {device.display_name}")
            print(f"    Serial: {device.serial_number}")
            print(f"    Setpoint: {device.setpoint}F (range: {device.setpoint_min}-{device.setpoint_max})")
            print(f"    Mode: {device.mode}")
            print(f"    Status: {device.running} | {status}")

    print("\n" + "=" * 60)
    print("Usage examples:")
    print("  rheem --location 0 --device 0 --temp 120")
    print('  rheem --location "My Home" --device "Electric" --temp 115')
    print("=" * 60)


def interactive_mode(api: RheemEcoNetAPI):
    """Interactive command mode"""
    print("\n" + "=" * 60)
    print("Interactive Mode - Commands:")
    print("  list                          - List locations and devices")
    print("  use <loc_idx> <dev_idx>       - Select device for commands")
    print("  temp <temperature>            - Set temperature")
    print("  mode <energy|performance>     - Set mode")
    print("  enable / disable              - Enable/disable device")
    print("  status                        - Show current device status")
    print("  refresh                       - Refresh data from server")
    print("  quit                          - Exit")
    print("=" * 60 + "\n")

    current_device: Optional[WaterHeater] = None

    # Default to first device
    locations = api.get_locations_list()
    if locations and locations[0].devices:
        current_device = locations[0].devices[0]
        print(f"Selected: {current_device.display_name} @ {current_device.location_name}")

    while True:
        try:
            prompt = f"rheem [{current_device.display_name if current_device else 'no device'}]> "
            cmd = input(prompt).strip()
            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0].lower()

            if action in ("quit", "exit", "q"):
                break

            elif action == "list":
                print_device_list(api)

            elif action == "use" and len(parts) >= 3:
                loc = api.get_location(parts[1])
                if loc:
                    dev = api.get_device(loc, parts[2])
                    if dev:
                        current_device = dev
                        print(f"Selected: {dev.display_name} @ {dev.location_name}")
                    else:
                        print(f"Device not found: {parts[2]}")
                else:
                    print(f"Location not found: {parts[1]}")

            elif action == "temp" and len(parts) >= 2:
                if current_device:
                    api.set_temperature(current_device, int(parts[1]))
                else:
                    print("No device selected. Use 'use <loc> <dev>' first.")

            elif action == "mode" and len(parts) >= 2:
                if current_device:
                    api.set_mode(current_device, parts[1])
                else:
                    print("No device selected.")

            elif action == "enable":
                if current_device:
                    api.set_enabled(current_device, True)
                else:
                    print("No device selected.")

            elif action == "disable":
                if current_device:
                    api.set_enabled(current_device, False)
                else:
                    print("No device selected.")

            elif action == "status":
                if current_device:
                    api.get_all_data()
                    if current_device.serial_number in api.water_heaters:
                        current_device = api.water_heaters[current_device.serial_number]
                    print(f"\n{current_device.display_name} @ {current_device.location_name}")
                    print(f"  Setpoint: {current_device.setpoint}F")
                    print(f"  Mode: {current_device.mode}")
                    print(f"  Status: {current_device.running}")
                    print(f"  Connected: {current_device.connected}")
                else:
                    print("No device selected.")

            elif action == "refresh":
                api.get_all_data()
                print("Data refreshed.")

            else:
                print(f"Unknown command: {action}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    api.disconnect()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="rheem",
        description="Rheem EcoNet Water Heater Control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rheem --list                              # List locations and devices
  rheem --status                            # Get all devices as JSON
  rheem --temp 120                          # Set temp (first device)
  rheem --location 0 --device 0 --temp 125  # Specify location/device by index
  rheem --location "Home" --device "Electric" --temp 120  # By name
  rheem --mode energy                       # Set Energy Saver mode
  rheem --mode performance                  # Set Performance mode
  rheem                                     # Interactive mode

Environment variables (or use .env file):
  RHEEM_EMAIL     - Your Rheem account email
  RHEEM_PASSWORD  - Your Rheem account password
        """,
    )

    parser.add_argument("--email", default=os.environ.get("RHEEM_EMAIL"), help="Rheem account email")
    parser.add_argument("--password", default=os.environ.get("RHEEM_PASSWORD"), help="Rheem account password")
    parser.add_argument("--location", "-L", default="0", help="Location index or name (default: 0)")
    parser.add_argument("--device", "-d", default="0", help="Device index, serial, or name (default: 0)")
    parser.add_argument("--list", "-l", action="store_true", help="List all locations and devices")
    parser.add_argument("--status", "-s", action="store_true", help="Get all device status as JSON")
    parser.add_argument("--temp", "-t", type=int, help="Set temperature in Fahrenheit")
    parser.add_argument("--mode", "-m", choices=["energy", "performance"], help="Set mode: energy or performance")
    parser.add_argument("--enable", action="store_true", help="Enable the water heater")
    parser.add_argument("--disable", action="store_true", help="Disable the water heater")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (JSON output only)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Force interactive mode")

    args = parser.parse_args()

    # Check credentials
    if not args.email or not args.password:
        print("Error: Credentials required. Set RHEEM_EMAIL and RHEEM_PASSWORD")
        print("       environment variables, create a .env file, or use --email/--password")
        sys.exit(1)

    has_command = args.list or args.status or args.temp or args.mode or args.enable or args.disable
    quiet = args.quiet or (has_command and not args.interactive)

    api = RheemEcoNetAPI(args.email, args.password, quiet=quiet)

    # Login
    if not api.login():
        print('{"error": "Login failed"}' if quiet else "[-] Login failed")
        sys.exit(1)

    # Get device data
    if not api.get_all_data():
        print('{"error": "Failed to get devices"}' if quiet else "[-] Failed to get devices")
        sys.exit(1)

    if not api.water_heaters:
        print('{"error": "No water heaters found"}' if quiet else "[-] No water heaters found")
        sys.exit(1)

    # Handle commands
    if args.list:
        print_device_list(api)

    elif args.status:
        output = {"locations": [loc.to_dict() for loc in api.get_locations_list()]}
        print(json.dumps(output, indent=2))

    elif args.temp or args.mode or args.enable or args.disable:
        location = api.get_location(args.location)
        if not location:
            msg = f"Location not found: {args.location}"
            print(f'{{"error": "{msg}"}}' if quiet else f"[-] {msg}")
            sys.exit(1)

        device = api.get_device(location, args.device)
        if not device:
            msg = f"Device not found: {args.device}"
            print(f'{{"error": "{msg}"}}' if quiet else f"[-] {msg}")
            sys.exit(1)

        if not quiet:
            print(f"[*] Target: {device.display_name} @ {location.name}")

        success = False
        result = {}

        if args.temp:
            success = api.set_temperature(device, args.temp)
            result = {"success": success, "temperature": args.temp}
        elif args.mode:
            success = api.set_mode(device, args.mode)
            result = {"success": success, "mode": args.mode}
        elif args.enable:
            success = api.set_enabled(device, True)
            result = {"success": success, "enabled": True}
        elif args.disable:
            success = api.set_enabled(device, False)
            result = {"success": success, "enabled": False}

        if quiet:
            print(json.dumps(result))

        sys.exit(0 if success else 1)

    else:
        # Interactive mode
        if not quiet:
            print("\n" + "=" * 60)
            print("Rheem EcoNet API Client")
            print("=" * 60)
            print_device_list(api)

        api.get_provisioning_config()

        if api.connect_mqtt():
            interactive_mode(api)
        else:
            print("[-] Could not connect to MQTT for real-time control")

    api.disconnect()


if __name__ == "__main__":
    main()
