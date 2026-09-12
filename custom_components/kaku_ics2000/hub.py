"""
ICS2000 Hub API client.

Handles login, device discovery, status polling, and sending commands
to the KlikAanKlikUit / Trust Smart Cloud API.

All device data is AES-128-CBC encrypted with the per-home AES key.
Commands are encoded as a binary frame sent to command.php.
"""
from __future__ import annotations

import base64
import json
import logging
import struct
from dataclasses import dataclass, field
from typing import Any

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from .const import (
    BASE_URL,
    CMD_FUNCTION_DIM,
    CMD_FUNCTION_SHUTTER,
    CMD_FUNCTION_SWITCH,
    DEVICE_TYPE_MAP,
    INTERNAL_MODULES,
    SHUTTER_CLOSE,
    SHUTTER_OPEN,
    SHUTTER_STOP,
)

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------

def _decrypt(encrypted_b64: str, aes_hex: str) -> str:
    """Decrypt an AES-128-CBC base64 payload from the ICS2000 API."""
    raw = base64.b64decode(encrypted_b64)
    iv = raw[:16]
    ciphertext = raw[16:]
    key = bytes.fromhex(aes_hex)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), 16).decode("utf-8")


def _encrypt(plaintext: str, aes_hex: str) -> bytes:
    """Encrypt a string with AES-128-CBC (zero IV) for command payloads."""
    block_size = 16
    pad_len = block_size - (len(plaintext) % block_size)
    padded = (plaintext + chr(pad_len) * pad_len).encode("utf-8")
    iv = bytes(16)
    key = bytes.fromhex(aes_hex)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(padded)


# ---------------------------------------------------------------------------
# Command frame builder
# ---------------------------------------------------------------------------

def _build_command(mac: str, entity_id: int, function: int, value: int | str, aes_hex: str) -> str:
    """
    Build an ICS2000 binary command frame (hex string).

    Frame layout (43 bytes header + encrypted data):
      [0]     frame number (1)
      [2]     type (128 = device command)
      [3..8]  MAC address bytes
      [9..12] magic number (653213 little-endian)
      [29..32] entity ID (little-endian)
      [41..42] data length (little-endian)
      [43+]   AES-encrypted JSON payload
    """
    header = bytearray(43)
    header[0] = 1         # frame
    header[2] = 128       # type: device command

    # MAC address
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    header[3:9] = mac_bytes

    # Magic number
    struct.pack_into("<I", header, 9, 653213)

    # Entity ID
    struct.pack_into("<I", header, 29, entity_id)

    # Build JSON payload
    payload = (
        '{"module":{"id":' + str(entity_id) +
        ',"function":' + str(function) +
        ',"value":' + str(value) + '}}'
    )
    encrypted_data = _encrypt(payload, aes_hex)

    # Data length
    struct.pack_into("<H", header, 41, len(encrypted_data))

    return header.hex() + encrypted_data.hex()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ICS2000Device:
    """Represents a single ICS2000 device (module)."""
    entity_id: int
    name: str
    device_type: int          # raw integer from ICS2000 API
    ha_platform: str          # HA domain: light / switch / cover / sensor / binary_sensor
    # Current status (updated by coordinator)
    functions: list[Any] = field(default_factory=list)
    raw_status: dict = field(default_factory=dict)

    @property
    def is_on(self) -> bool | None:
        """Return True/False for on/off devices, None if unknown."""
        if self.functions:
            return bool(self.functions[0])
        return None

    @property
    def brightness(self) -> int | None:
        """Return brightness (0-255) for dimmers, None if not a dimmer."""
        if len(self.functions) >= 2:
            return int(self.functions[1])
        return None


# ---------------------------------------------------------------------------
# Hub
# ---------------------------------------------------------------------------

