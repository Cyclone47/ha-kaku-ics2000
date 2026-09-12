"""Base entity for the KlikAanKlikUit ICS2000 integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import ICS2000Device, ICS2000Hub


class KakuEntity(CoordinatorEntity):
    """Base class for all ICS2000 entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, hub: ICS2000Hub, device: ICS2000Device) -> None:
        super().__init__(coordinator)
        self._hub = hub
        self._device = device
        self._attr_unique_id = f"{DOMAIN}_{device.entity_id}"
        self._attr_name = device.name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info so all entities group under one device card."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device.entity_id))},
            name=self._device.name,
            manufacturer="KlikAanKlikUit / Trust",
            model=f"ICS2000 device (type {self._device.device_type})",
            via_device=(DOMAIN, self._hub.mac),
        )

    @property
    def _functions(self) -> list:
        """Return the current status function list from the coordinator."""
        return self.coordinator.data.get(self._device.entity_id, [])
