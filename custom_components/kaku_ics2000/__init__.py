"""KlikAanKlikUit ICS2000 Home Assistant integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_MAC,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)
from .hub import ICS2000Device, ICS2000Hub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.COVER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SCENE,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ICS2000 from a config entry."""
    hub = ICS2000Hub(
        mac=entry.data[CONF_MAC],
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )

    # Login in executor (blocking I/O)
    ok = await hass.async_add_executor_job(hub.login)
    if not ok:
        raise ConfigEntryNotReady("ICS2000 login failed — check credentials")

    # Initial device & scene fetch
    devices: list[ICS2000Device] = await hass.async_add_executor_job(hub.fetch_devices)
    if not devices and not hub.scenes:
        raise ConfigEntryNotReady("ICS2000 returned no devices or scenes")

    # ---------------------------------------------------------------
    # DataUpdateCoordinator — polls status for all devices
    # ---------------------------------------------------------------
    async def _async_update_data() -> dict[int, list]:
        """Fetch status for every known device."""
        statuses: dict[int, list] = {}
        for device in hub.devices:
            statuses[device.entity_id] = await hass.async_add_executor_job(
                hub.fetch_status, device.entity_id
            )
        return statuses

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{hub.mac}",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
    )

    # Perform initial refresh
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "hub": hub,
        "coordinator": coordinator,
        "devices": hub.devices,
        "scenes": hub.scenes,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
