"""Heart Rate Service (HRS) handler for BLE fitness devices.

Implements the Bluetooth Heart Rate Service (0x180D) specification.
Provides more accurate and frequent heart rate updates compared to FTMS embedded data.

Specification: https://www.bluetooth.com/specifications/specs/heart-rate-service-1-0/
"""
from __future__ import annotations

import struct
from logging import Logger
from typing import Any

from bleak import BleakClient, BleakError

from .base import BLEServiceBase


class HeartRateService(BLEServiceBase):
    """Heart Rate Service (HRS) handler.
    
    Parses heart rate measurements including:
    - Heart rate (BPM)
    - Sensor contact status
    - Energy expended (cumulative kJ)
    - RR-intervals (heart rate variability)
    """

    SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
    MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

    def __init__(self, client: BleakClient, logger: Logger) -> None:
        """Initialize the Heart Rate Service handler.
        
        Args:
            client: The BleakClient connected to the device
            logger: Logger instance for this service
        """
        super().__init__(client, logger)
        self._characteristic_handle: int | None = None

    async def is_available(self) -> bool:
        """Check if Heart Rate Service is available on the device.
        
        Returns:
            True if HRS service and measurement characteristic exist
        """
        try:
            services = self._client.services
            if not services:
                return False

            hrs_service = services.get_service(self.SERVICE_UUID)
            if not hrs_service:
                self._logger.debug("Heart Rate Service not found")
                return False

            # Check for measurement characteristic
            measurement_char = hrs_service.get_characteristic(self.MEASUREMENT_UUID)
            if not measurement_char:
                self._logger.debug("Heart Rate Measurement characteristic not found")
                return False

            self._logger.info("Heart Rate Service is available")
            return True

        except (BleakError, AttributeError) as err:
            self._logger.debug("Error checking Heart Rate Service availability: %s", err)
            return False

    async def subscribe(self) -> None:
        """Subscribe to heart rate measurements.
        
        Raises:
            BleakError: If subscription fails
        """
        if self._subscribed:
            return

        try:
            await self._client.start_notify(
                self.MEASUREMENT_UUID,
                self._handle_measurement
            )
            self._subscribed = True
            self._logger.info("Subscribed to Heart Rate Service")

        except (BleakError, AttributeError) as err:
            self._logger.error("Failed to subscribe to Heart Rate Service: %s", err)
            raise

    async def unsubscribe(self) -> None:
        """Unsubscribe from heart rate measurements."""
        if not self._subscribed:
            return

        try:
            await self._client.stop_notify(self.MEASUREMENT_UUID)
            self._subscribed = False
            self._logger.debug("Unsubscribed from Heart Rate Service")
        except (BleakError, AttributeError) as err:
            self._logger.debug("Error unsubscribing from Heart Rate Service: %s", err)

    def handle_notification(self, sender: int, data: bytes) -> None:
        """Handle heart rate measurement notification.
        
        Args:
            sender: The characteristic handle that sent the notification
            data: The raw heart rate measurement data
        """
        self._handle_measurement(sender, data)

    def _handle_measurement(self, sender: int, data: bytes) -> None:
        """Parse and handle heart rate measurement.
        
        Args:
            sender: The characteristic handle
            data: Raw measurement data
        """
        try:
            parsed = self._parse_measurement(data)
            self._data.update(parsed)

            self._logger.debug(
                "Heart Rate: %s BPM, Contact: %s",
                parsed.get("heart_rate"),
                parsed.get("sensor_contact"),
            )

        except Exception as err:
            self._logger.warning("Failed to parse heart rate measurement: %s", err)

    def _parse_measurement(self, data: bytes) -> dict[str, Any]:
        """Parse Heart Rate Measurement characteristic data.
        
        Format per Bluetooth HRS specification:
        - Byte 0: Flags
          - Bit 0: Heart Rate Value Format (0=uint8, 1=uint16)
          - Bit 1-2: Sensor Contact Status (0/1=not supported, 2=no contact, 3=contact)
          - Bit 3: Energy Expended present
          - Bit 4: RR-Interval present
        - Byte 1-2: Heart Rate Value (uint8 or uint16)
        - Byte 3-4: Energy Expended (uint16, optional, in kJ)
        - Byte 5+: RR-Intervals (uint16[], optional, in 1/1024 seconds)
        
        Args:
            data: Raw measurement bytes
            
        Returns:
            Dictionary with parsed values:
            - heart_rate: int (BPM)
            - sensor_contact: bool (True if sensor is in contact)
            - energy_expended: int (kJ, optional)
            - rr_intervals: list[int] (ms, optional)
        """
        if not data or len(data) < 2:
            raise ValueError(f"Invalid heart rate data length: {len(data)}")

        result: dict[str, Any] = {}
        offset = 0

        # Parse flags
        flags = data[offset]
        offset += 1

        # Heart Rate Value (uint8 or uint16)
        if flags & 0x01:  # uint16 format
            if offset + 2 > len(data):
                raise ValueError("Insufficient data for uint16 heart rate")
            result["heart_rate"] = struct.unpack_from("<H", data, offset)[0]
            offset += 2
        else:  # uint8 format
            result["heart_rate"] = data[offset]
            offset += 1

        # Sensor Contact Status (bits 1-2)
        sensor_contact_bits = (flags >> 1) & 0x03
        if sensor_contact_bits == 0x02:
            result["sensor_contact"] = False  # No contact detected
        elif sensor_contact_bits == 0x03:
            result["sensor_contact"] = True  # Contact detected
        # If 0x00 or 0x01, sensor contact not supported - don't set the key

        # Energy Expended (optional, cumulative kJ)
        if flags & 0x08:  # Energy Expended present
            if offset + 2 <= len(data):
                result["energy_expended"] = struct.unpack_from("<H", data, offset)[0]
                offset += 2

        # RR-Intervals (optional, for HRV analysis)
        if flags & 0x10:  # RR-Interval present
            rr_intervals = []
            while offset + 2 <= len(data):
                # RR-Interval in 1/1024 second units
                rr_value = struct.unpack_from("<H", data, offset)[0]
                # Convert to milliseconds
                rr_ms = int((rr_value / 1024.0) * 1000)
                rr_intervals.append(rr_ms)
                offset += 2

            if rr_intervals:
                result["rr_intervals"] = rr_intervals

        return result
