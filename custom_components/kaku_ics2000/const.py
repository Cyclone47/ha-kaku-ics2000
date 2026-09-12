"""Constants for the KlikAanKlikUit ICS2000 integration."""

DOMAIN = "kaku_ics2000"
CONF_MAC = "mac"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# ICS2000 Cloud API
BASE_URL = "https://trustsmartcloud2.com/ics2000_api"

# How often to poll the hub (seconds)
SCAN_INTERVAL_SECONDS = 30

# Device type integers returned by the ICS2000 API
# These were reverse-engineered by querying the cloud API directly.
DEVICE_SWITCH = 1        # Aan/uit schakelaar, generic on/off
DEVICE_DIMMER = 2        # Dimmer (brightness + on/off)
DEVICE_OPENCLOSE = 3     # Open/close (e.g. garage door motor)
DEVICE_SENSOR = 4        # Binary sensor (e.g. door sensor, motion)
DEVICE_REMOTE = 8        # Remote/button (wall switch, keyfob) — not controllable
DEVICE_SHUTTER = 23      # Rolluik / blind / shutter (up/my/down)
DEVICE_LIGHT = 24        # Simple on/off lamp (no dimming)
DEVICE_SWITCH_GROUP = 27 # Switch group
DEVICE_KEYFOB = 29       # Key fob remote — not controllable
DEVICE_ZIGBEE_SENSOR = 46  # Zigbee temperature & humidity sensor

# Internal hub modules — skip these
INTERNAL_MODULES = {238, 239, 240, 241, 242, 243}

# Devices that HA can control/display
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

# ICS2000 command function codes
CMD_FUNCTION_SWITCH = 0   # on (value=1) / off (value=0)
CMD_FUNCTION_DIM = 1      # dim level 0–255
CMD_FUNCTION_SHUTTER = 2  # shutter: 0=stop, 1=open, 2=close (MY position)

# Shutter command values
SHUTTER_OPEN = 1
SHUTTER_STOP = 0
SHUTTER_CLOSE = 2
