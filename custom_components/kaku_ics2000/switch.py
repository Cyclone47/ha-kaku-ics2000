"""Switch platform for KlikAanKlikUit ICS2000.

Handles:
  - device=1  → Aan/uit schakelaar (generic on/off switch)
  - device=3  → Open/close (e.g. garage door motor used as switch)
  - device=27 → Switch group
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_SWITCH, DOMAIN
from .entity import KakuEntity
from .hub import ICS2000Device, ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ICS2000 switches from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator = data["coordinator"]
    devices: list[ICS2000Device] = data["devices"]

    async_add_entities(
        KakuSwitch(coordinator, hub, device)
        for device in devices
        if device.ha_platform == DEVICE_TYPE_SWITCH
    )


class KakuSwitch(KakuEntity, SwitchEntity):
    """Represents an ICS2000 on/off switch."""

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
