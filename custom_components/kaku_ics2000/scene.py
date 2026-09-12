"""Scene platform for KlikAanKlikUit ICS2000.

Provides native Home Assistant Scene entities for all ICS2000 scenes.
Activating a scene sends the run command directly to the hub via local UDP.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
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
    """Set up ICS2000 scenes from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    scenes: list[ICS2000Scene] = hub.scenes

    async_add_entities(
        KakuSceneEntity(hub, scene) for scene in scenes
    )


class KakuSceneEntity(Scene):
    """Represents an ICS2000 scene in Home Assistant."""

    _attr_has_entity_name = True

    def __init__(self, hub: ICS2000Hub, scene: ICS2000Scene) -> None:
        self._hub = hub
        self._scene = scene
        self._attr_unique_id = f"{DOMAIN}_scene_{scene.entity_id}"
        self._attr_name = scene.name

    @property
    def device_info(self) -> DeviceInfo:
        """Group scenes under the ICS2000 Hub device card."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub.mac)},
            name="KlikAanKlikUit ICS2000 Hub",
            manufacturer="KlikAanKlikUit / Trust",
            model="ICS2000",
        )

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate (play) this scene."""
        await self.hass.async_add_executor_job(
            self._hub.run_scene, self._scene.entity_id
        )
