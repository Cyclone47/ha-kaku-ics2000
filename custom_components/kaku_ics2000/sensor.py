"""Sensor platform for KlikAanKlikUit ICS2000.

Handles:
  - device=46 → Zigbee temperature & humidity sensor
"""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_ZIGBEE_SENSOR, DEVICE_TYPE_SENSOR, DOMAIN
from .entity import KakuEntity
from .hub import ICS2000Device, ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ICS2000 sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator = data["coordinator"]
    devices: list[ICS2000Device] = data["devices"]

    entities = []
    for device in devices:
        if device.ha_platform != DEVICE_TYPE_SENSOR:
            continue
        if device.device_type == DEVICE_ZIGBEE_SENSOR:
            entities.append(KakuTemperatureSensor(coordinator, hub, device))
            entities.append(KakuHumiditySensor(coordinator, hub, device))

    async_add_entities(entities)


class KakuTemperatureSensor(KakuEntity, SensorEntity):
    """Temperature reading from a Zigbee sensor (device=46)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, hub: ICS2000Hub, device: ICS2000Device) -> None:
        super().__init__(coordinator, hub, device)
        self._attr_unique_id = f"{DOMAIN}_{device.entity_id}_temperature"
        self._attr_name = f"{device.name} Temperature"

    @property
    def native_value(self) -> float | None:
        """Return temperature in °C. ICS2000 stores as value/100."""
        fns = self._functions
        if len(fns) >= 1 and fns[0] is not None:
            try:
                return round(fns[0] / 100, 1)
            except (TypeError, ValueError):
                return None
        return None


class KakuHumiditySensor(KakuEntity, SensorEntity):
    """Humidity reading from a Zigbee sensor (device=46)."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, hub: ICS2000Hub, device: ICS2000Device) -> None:
        super().__init__(coordinator, hub, device)
        self._attr_unique_id = f"{DOMAIN}_{device.entity_id}_humidity"
        self._attr_name = f"{device.name} Humidity"

    @property
    def native_value(self) -> float | None:
        """Return humidity %. ICS2000 stores as value/100."""
        fns = self._functions
        if len(fns) >= 2 and fns[1] is not None:
            try:
                return round(fns[1] / 100, 1)
            except (TypeError, ValueError):
                return None
        return None
