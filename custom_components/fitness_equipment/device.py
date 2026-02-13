"""Device helpers for Fitness Equipment integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


def get_device_info(
    entry: ConfigEntry,
    device_type: str | None = None,
    manufacturer: str | None = None,
    model: str | None = None,
) -> DeviceInfo:
    """Get device info for a fitness equipment device.
    
    Args:
        entry: The config entry
        device_type: The type of fitness device (treadmill, bike, rower)
        manufacturer: The manufacturer name from Device Information Service
        model: The model number from Device Information Service
        
    Returns:
        DeviceInfo object for the device
    """
    # Use device type for model if no model number available
    device_model = model or (device_type.title() if device_type else "Fitness Equipment")
    
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=manufacturer or "Unknown",
        model=device_model,
    )


def format_device_name(name: str | None, address: str) -> str:
    """Format a device name for display.
    
    Args:
        name: The device name from Bluetooth
        address: The device MAC address
        
    Returns:
        Formatted device name
    """
    if name:
        return f"{name} ({address})"
    return address


def is_ftms_device(service_uuids: list[str], ftms_uuid: str) -> bool:
    """Check if a device is an FTMS device.
    
    Args:
        service_uuids: List of service UUIDs from the device
        ftms_uuid: The FTMS service UUID to check for
        
    Returns:
        True if device has FTMS service
    """
    return ftms_uuid.lower() in [uuid.lower() for uuid in service_uuids]
