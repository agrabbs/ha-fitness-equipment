"""BLE Services package for Fitness Equipment integration.

This package provides modular handlers for various Bluetooth Low Energy services:
- FTMS (Fitness Machine Service) - Primary workout data
- Heart Rate Service - Heart rate monitoring
- Device Information Service - Manufacturer, model, etc.

Future services to be added:
- Battery Service
- Cycling Power Service
- Cycling Speed and Cadence Service
- Running Speed and Cadence Service
"""
from __future__ import annotations

from .base import BLEServiceBase
from .device_info import DeviceInfoService
from .ftms import FTMSService
from .heart_rate import HeartRateService

__all__ = [
    "BLEServiceBase",
    "DeviceInfoService",
    "FTMSService",
    "HeartRateService",
]
