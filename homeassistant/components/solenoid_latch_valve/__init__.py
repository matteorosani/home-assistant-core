"""The Solenoid latch valve integration."""

from __future__ import annotations

from RPi import GPIO

from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

PLATFORMS: list[Platform] = [Platform.SWITCH]

CONFIG_SCHEMA = cv.empty_config_schema


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Raspberry PI GPIO component."""

    def cleanup_gpio(event):
        """Stuff to do before stopping."""
        GPIO.cleanup()

    def prepare_gpio(event):
        """Stuff to do when Home Assistant starts."""
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, cleanup_gpio)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, prepare_gpio)
    GPIO.setmode(GPIO.BCM)
    return True


def setup_output(port):
    """Set up a GPIO as output."""
    GPIO.setup(port, GPIO.OUT)


def write_output(port, value):
    """Write a value to a GPIO."""
    GPIO.output(port, value)
