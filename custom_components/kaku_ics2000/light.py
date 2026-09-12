"""Light platform for KlikAanKlikUit ICS2000.

Handles:
  - device=2  → Dimmer  (brightness slider + on/off)
  - device=24 → Simple on/off lamp (no dimming)
"""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_DIMMER, DEVICE_LIGHT, DEVICE_TYPE_LIGHT, DOMAIN
from .entity import KakuEntity
from .hub import ICS2000Device, ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ICS2000 lights from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator = data["coordinator"]
    devices: list[ICS2000Device] = data["devices"]

    entities = []
    for device in devices:
        if device.ha_platform != DEVICE_TYPE_LIGHT:
            continue
        if device.device_type == DEVICE_DIMMER:
            entities.append(KakuDimmerLight(coordinator, hub, device))
        else:
            entities.append(KakuOnOffLight(coordinator, hub, device))

    async_add_entities(entities)


class KakuOnOffLight(KakuEntity, LightEntity):
    """Simple on/off lamp (device=24)."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool:
        fns = self._functions
        return bool(fns[0]) if fns else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._hub.turn_on, self._device.entity_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._hub.turn_off, self._device.entity_id)
        await self.coordinator.async_request_refresh()


class KakuDimmerLight(KakuEntity, LightEntity):
    """Dimmable lamp (device=2). Supports brightness 1–255."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool:
        fns = self._functions
        return bool(fns[0]) if fns else False

    @property
    def brightness(self) -> int | None:
        """Return brightness 0-255. ICS2000 uses 0-255 scale directly."""
        fns = self._functions
        if len(fns) >= 2:
            return int(fns[1])
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            level = kwargs[ATTR_BRIGHTNESS]
            await self.hass.async_add_executor_job(
                self._hub.dim, self._device.entity_id, level
            )
        else:
            await self.hass.async_add_executor_job(
                self._hub.turn_on, self._device.entity_id
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._hub.turn_off, self._device.entity_id)
        await self.coordinator.async_request_refresh()
