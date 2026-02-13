"""The Fitness Equipment integration."""
from __future__ import annotations

import logging

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import FitnessEquipmentCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type FitnessEquipmentConfigEntry = ConfigEntry[FitnessEquipmentCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: FitnessEquipmentConfigEntry
) -> bool:
    """Set up Fitness Equipment from a config entry."""
    address: str = entry.data[CONF_ADDRESS]

    # Get the BLE device
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if not ble_device:
        raise ConfigEntryNotReady(f"Could not find BLE device with address {address}")

    # Create coordinator
    coordinator = FitnessEquipmentCoordinator(hass, entry, ble_device)

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to connect to device: {err}") from err

    # Store coordinator in entry runtime_data
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FitnessEquipmentConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()

    return unload_ok