class ICS2000Hub:
    """Manages communication with the ICS2000 cloud API."""

    def __init__(self, mac: str, email: str, password: str) -> None:
        self._mac = mac.replace(":", "").upper()
        self._mac_colons = ":".join(self._mac[i:i+2] for i in range(0, 12, 2))
        self._email = email
        self._password = password
        self._aes_key: str | None = None
        self._home_id: int | None = None
        self._devices: list[ICS2000Device] = []

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """Login to ICS2000 cloud and retrieve AES key + home ID."""
        try:
            resp = requests.get(
                f"{BASE_URL}/account.php",
                params={
                    "action": "login",
                    "email": self._email,
                    "mac": self._mac,
                    "password_hash": self._password,
                    "device_unique_id": "android",
                    "platform": "Android",
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            homes = data.get("homes", [])
            if not homes:
                _LOGGER.error("ICS2000 login returned no homes")
                return False
            self._aes_key = homes[0]["aes_key"]
            self._home_id = homes[0]["home_id"]
            _LOGGER.debug("ICS2000 login OK — home_id=%s", self._home_id)
            return True
        except Exception as exc:
            _LOGGER.error("ICS2000 login failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def fetch_devices(self) -> list[ICS2000Device]:
        """Fetch and decrypt all modules from the ICS2000 gateway."""
        if not self._aes_key:
            _LOGGER.error("Cannot fetch devices: not logged in")
            return []

        try:
            resp = requests.get(
                f"{BASE_URL}/gateway.php",
                params={
                    "action": "sync",
                    "email": self._email,
                    "mac": self._mac,
                    "home_id": self._home_id,
                    "password_hash": self._password,
                    "device_unique_id": "android",
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            modules = resp.json()
        except Exception as exc:
            _LOGGER.error("ICS2000 device sync failed: %s", exc)
            return []

        devices = []
        for raw in modules:
            data_enc = raw.get("data")
            if not data_enc:
                continue
            try:
                decrypted = json.loads(_decrypt(data_enc, self._aes_key))
            except Exception as exc:
                _LOGGER.debug("Could not decrypt module %s: %s", raw.get("id"), exc)
                continue

            if "module" not in decrypted:
                continue  # room, scenario, zone — skip

            mod = decrypted["module"]
            device_int = mod.get("device")
            if device_int is None:
                continue
            if device_int in INTERNAL_MODULES:
                continue  # P1, Alarm, IPCam, etc.

            ha_platform = DEVICE_TYPE_MAP.get(device_int)
            if ha_platform is None:
                _LOGGER.debug(
                    "Unknown device type %s for '%s' — skipping",
                    device_int, mod.get("name"),
                )
                continue

            devices.append(ICS2000Device(
                entity_id=mod["id"],
                name=mod["name"],
                device_type=device_int,
                ha_platform=ha_platform,
            ))
            _LOGGER.debug(
                "Found device '%s' id=%s device=%s → %s",
                mod["name"], mod["id"], device_int, ha_platform,
            )

        self._devices = devices
        return devices

    # ------------------------------------------------------------------
    # Status polling
    # ------------------------------------------------------------------

    def fetch_status(self, entity_id: int) -> list[Any]:
        """
        Fetch the current status (function values) for a single device.
        Returns a list where [0] is on/off, [1] is dim level, etc.
        """
        if not self._aes_key:
            return []
        try:
            resp = requests.get(
                f"{BASE_URL}/entity.php",
                params={
                    "action": "get-multiple",
                    "email": self._email,
                    "mac": self._mac,
                    "password_hash": self._password,
                    "home_id": self._home_id,
                    "entity_id": f"[{entity_id}]",
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            arr = resp.json()
            if not arr or arr[0].get("status") is None:
                return []
            dec = json.loads(_decrypt(arr[0]["status"], self._aes_key))
            return dec.get("module", {}).get("functions", [])
        except Exception as exc:
            _LOGGER.debug("Status fetch failed for %s: %s", entity_id, exc)
            return []

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _send_command(self, entity_id: int, function: int, value: int | str) -> bool:
        """Send a command to the ICS2000 hub via the cloud API."""
        if not self._aes_key:
            _LOGGER.error("Cannot send command: not logged in")
            return False
        try:
            command_hex = _build_command(
                self._mac_colons, entity_id, function, value, self._aes_key
            )
            resp = requests.get(
                f"{BASE_URL}/command.php",
                params={
                    "action": "add",
                    "email": self._email,
                    "mac": self._mac,
                    "password_hash": self._password,
                    "device_unique_id": "android",
                    "command": command_hex,
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            _LOGGER.debug(
                "Command sent: entity=%s func=%s value=%s → %s",
                entity_id, function, value, resp.text[:80],
            )
            return True
        except Exception as exc:
            _LOGGER.error("Command failed for entity %s: %s", entity_id, exc)
            return False

    def turn_on(self, entity_id: int) -> bool:
        """Turn a switch/lamp on."""
        return self._send_command(entity_id, CMD_FUNCTION_SWITCH, 1)

    def turn_off(self, entity_id: int) -> bool:
        """Turn a switch/lamp off."""
        return self._send_command(entity_id, CMD_FUNCTION_SWITCH, 0)

    def dim(self, entity_id: int, level: int) -> bool:
        """Set dimmer level (0–255)."""
        level = max(0, min(255, level))
        return self._send_command(entity_id, CMD_FUNCTION_DIM, level)

    def shutter_open(self, entity_id: int) -> bool:
        """Open a shutter/rolluik."""
        return self._send_command(entity_id, CMD_FUNCTION_SHUTTER, SHUTTER_OPEN)

    def shutter_close(self, entity_id: int) -> bool:
        """Close a shutter/rolluik."""
        return self._send_command(entity_id, CMD_FUNCTION_SHUTTER, SHUTTER_CLOSE)

    def shutter_stop(self, entity_id: int) -> bool:
        """Stop a shutter/rolluik (MY position)."""
        return self._send_command(entity_id, CMD_FUNCTION_SHUTTER, SHUTTER_STOP)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def mac(self) -> str:
        return self._mac

    @property
    def home_id(self) -> int | None:
        return self._home_id

    @property
    def devices(self) -> list[ICS2000Device]:
        return self._devices
