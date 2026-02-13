"""Sensor platform for Fitness Equipment integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)
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
    """Set up Fitness Equipment sensor platform."""
    coordinator = entry.runtime_data

    # Create all sensors upfront - they will show as unavailable until data arrives
    # This allows sensors to appear even if the device hasn't sent data yet
    entities: list[FitnessEquipmentSensor] = []

    # Common sensors for all device types - always create these
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Speed",
            "speed",
            UnitOfSpeed.KILOMETERS_PER_HOUR,
            SensorDeviceClass.SPEED,
            "mdi:speedometer",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Average Speed",
            "average_speed",
            UnitOfSpeed.KILOMETERS_PER_HOUR,
            SensorDeviceClass.SPEED,
            "mdi:speedometer-medium",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Distance",
            "distance",
            UnitOfLength.METERS,
            SensorDeviceClass.DISTANCE,
            "mdi:map-marker-distance",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Calories",
            "calories",
            UnitOfEnergy.KILO_CALORIE,
            None,
            "mdi:fire",
        )
    )
    
    # Heart Rate - FTMS (embedded in workout data)
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Heart Rate (FTMS)",
            "heart_rate_ftms",
            "bpm",
            None,
            "mdi:heart-pulse",
        )
    )
    
    # Heart Rate - HRS (dedicated Heart Rate Service - more accurate)
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Heart Rate (HRS)",
            "heart_rate_hrs",
            "bpm",
            None,
            "mdi:heart",
        )
    )
    
    # Energy Expended from HRS
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Energy Expended (HRS)",
            "energy_expended_hrs",
            UnitOfEnergy.KILO_JOULE,
            SensorDeviceClass.ENERGY,
            "mdi:lightning-bolt-circle",
        )
    )
    
    # RR-Intervals (HRV data)
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "RR Intervals",
            "rr_intervals",
            "ms",
            None,
            "mdi:heart-pulse",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Power",
            "power",
            UnitOfPower.WATT,
            SensorDeviceClass.POWER,
            "mdi:lightning-bolt",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Elapsed Time",
            "elapsed_time",
            UnitOfTime.SECONDS,
            SensorDeviceClass.DURATION,
            "mdi:timer",
        )
    )

    # Device-specific sensors - create all for treadmill since that's what KICKR RUN is
    # Create treadmill-specific sensors
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Inclination",
            "inclination",
            PERCENTAGE,
            None,
            "mdi:slope-uphill",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Pace",
            "pace",
            "min/km",
            None,
            "mdi:run",
        )
    )

    # Also create bike sensors if unknown device type (will auto-hide if not applicable)
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Cadence",
            "cadence",
            "rpm",
            None,
            "mdi:rotate-right",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Average Cadence",
            "average_cadence",
            "rpm",
            None,
            "mdi:rotate-right",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Average Power",
            "average_power",
            UnitOfPower.WATT,
            SensorDeviceClass.POWER,
            "mdi:lightning-bolt-outline",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Resistance",
            "resistance",
            None,
            None,
            "mdi:gauge",
        )
    )

    # Rower sensors
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Stroke Rate",
            "stroke_rate",
            "spm",
            None,
            "mdi:rowing",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Average Stroke Rate",
            "average_stroke_rate",
            "spm",
            None,
            "mdi:rowing",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Stroke Count",
            "stroke_count",
            None,
            None,
            "mdi:counter",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Rower Pace",
            "pace",
            "sec/500m",
            None,
            "mdi:speedometer",
        )
    )
    
    entities.append(
        FitnessEquipmentSensor(
            coordinator,
            entry,
            "Rower Average Pace",
            "average_pace",
            "sec/500m",
            None,
            "mdi:speedometer",
        )
    )

    async_add_entities(entities)


class FitnessEquipmentSensor(CoordinatorEntity[FitnessEquipmentCoordinator], SensorEntity):
    """Representation of a Fitness Equipment sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: FitnessEquipmentCoordinator,
        entry: ConfigEntry,
        name: str,
        data_key: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        icon: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._data_key = data_key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{data_key}"
        
        # Set suggested display precision based on sensor type
        if data_key in ("speed", "average_speed", "cadence", "average_cadence", "stroke_rate", "average_stroke_rate"):
            self._attr_suggested_display_precision = 1
        elif data_key in ("power", "average_power", "heart_rate_ftms", "heart_rate_hrs", "calories", "energy_expended_hrs"):
            self._attr_suggested_display_precision = 0
        elif data_key == "distance":
            self._attr_suggested_display_precision = 0
        elif data_key == "rr_intervals":
            self._attr_suggested_display_precision = 1  # milliseconds with 1 decimal

        # Device info - use coordinator's manufacturer and model if available
        device_type = coordinator.data.get("device_type") if coordinator.data else None
        self._attr_device_info = get_device_info(
            entry,
            device_type,
            coordinator.manufacturer,
            coordinator.model,
        )

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor.
        
        Returns:
            Sensor value or None if not available
        """
        if not self.coordinator.data:
            return None
        
        value = self.coordinator.data.get(self._data_key)
        
        # Special handling for RR intervals (HRV data) - could be a list
        if self._data_key == "rr_intervals" and isinstance(value, list):
            # Return the most recent RR interval if available
            if value:
                return value[-1]
            return None
        
        # Validate numeric values
        if value is not None and not isinstance(value, (int, float)):
            _LOGGER.warning(
                "Invalid value type for %s: %s (expected int or float)",
                self._data_key,
                type(value).__name__,
            )
            return None
        
        return value

    @property
    def available(self) -> bool:
        """Return if entity is available.
        
        Returns:
            True if sensor data is available and valid
        """
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._data_key in self.coordinator.data
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Error updating sensor %s: %s",
                self._attr_name,
                err,
                exc_info=True,
            )
