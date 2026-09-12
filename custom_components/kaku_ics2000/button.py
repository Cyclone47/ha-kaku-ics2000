"""Button platform for KlikAanKlikUit ICS2000.

Provides explicit Play and Stop button entities for each ICS2000 scene,
matching the play/stop buttons in the official Klik Aan Klik Uit mobile app.
"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import ICS2000Hub, ICS2000Scene

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ICS2000 scene Play and Stop buttons from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    scenes: list[ICS2000Scene] = hub.scenes

    entities: list[ButtonEntity] = []
    for scene in scenes:
        entities.append(KakuScenePlayButton(hub, scene))
        entities.append(KakuSceneStopButton(hub, scene))

    async_add_entities(entities)


class KakuScenePlayButton(ButtonEntity):
    """Button to Play (run) an ICS2000 scene."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, hub: ICS2000Hub, scene: ICS2000Scene) -> None:
        self._hub = hub
        self._scene = scene
        self._attr_unique_id = f"{DOMAIN}_button_play_{scene.entity_id}"
        self._attr_name = f"Play {scene.name}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub.mac)},
            name="KlikAanKlikUit ICS2000 Hub",
            manufacturer="KlikAanKlikUit / Trust",
            model="ICS2000",
        )

    async def async_press(self) -> None:
        """Press the Play button."""
        await self.hass.async_add_executor_job(
            self._hub.run_scene, self._scene.entity_id
        )


class KakuSceneStopButton(ButtonEntity):
    """Button to Stop an ICS2000 scene."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:stop-circle-outline"

    def __init__(self, hub: ICS2000Hub, scene: ICS2000Scene) -> None:
        self._hub = hub
        self._scene = scene
        self._attr_unique_id = f"{DOMAIN}_button_stop_{scene.entity_id}"
        self._attr_name = f"Stop {scene.name}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub.mac)},
            name="KlikAanKlikUit ICS2000 Hub",
            manufacturer="KlikAanKlikUit / Trust",
            model="ICS2000",
        )

    async def async_press(self) -> None:
        """Press the Stop button."""
        await self.hass.async_add_executor_job(
            self._hub.stop_scene, self._scene.entity_id
        )
