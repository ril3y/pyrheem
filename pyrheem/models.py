"""Data models for Rheem EcoNet API"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class RheemSession:
    """Session information for authenticated user"""
    user_token: str = ""
    user_id: str = ""
    account_id: str = ""
    cloud_url: str = ""
    cloud_port: int = 1884


@dataclass
class Location:
    """A location (home) containing devices"""
    location_id: str
    name: str
    address: str
    devices: List["WaterHeater"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location_id": self.location_id,
            "name": self.name,
            "address": self.address,
            "devices": [d.to_dict() for d in self.devices]
        }


@dataclass
class WaterHeater:
    """A Rheem water heater device"""
    serial_number: str
    device_name: str
    display_name: str
    device_type: str
    location_id: str
    location_name: str
    setpoint: int = 120
    setpoint_min: int = 95
    setpoint_max: int = 140
    mode: str = ""
    mode_value: int = 0
    running: str = ""
    connected: bool = False
    enabled: bool = True
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "serial_number": self.serial_number,
            "device_name": self.device_name,
            "display_name": self.display_name,
            "location": self.location_name,
            "setpoint": self.setpoint,
            "setpoint_range": [self.setpoint_min, self.setpoint_max],
            "mode": self.mode,
            "running": self.running,
            "connected": self.connected,
            "enabled": self.enabled,
        }
