"""Constants for the KlikAanKlikUit ICS2000 integration."""

DOMAIN = "kaku_ics2000"
CONF_MAC = "mac"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# ICS2000 Cloud API
BASE_URL = "https://trustsmartcloud2.com/ics2000_api"

# Local hub UDP port
HUB_UDP_PORT = 2012
# Discovery broadcast message
DISCOVERY_BROADCAST_MSG = bytes.fromhex(
    "010003ffffffffffffca000000010400044795000401040004000400040000000000000000020000003000"
)

# How often to poll the hub for status (seconds)
SCAN_INTERVAL_SECONDS = 30

# Device type integers returned by the ICS2000 API
DEVICE_SWITCH = 1          # Aan/uit schakelaar, generic on/off
DEVICE_DIMMER = 2          # Dimmer (brightness + on/off)
DEVICE_OPENCLOSE = 3       # Open/close actuator (e.g. garage door motor)
DEVICE_SENSOR = 4          # Binary sensor (contact, motion)
DEVICE_REMOTE = 8          # Remote/button — not controllable
DEVICE_SHUTTER = 23        # Somfy / Rolluik shutter actuator
DEVICE_LIGHT = 24          # Simple lamp (on/off)
DEVICE_SWITCH_GROUP = 27   # Switch group
DEVICE_KEYFOB = 29         # Key fob remote
DEVICE_ZIGBEE_SENSOR = 46  # Zigbee temperature & humidity sensor

# Internal hub modules — skip these
INTERNAL_MODULES = {238, 239, 240, 241, 242, 243}

# HA Platform types
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_COVER = "cover"
DEVICE_TYPE_SENSOR = "sensor"
DEVICE_TYPE_BINARY_SENSOR = "binary_sensor"

# Map device integer → HA platform
DEVICE_TYPE_MAP: dict[int, str] = {
    DEVICE_SWITCH: DEVICE_TYPE_SWITCH,
    DEVICE_DIMMER: DEVICE_TYPE_LIGHT,
    DEVICE_OPENCLOSE: DEVICE_TYPE_COVER,
    DEVICE_SENSOR: DEVICE_TYPE_BINARY_SENSOR,
    DEVICE_SHUTTER: DEVICE_TYPE_COVER,
    DEVICE_LIGHT: DEVICE_TYPE_LIGHT,
    DEVICE_SWITCH_GROUP: DEVICE_TYPE_SWITCH,
    DEVICE_ZIGBEE_SENSOR: DEVICE_TYPE_SENSOR,
}

# Standard switch / dimmer command functions
CMD_FUNCTION_SWITCH = 0     # on (value=1) / off (value=0)
CMD_FUNCTION_DIM = 1        # dim level 0–255

# Somfy Shutter command functions (device=23)
# Discovered from ICS2000 live rules/scenarios:
# "Rolluiken open": function=0, value=1
# "Rolluik stop / MY": function=1, value=1
# "Rolluik dicht": function=2, value=1
CMD_FUNCTION_SHUTTER_OPEN = 0
CMD_FUNCTION_SHUTTER_STOP = 1
CMD_FUNCTION_SHUTTER_CLOSE = 2
SHUTTER_COMMAND_VALUE = 1
