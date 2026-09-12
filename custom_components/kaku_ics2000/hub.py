"""
ICS2000 Hub API client with local UDP support and cloud fallback.

Commands are sent via local UDP directly to port 2012 of the hub on the LAN
for sub-second response times. If the hub cannot be reached locally, it
transparently falls back to the cloud API.
"""
from __future__ import annotations

import base64
import json
import logging
import socket
import struct
from dataclasses import dataclass, field
from typing import Any

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from .const import (
    BASE_URL,
    CMD_FUNCTION_DIM,
    CMD_FUNCTION_SHUTTER_CLOSE,
    CMD_FUNCTION_SHUTTER_OPEN,
    CMD_FUNCTION_SHUTTER_STOP,
    CMD_FUNCTION_SWITCH,
    DEVICE_TYPE_MAP,
    DISCOVERY_BROADCAST_MSG,
    HUB_UDP_PORT,
    INTERNAL_MODULES,
    SHUTTER_COMMAND_VALUE,
)

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 12  # seconds


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
    dec = cipher.decrypt(ciphertext)
    pad = dec[-1]
    if 1 <= pad <= 16:
        dec = dec[:-pad]
    return dec.decode("utf-8", errors="replace")


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
# Command packet builder
# ---------------------------------------------------------------------------

def _build_command_bytes(mac: str, entity_id: int, function: int, value: int | str, aes_hex: str) -> bytes:
    """
    Build an ICS2000 binary command packet.

    Frame layout (43 bytes header + AES encrypted data):
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

    # MAC address (6 bytes)
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

    return bytes(header) + encrypted_data


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ICS2000Device:
    """Represents a single ICS2000 device (module)."""
    entity_id: int
    name: str
    device_type: int
    ha_platform: str
    functions: list[Any] = field(default_factory=list)
    raw_status: dict = field(default_factory=dict)

    @property
    def is_on(self) -> bool | None:
        if self.functions:
            return bool(self.functions[0])
        return None

    @property
    def brightness(self) -> int | None:
        if len(self.functions) >= 2:
            return int(self.functions[1])
        return None


# ---------------------------------------------------------------------------
# Hub
# ---------------------------------------------------------------------------

class ICS2000Hub:
    """Manages communication with the ICS2000 hub via local UDP and cloud."""

    def __init__(self, mac: str, email: str, password: str) -> None:
        self._mac = mac.replace(":", "").upper()
        self._mac_colons = ":".join(self._mac[i:i+2] for i in range(0, 12, 2))
        self._email = email
        self._password = password
        self._aes_key: str | None = None
        self._home_id: int | None = None
        self._local_ip: str | None = None
        self._devices: list[ICS2000Device] = []
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Auth & Discovery
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """Login to ICS2000 cloud and retrieve AES key + home ID."""
        try:
            resp = self._session.get(
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
            _LOGGER.info("ICS2000 login OK — home_id=%s", self._home_id)

            # Discover local hub IP
            self.discover_local_hub()
            return True
        except Exception as exc:
            _LOGGER.error("ICS2000 login failed: %s", exc)
            return False

    def discover_local_hub(self) -> str | None:
        """Discover the ICS2000 local IP address using UDP broadcast."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2.0)
            
            # Send discovery to global broadcast and subnet broadcast
            targets = ["255.255.255.255"]
            try:
                # Add local broadcast if possible
                host_ip = socket.gethostbyname(socket.gethostname())
                subnet = ".".join(host_ip.split(".")[:3]) + ".255"
                targets.append(subnet)
            except Exception:
                pass

            for target in targets:
                try:
                    sock.sendto(DISCOVERY_BROADCAST_MSG, (target, HUB_UDP_PORT))
                except Exception:
                    continue

            data, addr = sock.recvfrom(1024)
            sock.close()

            # Verify response belongs to our hub MAC
            resp_hex = data.hex().lower()
            if self._mac.lower() in resp_hex:
                self._local_ip = addr[0]
                _LOGGER.info("Discovered ICS2000 hub locally at %s", self._local_ip)
                return self._local_ip
        except Exception as exc:
            _LOGGER.debug("Local UDP discovery attempt ended: %s", exc)
        return self._local_ip

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def fetch_devices(self) -> list[ICS2000Device]:
        """Fetch and decrypt all modules from the ICS2000 gateway."""
        if not self._aes_key:
            _LOGGER.error("Cannot fetch devices: not logged in")
            return []

        try:
            resp = self._session.get(
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
                continue

            mod = decrypted["module"]
            device_int = mod.get("device")
            if device_int is None or device_int in INTERNAL_MODULES:
                continue

            ha_platform = DEVICE_TYPE_MAP.get(device_int)
            if ha_platform is None:
                _LOGGER.debug("Unknown device type %s for '%s' — skipping", device_int, mod.get("name"))
                continue

            devices.append(ICS2000Device(
                entity_id=mod["id"],
                name=mod["name"],
                device_type=device_int,
                ha_platform=ha_platform,
            ))

        self._devices = devices
        return devices

    # ------------------------------------------------------------------
    # Status polling
    # ------------------------------------------------------------------

    def fetch_status(self, entity_id: int) -> list[Any]:
        """Fetch current status for an entity from cloud API."""
        if not self._aes_key:
            return []
        try:
            resp = self._session.get(
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
    # Command Sending: Local UDP with Cloud Fallback
    # ------------------------------------------------------------------

    def _send_command(self, entity_id: int, function: int, value: int | str) -> bool:
        """
        Send a command to the ICS2000.
        Tries local UDP first (instant), falls back to cloud API if needed.
        """
        if not self._aes_key:
            _LOGGER.error("Cannot send command: not logged in")
            return False

        pkt = _build_command_bytes(self._mac, entity_id, function, value, self._aes_key)

        # 1. Try Local UDP
        if not self._local_ip:
            self.discover_local_hub()

        if self._local_ip:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1.5)
                sock.sendto(pkt, (self._local_ip, HUB_UDP_PORT))
                try:
                    # Hub sends acknowledgment
                    sock.recvfrom(1024)
                except socket.timeout:
                    pass
                sock.close()
                _LOGGER.debug(
                    "Command sent via local UDP to %s: entity=%s fn=%s val=%s",
                    self._local_ip, entity_id, function, value,
                )
                return True
            except Exception as exc:
                _LOGGER.warning("Local UDP send to %s failed (%s), trying cloud fallback...", self._local_ip, exc)
                self._local_ip = None

        # 2. Cloud Fallback
        try:
            resp = self._session.get(
                f"{BASE_URL}/command.php",
                params={
                    "action": "add",
                    "email": self._email,
                    "mac": self._mac,
                    "password_hash": self._password,
                    "device_unique_id": "android",
                    "command": pkt.hex(),
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            _LOGGER.debug("Command sent via cloud: entity=%s fn=%s val=%s", entity_id, function, value)
            return True
        except Exception as exc:
            _LOGGER.error("Cloud command failed for entity %s: %s", entity_id, exc)
            return False

    def turn_on(self, entity_id: int) -> bool:
        """Turn switch or lamp on."""
        return self._send_command(entity_id, CMD_FUNCTION_SWITCH, 1)

    def turn_off(self, entity_id: int) -> bool:
        """Turn switch or lamp off."""
        return self._send_command(entity_id, CMD_FUNCTION_SWITCH, 0)

    def dim(self, entity_id: int, level: int) -> bool:
        """Set dimmer level (0–255)."""
        level = max(0, min(255, level))
        return self._send_command(entity_id, CMD_FUNCTION_DIM, level)

    def shutter_open(self, entity_id: int) -> bool:
        """Open shutter (▲)."""
        return self._send_command(entity_id, CMD_FUNCTION_SHUTTER_OPEN, SHUTTER_COMMAND_VALUE)

    def shutter_stop(self, entity_id: int) -> bool:
        """Stop shutter / MY favourite position (⏹)."""
        return self._send_command(entity_id, CMD_FUNCTION_SHUTTER_STOP, SHUTTER_COMMAND_VALUE)

    def shutter_close(self, entity_id: int) -> bool:
        """Close shutter (▼)."""
        return self._send_command(entity_id, CMD_FUNCTION_SHUTTER_CLOSE, SHUTTER_COMMAND_VALUE)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def mac(self) -> str:
        return self._mac

    @property
    def local_ip(self) -> str | None:
        return self._local_ip

    @property
    def home_id(self) -> int | None:
        return self._home_id

    @property
    def devices(self) -> list[ICS2000Device]:
        return self._devices
