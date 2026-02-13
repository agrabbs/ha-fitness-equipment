"""Coordinator for Fitness Equipment integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Final

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEVICE_INFO_SERVICE_UUID,
    DOMAIN,
    FTMS_INDOOR_BIKE_DATA_UUID,
    FTMS_ROWER_DATA_UUID,
    FTMS_SERVICE_UUID,
    FTMS_TREADMILL_DATA_UUID,
    MANUFACTURER_NAME_UUID,
    MODEL_NUMBER_UUID,
)
from .ftms_parser import (
    FTMSParser,
    IndoorBikeData,
    RowerData,
    TreadmillData,
)

_LOGGER = logging.getLogger(__name__)

# Connection constants
RECONNECT_DELAY: Final = 5  # seconds
MAX_RECONNECT_ATTEMPTS: Final = 3
CONNECTION_TIMEOUT: Final = 30  # seconds


class FitnessEquipmentCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Fitness Equipment device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        ble_device: BLEDevice,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=30),  # Fallback polling
        )
        self.entry = entry
        self.ble_device = ble_device
        self._client: BleakClient | None = None
        self._device_type: str | None = None
        self._expected_disconnected = False
        self._parser = FTMSParser()
        self.manufacturer: str | None = None
        self.model: str | None = None

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        # Connect and determine device type
        await self._ensure_connected()

    async def _ensure_connected(self) -> None:
        """Ensure we have a connection to the device.
        
        Raises:
            UpdateFailed: If connection fails after retries
        """
        if self._client and self._client.is_connected:
            return

        _LOGGER.debug(
            "Connecting to %s (%s)",
            self.ble_device.name or "Unknown",
            self.ble_device.address,
        )
        
        last_error: Exception | None = None
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            try:
                self._client = await asyncio.wait_for(
                    establish_connection(
                        BleakClient,
                        self.ble_device,
                        self.ble_device.address,
                        self._on_disconnect,
                        use_services_cache=True,
                        ble_device_callback=lambda: self.ble_device,
                    ),
                    timeout=CONNECTION_TIMEOUT,
                )
                break  # Connection successful
            except asyncio.TimeoutError as err:
                last_error = err
                _LOGGER.warning(
                    "Connection timeout for %s (attempt %d/%d)",
                    self.ble_device.address,
                    attempt,
                    MAX_RECONNECT_ATTEMPTS,
                )
                if attempt < MAX_RECONNECT_ATTEMPTS:
                    await asyncio.sleep(RECONNECT_DELAY)
            except BleakError as err:
                last_error = err
                _LOGGER.warning(
                    "Connection error for %s: %s (attempt %d/%d)",
                    self.ble_device.address,
                    err,
                    attempt,
                    MAX_RECONNECT_ATTEMPTS,
                )
                if attempt < MAX_RECONNECT_ATTEMPTS:
                    await asyncio.sleep(RECONNECT_DELAY)
        
        if not self._client or not self._client.is_connected:
            error_msg = f"Failed to connect to {self.ble_device.address} after {MAX_RECONNECT_ATTEMPTS} attempts"
            if last_error:
                error_msg = f"{error_msg}: {last_error}"
            _LOGGER.error(error_msg)
            raise UpdateFailed(error_msg)

        # Read device information (manufacturer, model, etc.)
        await self._read_device_info()

        # Determine device type by checking available characteristics
        try:
            await self._detect_device_type()
        except Exception as err:
            _LOGGER.error("Failed to detect device type: %s", err)
            raise UpdateFailed(f"Failed to detect device type: {err}") from err

        _LOGGER.info(
            "Connected to %s (%s) - Type: %s, Manufacturer: %s",
            self.ble_device.name or "Unknown",
            self.ble_device.address,
            self._device_type or "Unknown",
            self.manufacturer or "Unknown",
        )
    
    async def _read_device_info(self) -> None:
        """Read device information from Device Information Service.
        
        Reads manufacturer name and model number if available.
        """
        if not self._client:
            return
            
        try:
            services = self._client.services
            if not services:
                _LOGGER.debug("No services available to read device info")
                return
                
            # Try to get Device Information Service
            device_info_service = services.get_service(DEVICE_INFO_SERVICE_UUID)
            if not device_info_service:
                _LOGGER.debug("Device Information Service not available")
                return
            
            # Read manufacturer name
            try:
                manufacturer_char = device_info_service.get_characteristic(
                    MANUFACTURER_NAME_UUID
                )
                if manufacturer_char:
                    data = await self._client.read_gatt_char(manufacturer_char)
                    self.manufacturer = data.decode("utf-8").strip()
                    _LOGGER.debug("Manufacturer: %s", self.manufacturer)
            except (BleakError, UnicodeDecodeError, AttributeError) as err:
                _LOGGER.debug("Could not read manufacturer name: %s", err)
            
            # Read model number
            try:
                model_char = device_info_service.get_characteristic(MODEL_NUMBER_UUID)
                if model_char:
                    data = await self._client.read_gatt_char(model_char)
                    self.model = data.decode("utf-8").strip()
                    _LOGGER.debug("Model: %s", self.model)
            except (BleakError, UnicodeDecodeError, AttributeError) as err:
                _LOGGER.debug("Could not read model number: %s", err)
                
        except Exception as err:
            _LOGGER.debug("Error reading device info: %s", err)
    
    async def _detect_device_type(self) -> None:
        """Detect the fitness equipment type from GATT characteristics.
        
        Raises:
            ValueError: If no supported device type is detected
        """
        if not self._client:
            raise ValueError("Client not connected")
            
        services = self._client.services
        if not services:
            raise ValueError("No services available")
            
        ftms_service = services.get_service(FTMS_SERVICE_UUID)
        if not ftms_service:
            raise ValueError(f"FTMS service {FTMS_SERVICE_UUID} not found")
        
        characteristics = ftms_service.characteristics
        for char in characteristics:
            if char.uuid == FTMS_TREADMILL_DATA_UUID:
                self._device_type = "treadmill"
                await self._subscribe_to_characteristic(FTMS_TREADMILL_DATA_UUID)
                return
            elif char.uuid == FTMS_INDOOR_BIKE_DATA_UUID:
                self._device_type = "bike"
                await self._subscribe_to_characteristic(FTMS_INDOOR_BIKE_DATA_UUID)
                return
            elif char.uuid == FTMS_ROWER_DATA_UUID:
                self._device_type = "rower"
                await self._subscribe_to_characteristic(FTMS_ROWER_DATA_UUID)
                return
        
        raise ValueError("No supported fitness equipment characteristics found")

    async def _subscribe_to_characteristic(self, uuid: str) -> None:
        """Subscribe to a characteristic for notifications.
        
        Args:
            uuid: The characteristic UUID to subscribe to
            
        Raises:
            BleakError: If subscription fails
        """
        if not self._client:
            raise ValueError("Client not connected")

        try:
            await self._client.start_notify(uuid, self._notification_handler)
            _LOGGER.debug(
                "Subscribed to characteristic %s for %s",
                uuid,
                self._device_type or "Unknown",
            )
        except (BleakError, AttributeError) as err:
            _LOGGER.error(
                "Failed to subscribe to characteristic %s: %s",
                uuid,
                err,
            )
            raise

    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle BLE notifications from fitness equipment.
        
        Args:
            sender: The characteristic handle that sent the notification
            data: The raw notification data
        """
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Received notification from handle %s (%d bytes): %s",
                sender,
                len(data),
                data.hex(),
            )
        
        if not data:
            _LOGGER.warning("Received empty notification from handle %s", sender)
            return
        
        try:
            # Parse the data based on device type
            parsed_data: dict[str, Any] = {}
            
            if self._device_type == "treadmill":
                treadmill_data = self._parser.parse_treadmill_data(bytes(data))
                parsed_data = self._treadmill_to_dict(treadmill_data)
            elif self._device_type == "bike":
                bike_data = self._parser.parse_indoor_bike_data(bytes(data))
                parsed_data = self._bike_to_dict(bike_data)
            elif self._device_type == "rower":
                rower_data = self._parser.parse_rower_data(bytes(data))
                parsed_data = self._rower_to_dict(rower_data)
            else:
                _LOGGER.warning("Unknown device type: %s", self._device_type)
                return
            
            # Update coordinator data
            self.async_set_updated_data(parsed_data)
            
        except Exception as err:
            _LOGGER.exception(
                "Failed to parse notification data from %s: %s",
                self._device_type or "Unknown",
                err,
            )

    def _treadmill_to_dict(self, data: TreadmillData) -> dict[str, Any]:
        """Convert treadmill data to dictionary.
        
        Args:
            data: Parsed treadmill data from FTMS
            
        Returns:
            Dictionary with sensor values
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
            "heart_rate": data.heart_rate,
            "power": data.power_output,
            "elapsed_time": data.elapsed_time,
            "remaining_time": data.remaining_time,
        }

    def _bike_to_dict(self, data: IndoorBikeData) -> dict[str, Any]:
        """Convert bike data to dictionary.
        
        Args:
            data: Parsed bike data from FTMS
            
        Returns:
            Dictionary with sensor values
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
            "heart_rate": data.heart_rate,
            "elapsed_time": data.elapsed_time,
            "remaining_time": data.remaining_time,
        }

    def _rower_to_dict(self, data: RowerData) -> dict[str, Any]:
        """Convert rower data to dictionary.
        
        Args:
            data: Parsed rower data from FTMS
            
        Returns:
            Dictionary with sensor values
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
            "heart_rate": data.heart_rate,
            "elapsed_time": data.elapsed_time,
            "remaining_time": data.remaining_time,
        }

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle disconnection from BLE device.
        
        Args:
            client: The BleakClient that disconnected
        """
        if self._expected_disconnected:
            _LOGGER.debug(
                "Expected disconnection from %s (%s)",
                self.ble_device.name or "Unknown",
                self.ble_device.address,
            )
            return
        
        _LOGGER.warning(
            "Unexpected disconnection from %s (%s)",
            self.ble_device.name or "Unknown", 
            self.ble_device.address,
        )
        # Try to reconnect
        self.hass.loop.create_task(self._handle_disconnect())

    async def _handle_disconnect(self) -> None:
        """Handle unexpected disconnection and attempt reconnection."""
        _LOGGER.info(
            "Attempting to reconnect to %s in %d seconds",
            self.ble_device.address,
            RECONNECT_DELAY,
        )
        await asyncio.sleep(RECONNECT_DELAY)
        
        try:
            await self._ensure_connected()
            _LOGGER.info("Successfully reconnected to %s", self.ble_device.address)
        except UpdateFailed as err:
            _LOGGER.error(
                "Failed to reconnect to %s: %s. Will retry on next update cycle.",
                self.ble_device.address,
                err,
            )
        except Exception as err:
            _LOGGER.exception(
                "Unexpected error during reconnection to %s: %s",
                self.ble_device.address,
                err,
            )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via polling (fallback if notifications don't work).
        
        Returns:
            Current sensor data dictionary
            
        Raises:
            UpdateFailed: If connection fails
        """
        try:
            # Ensure we're connected
            await self._ensure_connected()
        except UpdateFailed:
            # Re-raise UpdateFailed as-is
            raise
        except Exception as err:
            # Wrap unexpected errors
            raise UpdateFailed(f"Connection error: {err}") from err
        
        # Return current data (notifications should keep it updated)
        return self.data or {}

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and disconnect from device."""
        self._expected_disconnected = True
        
        if self._client and self._client.is_connected:
            _LOGGER.debug(
                "Disconnecting from %s (%s)",
                self.ble_device.name or "Unknown",
                self.ble_device.address,
            )
            try:
                await self._client.disconnect()
                _LOGGER.info("Successfully disconnected from %s", self.ble_device.address)
            except Exception as err:
                _LOGGER.warning(
                    "Error during disconnect from %s: %s",
                    self.ble_device.address,
                    err,
                )
