"""Cover platform for KlikAanKlikUit ICS2000.

Handles:
  - device=23 → Rolluik / blind / shutter  (open ▲ / stop MY / close ▼)
  - device=3  → Garage door motor (open/close)

The ICS2000 does NOT report shutter position percentages — covers show
as 'open' or 'closed' based on the last command sent (optimistic).
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_OPENCLOSE, DEVICE_SHUTTER, DEVICE_TYPE_COVER, DOMAIN
from .entity import KakuEntity
from .hub import ICS2000Device, ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ICS2000 covers from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator = data["coordinator"]
    devices: list[ICS2000Device] = data["devices"]

    entities = []
    for device in devices:
        if device.ha_platform != DEVICE_TYPE_COVER:
            continue
        if device.device_type == DEVICE_SHUTTER:
            entities.append(KakuShutter(coordinator, hub, device))
        elif device.device_type == DEVICE_OPENCLOSE:
            entities.append(KakuGarageDoor(coordinator, hub, device))

    async_add_entities(entities)


class KakuShutter(KakuEntity, CoverEntity):
    """
    Rolluik / shutter cover entity (device=23).

    Supports Open, Close, and Stop (MY favourite position).
    Position percentage is not available from the ICS2000 API.
    """

    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )

    def __init__(self, coordinator, hub: ICS2000Hub, device: ICS2000Device) -> None:
        super().__init__(coordinator, hub, device)
        # Optimistic state tracking
        self._is_closed: bool | None = None

    @property
    def is_closed(self) -> bool | None:
        """Return True if shutter is closed, False if open, None if unknown."""
        return self._is_closed

    @property
    def is_opening(self) -> bool:
        return False

    @property
    def is_closing(self) -> bool:
        return False

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the shutter (▲)."""
        await self.hass.async_add_executor_job(
            self._hub.shutter_open, self._device.entity_id
        )
        self._is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the shutter (▼)."""
        await self.hass.async_add_executor_job(
            self._hub.shutter_close, self._device.entity_id
        )
        self._is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the shutter at MY favourite position."""
        await self.hass.async_add_executor_job(
            self._hub.shutter_stop, self._device.entity_id
        )
        # After stop we don't know exact position
        self._is_closed = None
        self.async_write_ha_state()


class KakuGarageDoor(KakuEntity, CoverEntity):
    """
    Garage door / open-close motor (device=3).

    Supports Open and Close only (no stop position feedback).
    """

    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, coordinator, hub: ICS2000Hub, device: ICS2000Device) -> None:
        super().__init__(coordinator, hub, device)
        self._is_closed: bool | None = None

    @property
    def is_closed(self) -> bool | None:
        fns = self._functions
        if fns:
            return not bool(fns[0])
        return self._is_closed

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._hub.turn_on, self._device.entity_id)
        self._is_closed = False
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._hub.turn_off, self._device.entity_id)
        self._is_closed = True
        await self.coordinator.async_request_refresh()
