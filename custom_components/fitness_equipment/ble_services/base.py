"""Base class for BLE service handlers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from logging import Logger
from typing import Any

from bleak import BleakClient


class BLEServiceBase(ABC):
    """Base class for all BLE service handlers.
    
    Provides common functionality for BLE service management including:
    - Service availability detection
    - Subscription management
    - Notification handling
    - Data caching
    
    Subclasses must implement:
    - SERVICE_UUID: The Bluetooth service UUID
    - is_available(): Check if service exists on device
    - subscribe(): Subscribe to service notifications
    - handle_notification(): Parse notification data
    """

    SERVICE_UUID: str = ""  # Override in subclass

    def __init__(self, client: BleakClient, logger: Logger) -> None:
        """Initialize the BLE service handler.
        
        Args:
            client: The BleakClient connected to the device
            logger: Logger instance for this service
        """
        self._client = client
        self._logger = logger
        self._subscribed = False
        self._data: dict[str, Any] = {}

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this service is available on the device.
        
        Returns:
            True if the service exists and can be used
        """

    @abstractmethod
    async def subscribe(self) -> None:
        """Subscribe to service notifications.
        
        Should set self._subscribed = True on success.
        
        Raises:
            BleakError: If subscription fails
        """

    async def unsubscribe(self) -> None:
        """Unsubscribe from service notifications.
        
        Default implementation - subclasses can override.
        """
        if not self._subscribed:
            return

        self._subscribed = False
        self._logger.debug("Unsubscribed from %s", self.__class__.__name__)

    @abstractmethod
    def handle_notification(self, sender: int, data: bytes) -> None:
        """Handle a notification from the service.
        
        Args:
            sender: The characteristic handle that sent the notification
            data: The raw notification data
            
        Should update self._data with parsed values.
        """

    def get_data(self) -> dict[str, Any]:
        """Get the current data from this service.
        
        Returns:
            Dictionary of current sensor values
        """
        return self._data.copy()

    def clear_data(self) -> None:
        """Clear the cached data."""
        self._data.clear()

    @property
    def is_subscribed(self) -> bool:
        """Check if currently subscribed to notifications.
        
        Returns:
            True if subscribed
        """
        return self._subscribed
