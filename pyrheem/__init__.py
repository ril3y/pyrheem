"""
pyrheem - Rheem EcoNet API Client

A Python library and CLI for controlling Rheem water heaters via the EcoNet API.

Library Usage:
    from pyrheem import RheemEcoNetAPI, WaterHeater, Location

    api = RheemEcoNetAPI("email@example.com", "password")
    if api.login() and api.get_all_data():
        # Get first water heater
        heater = list(api.water_heaters.values())[0]
        print(f"Current temp: {heater.setpoint}F")

        # Set temperature
        api.set_temperature(heater, 120)

        # Cleanup
        api.disconnect()

CLI Usage:
    rheem --list                    # List all devices
    rheem --status                  # Get status as JSON
    rheem --temp 120                # Set temperature
    rheem --mode energy             # Set to energy saver mode
    rheem                           # Interactive mode
"""

__version__ = "0.1.0"
__author__ = "Riley Porter"

from .api import RheemEcoNetAPI
from .models import Location, RheemSession, WaterHeater

__all__ = [
    "RheemEcoNetAPI",
    "RheemSession",
    "Location",
    "WaterHeater",
    "__version__",
]
