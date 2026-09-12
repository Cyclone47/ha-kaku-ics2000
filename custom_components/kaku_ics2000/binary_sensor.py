"""Binary sensor platform for KlikAanKlikUit ICS2000.

Handles:
  - device=4 → Contact / motion / presence sensor (e.g. Garage sensor)
"""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_BINARY_SENSOR, DOMAIN
from .entity import KakuEntity
from .hub import ICS2000Device, ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ICS2000 binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator = data["coordinator"]
    devices: list[ICS2000Device] = data["devices"]

    async_add_entities(
        KakuBinarySensor(coordinator, hub, device)
        for device in devices
        if device.ha_platform == DEVICE_TYPE_BINARY_SENSOR
    )


class KakuBinarySensor(KakuEntity, BinarySensorEntity):
    """A binary (on/off) sensor like a door or motion detector."""

    _attr_device_class = BinarySensorDeviceClass.OPENING

    @property
    def is_on(self) -> bool:
        """Return True when sensor is triggered (door open / motion detected)."""
        fns = self._functions
        return bool(fns[0]) if fns else False
