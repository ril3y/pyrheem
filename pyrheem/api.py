"""Rheem EcoNet API Client"""

import json
import ssl
import time
from typing import Callable, Dict, List, Optional

import requests

from .models import Location, RheemSession, WaterHeater

# Try to import paho-mqtt
try:
    import paho.mqtt.client as mqtt

    try:
        from paho.mqtt.enums import CallbackAPIVersion

        PAHO_V2 = True
    except ImportError:
        PAHO_V2 = False
    MQTT_AVAILABLE = True
except ImportError:
    mqtt = None
    PAHO_V2 = False
    MQTT_AVAILABLE = False

# API Constants (from decompiled APK)
PROD_URL = "https://rheem.rheemconnect.com/api/v/1/"
SYSTEM_KEY = "e2e699cb0bb0bbb88fc8858cb5a401"
SYSTEM_SECRET = "E2E699CB0BE6C6FADDB1B0BC9A20"

# MQTT Topics
USER_DESIRED_TOPIC = "user/{account_id}/device/desired"
USER_REPORTED_TOPIC = "user/{account_id}/device/reported"


class RheemEcoNetAPI:
    """
    Rheem EcoNet API Client for controlling water heaters.

    Example usage as a library:
        from pyrheem import RheemEcoNetAPI

        api = RheemEcoNetAPI("email@example.com", "password")
        if api.login() and api.get_all_data():
            # Get first water heater
            heater = list(api.water_heaters.values())[0]
            print(f"Current temp: {heater.setpoint}")

            # Set temperature
            api.set_temperature(heater, 120)
    """

    def __init__(self, email: str, password: str, quiet: bool = True):
        """
        Initialize the API client.

        Args:
            email: Rheem account email
            password: Rheem account password
            quiet: If True, suppress log output (default for library use)
        """
        self.email = email
        self.password = password
        self.quiet = quiet
        self.session = RheemSession()
        self.mqtt_client = None
        self.locations: Dict[str, Location] = {}
        self.water_heaters: Dict[str, WaterHeater] = {}
        self._mqtt_connected = False
        self._on_message_callback: Optional[Callable] = None

    def _log(self, msg: str):
        if not self.quiet:
            print(msg)

    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EcoNet/6.14.0 Android",
            "ClearBlade-SystemKey": SYSTEM_KEY,
            "ClearBlade-SystemSecret": SYSTEM_SECRET,
        }
        if include_auth and self.session.user_token:
            headers["ClearBlade-UserToken"] = self.session.user_token
        return headers

    def login(self) -> bool:
        """
        Authenticate with the Rheem API.

        Returns:
            True if login successful, False otherwise
        """
        url = f"{PROD_URL}user/auth"
        payload = {"email": self.email, "password": self.password}
        self._log(f"[*] Logging in as {self.email}...")

        try:
            response = requests.post(url, json=payload, headers=self._get_headers(include_auth=False))
            if response.status_code != 200:
                self._log(f"[-] Login failed: {response.status_code}")
                return False

            data = response.json()
            if "user_token" in data:
                self.session.user_token = data.get("user_token", "")
                self.session.user_id = data.get("user_id", "")
                self.session.account_id = data.get("options", {}).get("account_id", "")
                self._log("[+] Login successful!")
                return True
            return False
        except Exception as e:
            self._log(f"[-] Login error: {e}")
            return False

    def get_provisioning_config(self) -> bool:
        """Get MQTT broker configuration."""
        url = f"{PROD_URL}code/{SYSTEM_KEY}/provisioningConfig"
        self._log("[*] Getting MQTT config...")

        try:
            response = requests.post(url, headers=self._get_headers())
            data = response.json()
            if data.get("success"):
                results = data.get("results", {})
                domain = results.get("default_domain", results.get("defaultDomain", {}))
                self.session.cloud_url = domain.get("cloud_url", domain.get("cloudUrl", "rheemprod.rheemcert.com"))
                self.session.cloud_port = domain.get("cloud_port", domain.get("cloudPort", 1884))
                self._log(f"[+] MQTT: {self.session.cloud_url}:{self.session.cloud_port}")
                return True
        except Exception as e:
            self._log(f"[-] Config error: {e}")

        self.session.cloud_url = "rheemprod.rheemcert.com"
        self.session.cloud_port = 1884
        return True

    def get_all_data(self) -> bool:
        """
        Fetch all locations and devices.

        Returns:
            True if successful, False otherwise
        """
        url = f"{PROD_URL}code/{SYSTEM_KEY}/getUserDataForApp"
        self._log("[*] Fetching devices...")

        try:
            response = requests.post(url, json={"location_only": False}, headers=self._get_headers())
            if response.status_code != 200:
                return False

            data = response.json()
            self._parse_devices(data)
            return True
        except Exception as e:
            self._log(f"[-] Error: {e}")
            return False

    def _parse_devices(self, data: Dict):
        self.locations.clear()
        self.water_heaters.clear()

        locations_data = data.get("results", {}).get("locations", [])

        for loc_data in locations_data:
            location_id = loc_data.get("location_id", "")
            location_name = loc_data.get("@LOCATION_NAME", loc_data.get("name", "Unknown"))
            location_info = loc_data.get("@LOCATION_INFO", "")

            location = Location(location_id=location_id, name=location_name, address=location_info, devices=[])

            equipment_list = loc_data.get("equipment", loc_data.get("equiptments", []))

            for eq in equipment_list:
                device_type = eq.get("@TYPE", eq.get("device_type", ""))
                if "water" not in device_type.lower() and device_type != "WH":
                    continue

                serial = eq.get("serial_number", "")
                device_name = eq.get("device_name", "")
                display_name = eq.get("@NAME", {})
                display_name = (
                    display_name.get("value", "Water Heater")
                    if isinstance(display_name, dict)
                    else str(display_name) or "Water Heater"
                )

                setpoint_data = eq.get("@SETPOINT", {})
                if isinstance(setpoint_data, dict):
                    setpoint = int(setpoint_data.get("value", 120))
                    constraints = setpoint_data.get("constraints", {})
                    setpoint_min = constraints.get("lowerLimit", 95)
                    setpoint_max = constraints.get("upperLimit", 140)
                else:
                    setpoint = int(setpoint_data) if setpoint_data else 120
                    setpoint_min, setpoint_max = 95, 140

                mode_data = eq.get("@MODE", {})
                if isinstance(mode_data, dict):
                    mode = mode_data.get("status", "Unknown")
                    mode_value = int(mode_data.get("value", 0))
                else:
                    mode, mode_value = str(mode_data), 0

                enabled_data = eq.get("@ENABLED", {})
                enabled = enabled_data.get("value", 1) == 1 if isinstance(enabled_data, dict) else bool(enabled_data)

                wh = WaterHeater(
                    serial_number=serial,
                    device_name=device_name,
                    display_name=display_name,
                    device_type=device_type,
                    location_id=location_id,
                    location_name=location_name,
                    setpoint=setpoint,
                    setpoint_min=setpoint_min,
                    setpoint_max=setpoint_max,
                    mode=mode,
                    mode_value=mode_value,
                    running=eq.get("@RUNNING", ""),
                    connected=eq.get("@CONNECTED", False),
                    enabled=enabled,
                    raw_data=eq,
                )

                location.devices.append(wh)
                self.water_heaters[serial] = wh

            self.locations[location_id] = location

    def get_locations_list(self) -> List[Location]:
        """Get locations as ordered list."""
        return list(self.locations.values())

    def get_location(self, identifier: str) -> Optional[Location]:
        """
        Get location by index, ID, or name (partial match).

        Args:
            identifier: Location index (e.g., "0"), ID, or name

        Returns:
            Location if found, None otherwise
        """
        locations = self.get_locations_list()

        if identifier.isdigit():
            idx = int(identifier)
            if 0 <= idx < len(locations):
                return locations[idx]

        if identifier in self.locations:
            return self.locations[identifier]

        identifier_lower = identifier.lower()
        for loc in locations:
            if identifier_lower in loc.name.lower():
                return loc

        return None

    def get_device(self, location: Optional[Location], device_id: str) -> Optional[WaterHeater]:
        """
        Get device by index, serial, or name within a location.

        Args:
            location: Location to search in (None for all devices)
            device_id: Device index, serial number, or name

        Returns:
            WaterHeater if found, None otherwise
        """
        if location:
            devices = location.devices
        else:
            devices = list(self.water_heaters.values())

        if not devices:
            return None

        if device_id.isdigit():
            idx = int(device_id)
            if 0 <= idx < len(devices):
                return devices[idx]

        if device_id in self.water_heaters:
            return self.water_heaters[device_id]

        device_id_lower = device_id.lower()
        for dev in devices:
            if device_id_lower in dev.display_name.lower() or device_id_lower in dev.serial_number.lower():
                return dev

        return None

    # =========================================================================
    # MQTT Functions
    # =========================================================================

    @property
    def mqtt_available(self) -> bool:
        """Check if MQTT is available."""
        return MQTT_AVAILABLE

    @property
    def mqtt_connected(self) -> bool:
        """Check if MQTT is connected."""
        return self._mqtt_connected

    def connect_mqtt(self) -> bool:
        """
        Connect to MQTT broker for real-time control.

        Returns:
            True if connected successfully
        """
        if not MQTT_AVAILABLE:
            self._log("[-] paho-mqtt not installed. Run: pip install paho-mqtt")
            return False

        if not self.session.cloud_url:
            self.get_provisioning_config()

        self._log("[*] Connecting to MQTT...")
        client_id = f"python_econet_{int(time.time())}"

        try:
            if PAHO_V2:
                self.mqtt_client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv311
                )
            else:
                self.mqtt_client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

            self.mqtt_client.username_pw_set(self.session.user_token, SYSTEM_KEY)
            self.mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.mqtt_client.tls_insecure_set(True)

            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_message = self._on_message
            self.mqtt_client.on_disconnect = self._on_disconnect

            self.mqtt_client.connect(self.session.cloud_url, self.session.cloud_port, keepalive=60)
            self.mqtt_client.loop_start()

            for _ in range(10):
                if self._mqtt_connected:
                    return True
                time.sleep(0.5)

            self._log("[-] MQTT connection timeout")
            return False
        except Exception as e:
            self._log(f"[-] MQTT error: {e}")
            return False

    def set_message_callback(self, callback: Callable[[Dict], None]):
        """
        Set a callback for incoming MQTT messages.

        Args:
            callback: Function that receives parsed message dict
        """
        self._on_message_callback = callback

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        is_success = (reason_code == 0) if isinstance(reason_code, int) else not reason_code.is_failure
        if is_success:
            self._mqtt_connected = True
            self._log("[+] MQTT connected!")
            topic = USER_REPORTED_TOPIC.format(account_id=self.session.account_id)
            client.subscribe(topic, qos=0)
        else:
            self._log(f"[-] MQTT connect failed: {reason_code}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            self._log(f"\n[MQTT] {json.dumps(payload, indent=2)[:800]}")
            if self._on_message_callback:
                self._on_message_callback(payload)
        except Exception:
            pass

    def _on_disconnect(self, client, userdata, disconnect_flags_or_rc, reason_code=None, properties=None):
        self._mqtt_connected = False

    def _send_mqtt_command(self, wh: WaterHeater, **kwargs) -> bool:
        if not self._mqtt_connected:
            if not self.connect_mqtt():
                return False

        transaction_id = f"PYTHON_{int(time.time() * 1000)}"
        message = {
            "transactionId": transaction_id,
            "device_name": wh.device_name,
            "serial_number": wh.serial_number,
            **kwargs,
        }

        topic = USER_DESIRED_TOPIC.format(account_id=self.session.account_id)
        self._log(f"[*] Sending: {json.dumps(message)}")

        try:
            result = self.mqtt_client.publish(topic, json.dumps(message), qos=0)
            result.wait_for_publish(timeout=5)
            if result.rc == 0:
                self._log("[+] Command sent!")
                time.sleep(2)
                return True
        except Exception as e:
            self._log(f"[-] Error: {e}")
        return False

    def set_temperature(self, wh: WaterHeater, temperature: int) -> bool:
        """
        Set water heater temperature.

        Args:
            wh: WaterHeater device
            temperature: Target temperature in Fahrenheit

        Returns:
            True if command sent successfully
        """
        if temperature < wh.setpoint_min or temperature > wh.setpoint_max:
            self._log(f"[-] Temperature must be {wh.setpoint_min}-{wh.setpoint_max}F")
            return False
        self._log(f"[*] Setting {wh.display_name} to {temperature}F...")
        return self._send_mqtt_command(wh, **{"@SETPOINT": temperature})

    def set_mode(self, wh: WaterHeater, mode: str) -> bool:
        """
        Set water heater mode.

        Args:
            wh: WaterHeater device
            mode: "energy" or "performance"

        Returns:
            True if command sent successfully
        """
        mode_lower = mode.lower()
        if "energy" in mode_lower or "saver" in mode_lower:
            mode_value = 0
        elif "performance" in mode_lower or "high" in mode_lower:
            mode_value = 1
        else:
            self._log("[-] Invalid mode. Use: energy, performance")
            return False
        self._log(f"[*] Setting mode to {mode}...")
        return self._send_mqtt_command(wh, **{"@MODE": mode_value})

    def set_enabled(self, wh: WaterHeater, enabled: bool) -> bool:
        """
        Enable or disable water heater.

        Args:
            wh: WaterHeater device
            enabled: True to enable, False to disable

        Returns:
            True if command sent successfully
        """
        action = "Enabling" if enabled else "Disabling"
        self._log(f"[*] {action} {wh.display_name}...")
        return self._send_mqtt_command(wh, **{"@ENABLED": 1 if enabled else 0})

    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self._mqtt_connected = False
