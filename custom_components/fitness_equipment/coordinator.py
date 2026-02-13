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

from .ble_services import DeviceInfoService, FTMSService, HeartRateService
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Connection constants
RECONNECT_DELAY: Final = 5  # seconds
MAX_RECONNECT_ATTEMPTS: Final = 3
CONNECTION_TIMEOUT: Final = 30  # seconds


class FitnessEquipmentCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Fitness Equipment device.
    
    Orchestrates multiple BLE services (FTMS, Heart Rate, Device Info)
    and merges data from all available services.
    """

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
        self._expected_disconnected = False
        
        # BLE service handlers
        self._ftms_service: FTMSService | None = None
        self._hr_service: HeartRateService | None = None
        self._device_info_service: DeviceInfoService | None = None
        
        # Device metadata (from Device Info Service)
        self.manufacturer: str | None = None
        self.model: str | None = None
        self.serial_number: str | None = None
        self.hardware_revision: str | None = None
        self.firmware_revision: str | None = None
        self.software_revision: str | None = None

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        # Connect and discover available services
        await self._ensure_connected()

    async def _ensure_connected(self) -> None:
        """Ensure we have a connection to the device and services initialized.
        
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

        # Discover and initialize available BLE services
        try:
            await self._discover_services()
        except Exception as err:
            _LOGGER.error("Failed to discover services: %s", err)
            raise UpdateFailed(f"Failed to discover services: {err}") from err

        _LOGGER.info(
            "Connected to %s (%s) - FTMS: %s, HR: %s, Manufacturer: %s",
            self.ble_device.name or "Unknown",
            self.ble_device.address,
            "Yes" if self._ftms_service else "No",
            "Yes" if self._hr_service else "No",
            self.manufacturer or "Unknown",
        )
    
    async def _discover_services(self) -> None:
        """Discover and initialize available BLE services.
        
        Initializes service handlers for:
        - Device Information Service (DIS) - one-time read
        - FTMS Service - required, subscribes to notifications
        - Heart Rate Service (HRS) - optional, subscribes if available
        
        Raises:
            ValueError: If FTMS service is not available (required)
        """
        if not self._client:
            raise ValueError("Client not connected")
        
        # Initialize Device Information Service (one-time read)
        self._device_info_service = DeviceInfoService(self._client, _LOGGER)
        if await self._device_info_service.is_available():
            device_info = await self._device_info_service.read_static_data()
            self.manufacturer = device_info.get("manufacturer")
            self.model = device_info.get("model")
            self.serial_number = device_info.get("serial_number")
            self.hardware_revision = device_info.get("hardware_revision")
            self.firmware_revision = device_info.get("firmware_revision")
            self.software_revision = device_info.get("software_revision")
            _LOGGER.debug(
                "Device info: %s %s (Serial: %s, FW: %s)",
                self.manufacturer or "Unknown",
                self.model or "Unknown",
                self.serial_number or "N/A",
                self.firmware_revision or "N/A",
            )
        else:
            _LOGGER.debug("Device Information Service not available")
        
        # Initialize FTMS Service (required)
        self._ftms_service = FTMSService(self._client, _LOGGER)
        if not await self._ftms_service.is_available():
            raise ValueError("FTMS service not found - this is not a fitness equipment device")
        
        await self._ftms_service.subscribe()
        _LOGGER.info(
            "FTMS service initialized - Device type: %s",
            self._ftms_service.device_type or "Unknown",
        )
        
        # Initialize Heart Rate Service (optional)
        self._hr_service = HeartRateService(self._client, _LOGGER)
        if await self._hr_service.is_available():
            await self._hr_service.subscribe()
            _LOGGER.info("Heart Rate Service initialized and subscribed")
        else:
            _LOGGER.debug("Heart Rate Service not available")
    
    def _merge_service_data(self) -> dict[str, Any]:
        """Merge data from all available services.
        
        Returns:
            Merged dictionary from all service handlers
        """
        merged_data: dict[str, Any] = {}
        
        # Add FTMS data (base fitness data)
        if self._ftms_service:
            ftms_data = self._ftms_service.get_data()
            merged_data.update(ftms_data)
        
        # Add Heart Rate Service data (if available)
        if self._hr_service:
            hr_data = self._hr_service.get_data()
            merged_data.update(hr_data)
        
        return merged_data



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
        """Update data by merging from all service handlers.
        
        Services receive BLE notifications and cache data internally.
        This method merges data from all services and returns it.
        
        Returns:
            Merged sensor data dictionary from all services
            
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
        
        # Merge and return data from all services
        return self._merge_service_data()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and disconnect from device."""
        self._expected_disconnected = True
        
        # Unsubscribe from all services
        if self._ftms_service:
            try:
                await self._ftms_service.unsubscribe()
            except Exception as err:
                _LOGGER.debug("Error unsubscribing from FTMS service: %s", err)
        
        if self._hr_service:
            try:
                await self._hr_service.unsubscribe()
            except Exception as err:
                _LOGGER.debug("Error unsubscribing from HR service: %s", err)
        
        # Disconnect from device
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
