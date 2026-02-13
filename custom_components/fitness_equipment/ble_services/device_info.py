"""Device Information Service (DIS) handler for BLE fitness devices.

Reads static device information like manufacturer, model, and serial number.
This is typically read once during device setup.

Specification: https://www.bluetooth.com/specifications/specs/device-information-service-1-1/
"""
from __future__ import annotations

from logging import Logger
from typing import Any

from bleak import BleakClient, BleakError

from .base import BLEServiceBase


class DeviceInfoService(BLEServiceBase):
    """Device Information Service (DIS) handler.
    
    Reads device metadata:
    - Manufacturer name
    - Model number
    - Serial number
    - Hardware revision
    - Firmware revision
    - Software revision
    """

    SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
    MANUFACTURER_NAME_UUID = "00002a29-0000-1000-8000-00805f9b34fb"
    MODEL_NUMBER_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
    SERIAL_NUMBER_UUID = "00002a25-0000-1000-8000-00805f9b34fb"
    HARDWARE_REVISION_UUID = "00002a27-0000-1000-8000-00805f9b34fb"
    FIRMWARE_REVISION_UUID = "00002a26-0000-1000-8000-00805f9b34fb"
    SOFTWARE_REVISION_UUID = "00002a28-0000-1000-8000-00805f9b34fb"

    def __init__(self, client: BleakClient, logger: Logger) -> None:
        """Initialize the Device Information Service handler.
        
        Args:
            client: The BleakClient connected to the device
            logger: Logger instance for this service
        """
        super().__init__(client, logger)

    async def is_available(self) -> bool:
        """Check if Device Information Service is available.
        
        Returns:
            True if DIS service exists
        """
        try:
            services = self._client.services
            if not services:
                return False

            dis_service = services.get_service(self.SERVICE_UUID)
            if not dis_service:
                self._logger.debug("Device Information Service not found")
                return False

            self._logger.debug("Device Information Service is available")
            return True

        except (BleakError, AttributeError) as err:
            self._logger.debug("Error checking Device Information Service: %s", err)
            return False

    async def subscribe(self) -> None:
        """Subscribe to service (not applicable for DIS).
        
        Device Information Service doesn't use notifications.
        Call read_static_data() instead.
        """
        # DIS doesn't support notifications - it's read-only
        self._subscribed = False

    async def read_static_data(self) -> dict[str, Any]:
        """Read all available device information.
        
        Returns:
            Dictionary with device information:
            - manufacturer: str
            - model: str
            - serial_number: str
            - hardware_revision: str
            - firmware_revision: str
            - software_revision: str
        """
        device_info: dict[str, Any] = {}

        try:
            services = self._client.services
            if not services:
                return device_info

            dis_service = services.get_service(self.SERVICE_UUID)
            if not dis_service:
                return device_info

            # Try to read each characteristic
            device_info["manufacturer"] = await self._read_string_characteristic(
                dis_service, self.MANUFACTURER_NAME_UUID, "Manufacturer"
            )

            device_info["model"] = await self._read_string_characteristic(
                dis_service, self.MODEL_NUMBER_UUID, "Model"
            )

            device_info["serial_number"] = await self._read_string_characteristic(
                dis_service, self.SERIAL_NUMBER_UUID, "Serial Number"
            )

            device_info["hardware_revision"] = await self._read_string_characteristic(
                dis_service, self.HARDWARE_REVISION_UUID, "Hardware Revision"
            )

            device_info["firmware_revision"] = await self._read_string_characteristic(
                dis_service, self.FIRMWARE_REVISION_UUID, "Firmware Revision"
            )

            device_info["software_revision"] = await self._read_string_characteristic(
                dis_service, self.SOFTWARE_REVISION_UUID, "Software Revision"
            )

            # Cache the data
            self._data = {k: v for k, v in device_info.items() if v is not None}

            # Log what we found
            if self._data:
                self._logger.info(
                    "Device Info: %s %s",
                    self._data.get("manufacturer", "Unknown"),
                    self._data.get("model", "Unknown"),
                )

        except Exception as err:
            self._logger.debug("Error reading device information: %s", err)

        return device_info

    async def _read_string_characteristic(
        self,
        service: Any,
        char_uuid: str,
        char_name: str,
    ) -> str | None:
        """Read a string characteristic from the service.
        
        Args:
            service: The BLE service object
            char_uuid: The characteristic UUID to read
            char_name: Human-readable name for logging
            
        Returns:
            The string value, or None if not available
        """
        try:
            characteristic = service.get_characteristic(char_uuid)
            if not characteristic:
                return None

            data = await self._client.read_gatt_char(characteristic)
            value = data.decode("utf-8").strip()

            if value:
                self._logger.debug("%s: %s", char_name, value)
                return value

        except (BleakError, UnicodeDecodeError, AttributeError) as err:
            self._logger.debug("Could not read %s: %s", char_name, err)

        return None

    def handle_notification(self, sender: int, data: bytes) -> None:
        """Handle notification (not used for DIS).
        
        Args:
            sender: The characteristic handle
            data: The raw data
        """
        # DIS doesn't send notifications
        pass
