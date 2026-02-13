"""Binary sensor platform for Fitness Equipment integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FitnessEquipmentConfigEntry
from .const import DOMAIN
from .coordinator import FitnessEquipmentCoordinator
from .device import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FitnessEquipmentConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fitness Equipment binary sensor platform."""
    coordinator = entry.runtime_data

    # Create a workout active sensor based on speed/power
    async_add_entities([FitnessEquipmentWorkoutSensor(coordinator, entry)])


class FitnessEquipmentWorkoutSensor(
    CoordinatorEntity[FitnessEquipmentCoordinator], BinarySensorEntity
):
    """Binary sensor for workout active state."""

    _attr_has_entity_name = True
    _attr_name = "Workout Active"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: FitnessEquipmentCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_workout_active"

        # Device info - use coordinator's manufacturer and model if available
        device_type = coordinator.data.get("device_type") if coordinator.data else None
        self._attr_device_info = get_device_info(
            entry,
            device_type,
            coordinator.manufacturer,
            coordinator.model,
        )

    @property
    def is_on(self) -> bool:
        """Return true if workout is active.
        
        Returns:
            True if any activity detected (speed, power, stroke rate, or cadence)
        """
        if not self.coordinator.data:
            return False

        try:
            # Consider workout active if there's any speed or power
            speed = self.coordinator.data.get("speed", 0) or 0
            power = self.coordinator.data.get("power", 0) or 0
            stroke_rate = self.coordinator.data.get("stroke_rate", 0) or 0
            cadence = self.coordinator.data.get("cadence", 0) or 0

            return speed > 0.5 or power > 5 or stroke_rate > 5 or cadence > 5
        except (TypeError, ValueError) as err:
            _LOGGER.warning("Error checking workout active state: %s", err)
            return False

    @property
    def available(self) -> bool:
        """Return if entity is available.
        
        Returns:
            True if coordinator has valid data
        """
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Error updating binary sensor %s: %s",
                self._attr_name,
                err,
                exc_info=True,
            )
