"""Config flow for KlikAanKlikUit ICS2000 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_MAC, DOMAIN
from .hub import ICS2000Hub

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC, description={"suggested_value": "AA:BB:CC:DD:EE:FF"}): str,
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user's credentials by attempting login."""
    hub = ICS2000Hub(
        mac=data[CONF_MAC],
        email=data[CONF_EMAIL],
        password=data[CONF_PASSWORD],
    )
    success = await hass.async_add_executor_job(hub.login)
    if not success:
        raise ValueError("invalid_auth")
    return {"title": f"ICS2000 ({data[CONF_MAC].upper()})"}


class KakuICS2000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for KlikAanKlikUit ICS2000."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial (user) step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Normalise MAC: strip colons, uppercase
            mac = user_input[CONF_MAC].replace(":", "").replace("-", "").upper()
            if len(mac) != 12 or not all(c in "0123456789ABCDEF" for c in mac):
                errors[CONF_MAC] = "invalid_mac"
            else:
                # Format with colons for display
                user_input[CONF_MAC] = ":".join(mac[i:i+2] for i in range(0, 12, 2))
                try:
                    info = await _validate_input(self.hass, user_input)
                except ValueError:
                    errors["base"] = "invalid_auth"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error during ICS2000 login")
                    errors["base"] = "cannot_connect"
                else:
                    # Prevent duplicate entries for the same MAC
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
