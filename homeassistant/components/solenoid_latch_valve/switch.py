"""Allows to configure a valve using RPi GPIO."""

from __future__ import annotations

from time import sleep
from typing import Any

import voluptuous as vol

from homeassistant.components.switch import (
    PLATFORM_SCHEMA as SWITCH_PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_PORT,
    CONF_UNIQUE_ID,
    DEVICE_DEFAULT_NAME,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.reload import setup_reload_service
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import PLATFORMS, setup_output, write_output
from .const import CONF_BLACK_WIRE_PORT, CONF_RED_WIRE_PORT, CONF_VALVES, DOMAIN

_VALVE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_PORT): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_VALVES): vol.All(cv.ensure_list, [_VALVE_SCHEMA]),
        vol.Required(CONF_RED_WIRE_PORT): cv.positive_int,
        vol.Required(CONF_BLACK_WIRE_PORT): cv.positive_int,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Raspberry PI GPIO devices."""
    setup_reload_service(hass, DOMAIN, PLATFORMS)

    valves = []

    valves_conf: ConfigType | None = config.get(CONF_VALVES)

    if valves_conf is None:
        return

    setup_output(valves_conf[CONF_RED_WIRE_PORT])
    setup_output(valves_conf[CONF_BLACK_WIRE_PORT])

    valves = [
        PersistentRPiGPIOValve(
            valve[CONF_NAME],
            valve[CONF_PORT],
            valves_conf[CONF_RED_WIRE_PORT],
            valves_conf[CONF_BLACK_WIRE_PORT],
            valve[CONF_UNIQUE_ID],
        )
        for valve in valves_conf[CONF_VALVES]
    ]

    add_entities(valves, True)


class RPiGPIOValve(SwitchEntity):
    """Representation of a Raspberry Pi GPIO."""

    def __init__(
        self,
        name,
        port,
        red_wire_port,
        black_wire_port,
        unique_id=None,
        skip_reset=False,
    ) -> None:
        """Initialize the pin."""
        self._attr_name = name or DEVICE_DEFAULT_NAME
        self._attr_unique_id = unique_id
        self._attr_should_poll = False
        self._attr_assumed_state = True
        self._port = port
        self._red_wire_port = red_wire_port
        self._black_wire_port = black_wire_port
        self._state = False
        setup_output(self._port)
        if not skip_reset:
            write_output(self._red_wire_port, 1)
            write_output(self._black_wire_port, 0)
            sleep(0.5)
            write_output(self._port, 1)

    def _pulse(self):
        write_output(self._port, 0)
        sleep(0.1)
        write_output(self._port, 1)

    @property
    def is_on(self) -> bool | None:
        """Return true if the valve is open."""
        return self._state

    def turn_on(self, **kwargs: Any) -> None:
        """Open the valve."""
        write_output(self._red_wire_port, 0)
        write_output(self._black_wire_port, 1)
        sleep(0.5)
        self._pulse()
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs: Any) -> None:
        """Close the valve."""
        write_output(self._red_wire_port, 1)
        write_output(self._black_wire_port, 0)
        sleep(0.5)
        self._pulse()
        self._state = False
        self.schedule_update_ha_state()


class PersistentRPiGPIOValve(RPiGPIOValve, RestoreEntity):
    """Representation of a persistent Raspberry Pi GPIO."""

    def __init__(
        self, name, port, red_wire_port, black_wire_port, unique_id=None
    ) -> None:
        """Initialize the pin."""
        super().__init__(name, port, red_wire_port, black_wire_port, unique_id, True)

    async def async_added_to_hass(self) -> None:
        """Call when the switch is added to hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._state = state.state == STATE_ON
        if self._state:
            await self.async_turn_on()
        else:
            await self.async_turn_off()
