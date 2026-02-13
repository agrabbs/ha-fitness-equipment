"""Fitness Machine Service (FTMS) handler for BLE fitness equipment.

Implements the Bluetooth FTMS specification for treadmills, bikes, and rowers.
This is the primary service for workout data.

Specification: https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/
"""
from __future__ import annotations

from logging import Logger
from typing import Any

from bleak import BleakClient, BleakError

from ..ftms_parser import FTMSParser, IndoorBikeData, RowerData, TreadmillData
from .base import BLEServiceBase

# Import FTMS UUIDs - will be moved to const later
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
FTMS_TREADMILL_DATA_UUID = "00002acd-0000-1000-8000-00805f9b34fb"
FTMS_INDOOR_BIKE_DATA_UUID = "00002ad2-0000-1000-8000-00805f9b34fb"
FTMS_ROWER_DATA_UUID = "00002ad1-0000-1000-8000-00805f9b34fb"


class FTMSService(BLEServiceBase):
    """Fitness Machine Service (FTMS) handler.
    
    Detects device type (treadmill/bike/rower) and parses workout data:
    - Speed, distance, calories
    - Device-specific metrics (incline, cadence, stroke rate)
    - Heart rate (if provided by device)
    - Power output
    """

    SERVICE_UUID = FTMS_SERVICE_UUID

    def __init__(self, client: BleakClient, logger: Logger) -> None:
        """Initialize the FTMS service handler.
        
        Args:
            client: The BleakClient connected to the device
            logger: Logger instance for this service
        """
        super().__init__(client, logger)
        self._parser = FTMSParser()
        self._device_type: str | None = None
        self._characteristic_uuid: str | None = None

    @property
    def device_type(self) -> str | None:
        """Get the detected device type.
        
        Returns:
            'treadmill', 'bike', 'rower', or None if not detected
        """
        return self._device_type

    async def is_available(self) -> bool:
        """Check if FTMS service is available and detect device type.
        
        Returns:
            True if FTMS service exists with supported characteristics
        """
        try:
            services = self._client.services
            if not services:
                return False

            ftms_service = services.get_service(self.SERVICE_UUID)
            if not ftms_service:
                self._logger.debug("FTMS service not found")
                return False

            # Detect device type by checking available characteristics
            characteristics = ftms_service.characteristics
            for char in characteristics:
                if char.uuid == FTMS_TREADMILL_DATA_UUID:
                    self._device_type = "treadmill"
                    self._characteristic_uuid = FTMS_TREADMILL_DATA_UUID
                    self._logger.info("Detected treadmill device")
                    return True
                elif char.uuid == FTMS_INDOOR_BIKE_DATA_UUID:
                    self._device_type = "bike"
                    self._characteristic_uuid = FTMS_INDOOR_BIKE_DATA_UUID
                    self._logger.info("Detected indoor bike device")
                    return True
                elif char.uuid == FTMS_ROWER_DATA_UUID:
                    self._device_type = "rower"
                    self._characteristic_uuid = FTMS_ROWER_DATA_UUID
                    self._logger.info("Detected rower device")
                    return True

            self._logger.warning("FTMS service found but no supported device type")
            return False

        except (BleakError, AttributeError) as err:
            self._logger.debug("Error checking FTMS service: %s", err)
            return False

    async def subscribe(self) -> None:
        """Subscribe to FTMS workout data notifications.
        
        Raises:
            BleakError: If subscription fails
            ValueError: If device type not detected
        """
        if self._subscribed:
            return

        if not self._characteristic_uuid or not self._device_type:
            raise ValueError("Device type not detected - call is_available() first")

        try:
            await self._client.start_notify(
                self._characteristic_uuid,
                self._handle_ftms_notification
            )
            self._subscribed = True
            self._logger.info(
                "Subscribed to FTMS %s data",
                self._device_type
            )

        except (BleakError, AttributeError) as err:
            self._logger.error("Failed to subscribe to FTMS: %s", err)
            raise

    async def unsubscribe(self) -> None:
        """Unsubscribe from FTMS notifications."""
        if not self._subscribed or not self._characteristic_uuid:
            return

        try:
            await self._client.stop_notify(self._characteristic_uuid)
            self._subscribed = False
            self._logger.debug("Unsubscribed from FTMS")
        except (BleakError, AttributeError) as err:
            self._logger.debug("Error unsubscribing from FTMS: %s", err)

    def handle_notification(self, sender: int, data: bytes) -> None:
        """Handle FTMS notification.
        
        Args:
            sender: The characteristic handle
            data: The raw FTMS data
        """
        self._handle_ftms_notification(sender, data)

    def _handle_ftms_notification(self, sender: int, data: bytes) -> None:
        """Parse and handle FTMS notification.
        
        Args:
            sender: The characteristic handle
            data: Raw FTMS measurement data
        """
        if not data:
            self._logger.warning("Received empty FTMS notification")
            return

        try:
            # Parse based on device type
            if self._device_type == "treadmill":
                treadmill_data = self._parser.parse_treadmill_data(data)
                self._data = self._treadmill_to_dict(treadmill_data)
            elif self._device_type == "bike":
                bike_data = self._parser.parse_indoor_bike_data(data)
                self._data = self._bike_to_dict(bike_data)
            elif self._device_type == "rower":
                rower_data = self._parser.parse_rower_data(data)
                self._data = self._rower_to_dict(rower_data)
            else:
                self._logger.warning("Unknown device type: %s", self._device_type)
                return

            self._logger.debug(
                "FTMS %s data: Speed=%.1f, HR=%s",
                self._device_type,
                self._data.get("speed", 0),
                self._data.get("heart_rate"),
            )

        except Exception as err:
            self._logger.warning("Failed to parse FTMS data: %s", err)

    def _treadmill_to_dict(self, data: TreadmillData) -> dict[str, Any]:
        """Convert treadmill data to dictionary.
        
        Args:
            data: Parsed treadmill data from FTMS
            
        Returns:
            Dictionary with sensor values (prefixed with ftms_)
        """
        return {
            "device_type": "treadmill",
            "speed": data.instant_speed,
            "average_speed": data.average_speed,
            "distance": data.total_distance,
            "inclination": data.inclination,
            "elevation_gain": data.elevation_gain,
            "pace": data.instant_pace,
            "calories": data.total_energy,
            "heart_rate_ftms": data.heart_rate,  # Prefix to distinguish from HRS
            "power": data.power_output,
            "elapsed_time": data.elapsed_time,
            "remaining_time": data.remaining_time,
        }

    def _bike_to_dict(self, data: IndoorBikeData) -> dict[str, Any]:
        """Convert bike data to dictionary.
        
        Args:
            data: Parsed bike data from FTMS
            
        Returns:
            Dictionary with sensor values (prefixed with ftms_)
        """
        return {
            "device_type": "bike",
            "speed": data.instant_speed,
            "average_speed": data.average_speed,
            "cadence": data.instant_cadence,
            "average_cadence": data.average_cadence,
            "distance": data.total_distance,
            "resistance": data.resistance_level,
            "power": data.instant_power,
            "average_power": data.average_power,
            "calories": data.total_energy,
            "heart_rate_ftms": data.heart_rate,  # Prefix to distinguish from HRS
            "elapsed_time": data.elapsed_time,
            "remaining_time": data.remaining_time,
        }

    def _rower_to_dict(self, data: RowerData) -> dict[str, Any]:
        """Convert rower data to dictionary.
        
        Args:
            data: Parsed rower data from FTMS
            
        Returns:
            Dictionary with sensor values (prefixed with ftms_)
        """
        return {
            "device_type": "rower",
            "stroke_rate": data.stroke_rate,
            "stroke_count": data.stroke_count,
            "average_stroke_rate": data.average_stroke_rate,
            "distance": data.total_distance,
            "pace": data.instant_pace,
            "average_pace": data.average_pace,
            "power": data.instant_power,
            "average_power": data.average_power,
            "resistance": data.resistance_level,
            "calories": data.total_energy,
            "heart_rate_ftms": data.heart_rate,  # Prefix to distinguish from HRS
            "elapsed_time": data.elapsed_time,
            "remaining_time": data.remaining_time,
        }
