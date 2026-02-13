"""FTMS (Fitness Machine Service) data parser.

Parses binary BLE characteristic data according to the Bluetooth FTMS specification.
Specification: https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any

from .const import (
    BIKE_FLAG_AVG_CADENCE,
    BIKE_FLAG_AVG_POWER,
    BIKE_FLAG_AVG_SPEED,
    BIKE_FLAG_ELAPSED_TIME,
    BIKE_FLAG_EXPENDED_ENERGY,
    BIKE_FLAG_HEART_RATE,
    BIKE_FLAG_INSTANT_CADENCE,
    BIKE_FLAG_INSTANT_POWER,
    BIKE_FLAG_METABOLIC_EQUIVALENT,
    BIKE_FLAG_MORE_DATA,
    BIKE_FLAG_REMAINING_TIME,
    BIKE_FLAG_RESISTANCE_LEVEL,
    BIKE_FLAG_TOTAL_DISTANCE,
    ROWER_FLAG_AVG_PACE,
    ROWER_FLAG_AVG_POWER,
    ROWER_FLAG_AVG_STROKE,
    ROWER_FLAG_ELAPSED_TIME,
    ROWER_FLAG_EXPENDED_ENERGY,
    ROWER_FLAG_HEART_RATE,
    ROWER_FLAG_INSTANT_PACE,
    ROWER_FLAG_INSTANT_POWER,
    ROWER_FLAG_METABOLIC_EQUIVALENT,
    ROWER_FLAG_MORE_DATA,
    ROWER_FLAG_REMAINING_TIME,
    ROWER_FLAG_RESISTANCE_LEVEL,
    ROWER_FLAG_TOTAL_DISTANCE,
    TREADMILL_FLAG_AVG_PACE,
    TREADMILL_FLAG_AVG_SPEED,
    TREADMILL_FLAG_ELAPSED_TIME,
    TREADMILL_FLAG_ELEVATION_GAIN,
    TREADMILL_FLAG_EXPENDED_ENERGY,
    TREADMILL_FLAG_FORCE_ON_BELT,
    TREADMILL_FLAG_HEART_RATE,
    TREADMILL_FLAG_INCLINATION,
    TREADMILL_FLAG_INSTANT_PACE,
    TREADMILL_FLAG_METABOLIC_EQUIVALENT,
    TREADMILL_FLAG_MORE_DATA,
    TREADMILL_FLAG_POWER_OUTPUT,
    TREADMILL_FLAG_REMAINING_TIME,
    TREADMILL_FLAG_TOTAL_DISTANCE,
)


@dataclass
class TreadmillData:
    """Parsed treadmill data."""

    instant_speed: float | None = None  # km/h
    average_speed: float | None = None  # km/h
    total_distance: int | None = None  # meters
    inclination: float | None = None  # percent
    ramp_angle: float | None = None  # degrees
    elevation_gain: int | None = None  # meters
    instant_pace: float | None = None  # min/km
    average_pace: float | None = None  # min/km
    total_energy: int | None = None  # kcal
    energy_per_hour: int | None = None  # kcal/h
    energy_per_minute: int | None = None  # kcal/min
    heart_rate: int | None = None  # bpm
    metabolic_equivalent: float | None = None  # MET
    elapsed_time: int | None = None  # seconds
    remaining_time: int | None = None  # seconds
    force_on_belt: int | None = None  # newtons
    power_output: int | None = None  # watts


@dataclass
class IndoorBikeData:
    """Parsed indoor bike data."""

    instant_speed: float | None = None  # km/h
    average_speed: float | None = None  # km/h
    instant_cadence: float | None = None  # rpm
    average_cadence: float | None = None  # rpm
    total_distance: int | None = None  # meters
    resistance_level: int | None = None
    instant_power: int | None = None  # watts
    average_power: int | None = None  # watts
    total_energy: int | None = None  # kcal
    energy_per_hour: int | None = None  # kcal/h
    energy_per_minute: int | None = None  # kcal/min
    heart_rate: int | None = None  # bpm
    metabolic_equivalent: float | None = None  # MET
    elapsed_time: int | None = None  # seconds
    remaining_time: int | None = None  # seconds


@dataclass
class RowerData:
    """Parsed rower data."""

    stroke_rate: float | None = None  # strokes/min
    stroke_count: int | None = None
    average_stroke_rate: float | None = None  # strokes/min
    total_distance: int | None = None  # meters
    instant_pace: float | None = None  # seconds/500m
    average_pace: float | None = None  # seconds/500m
    instant_power: int | None = None  # watts
    average_power: int | None = None  # watts
    resistance_level: int | None = None
    total_energy: int | None = None  # kcal
    energy_per_hour: int | None = None  # kcal/h
    energy_per_minute: int | None = None  # kcal/min
    heart_rate: int | None = None  # bpm
    metabolic_equivalent: float | None = None  # MET
    elapsed_time: int | None = None  # seconds
    remaining_time: int | None = None  # seconds


class FTMSParser:
    """Parser for FTMS characteristic data."""

    @staticmethod
    def parse_treadmill_data(data: bytes) -> TreadmillData:
        """Parse treadmill data characteristic.
        
        Args:
            data: Raw bytes from FTMS Treadmill Data characteristic
            
        Returns:
            Parsed treadmill data
        """
        if len(data) < 3:
            return TreadmillData()

        result = TreadmillData()
        offset = 0

        # Parse flags (2 bytes, little endian)
        flags = struct.unpack_from("<H", data, offset)[0]
        offset += 2

        # Instant Speed (uint16, resolution 0.01 km/h) - ALWAYS present
        if offset + 2 <= len(data):
            speed_raw = struct.unpack_from("<H", data, offset)[0]
            result.instant_speed = speed_raw * 0.01
            offset += 2

        # Average Speed (uint16, resolution 0.01 km/h)
        if flags & TREADMILL_FLAG_AVG_SPEED and offset + 2 <= len(data):
            avg_speed_raw = struct.unpack_from("<H", data, offset)[0]
            result.average_speed = avg_speed_raw * 0.01
            offset += 2

        # Total Distance (uint24, meters)
        if flags & TREADMILL_FLAG_TOTAL_DISTANCE and offset + 3 <= len(data):
            distance_bytes = data[offset : offset + 3] + b"\x00"
            result.total_distance = struct.unpack("<I", distance_bytes)[0]
            offset += 3

        # Inclination and Ramp Angle (sint16, resolution 0.1%)
        if flags & TREADMILL_FLAG_INCLINATION and offset + 4 <= len(data):
            inclination_raw = struct.unpack_from("<h", data, offset)[0]
            result.inclination = inclination_raw * 0.1
            offset += 2
            ramp_raw = struct.unpack_from("<h", data, offset)[0]
            result.ramp_angle = ramp_raw * 0.1
            offset += 2

        # Positive Elevation Gain (uint16, meters)
        if flags & TREADMILL_FLAG_ELEVATION_GAIN and offset + 2 <= len(data):
            result.elevation_gain = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        # Instantaneous Pace (uint8, resolution 1 min/km)
        if flags & TREADMILL_FLAG_INSTANT_PACE and offset + 1 <= len(data):
            result.instant_pace = struct.unpack_from("<B", data, offset)[0]
            offset += 1

        # Average Pace (uint8, resolution 1 min/km)
        if flags & TREADMILL_FLAG_AVG_PACE and offset + 1 <= len(data):
            result.average_pace = struct.unpack_from("<B", data, offset)[0]
            offset += 1

        # Expended Energy (3x uint16: total, per hour, per minute in kcal)
        if flags & TREADMILL_FLAG_EXPENDED_ENERGY and offset + 6 <= len(data):
            result.total_energy = struct.unpack_from("<H", data, offset)[0]
            result.energy_per_hour = struct.unpack_from("<H", data, offset + 2)[0]
            result.energy_per_minute = struct.unpack_from("<B", data, offset + 4)[0]
            offset += 5

        # Heart Rate (uint8, bpm)
        if flags & TREADMILL_FLAG_HEART_RATE and offset + 1 <= len(data):
            result.heart_rate = struct.unpack_from("<B", data, offset)[0]
            offset += 1

        # Metabolic Equivalent (uint8, resolution 0.1)
        if flags & TREADMILL_FLAG_METABOLIC_EQUIVALENT and offset + 1 <= len(data):
            met_raw = struct.unpack_from("<B", data, offset)[0]
            result.metabolic_equivalent = met_raw * 0.1
            offset += 1

        # Elapsed Time (uint16, seconds)
        if flags & TREADMILL_FLAG_ELAPSED_TIME and offset + 2 <= len(data):
            result.elapsed_time = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        # Remaining Time (uint16, seconds)
        if flags & TREADMILL_FLAG_REMAINING_TIME and offset + 2 <= len(data):
            result.remaining_time = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        # Force on Belt (uint16, newtons)
        if flags & TREADMILL_FLAG_FORCE_ON_BELT and offset + 2 <= len(data):
            result.force_on_belt = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        # Power Output (sint16, watts)
        if flags & TREADMILL_FLAG_POWER_OUTPUT and offset + 2 <= len(data):
            result.power_output = struct.unpack_from("<h", data, offset)[0]
            offset += 2

        return result

    @staticmethod
    def parse_indoor_bike_data(data: bytes) -> IndoorBikeData:
        """Parse indoor bike data characteristic.
        
        Args:
            data: Raw bytes from FTMS Indoor Bike Data characteristic
            
        Returns:
            Parsed indoor bike data
        """
        if len(data) < 3:
            return IndoorBikeData()

        result = IndoorBikeData()
        offset = 0

        # Parse flags (2 bytes, little endian)
        flags = struct.unpack_from("<H", data, offset)[0]
        offset += 2

        # Instant Speed (uint16, resolution 0.01 km/h) - ALWAYS present
        if offset + 2 <= len(data):
            speed_raw = struct.unpack_from("<H", data, offset)[0]
            result.instant_speed = speed_raw * 0.01
            offset += 2

        # Average Speed (uint16, resolution 0.01 km/h)
        if flags & BIKE_FLAG_AVG_SPEED and offset + 2 <= len(data):
            avg_speed_raw = struct.unpack_from("<H", data, offset)[0]
            result.average_speed = avg_speed_raw * 0.01
            offset += 2

        # Instantaneous Cadence (uint16, resolution 0.5 rpm)
        if flags & BIKE_FLAG_INSTANT_CADENCE and offset + 2 <= len(data):
            cadence_raw = struct.unpack_from("<H", data, offset)[0]
            result.instant_cadence = cadence_raw * 0.5
            offset += 2

        # Average Cadence (uint16, resolution 0.5 rpm)
        if flags & BIKE_FLAG_AVG_CADENCE and offset + 2 <= len(data):
            avg_cadence_raw = struct.unpack_from("<H", data, offset)[0]
            result.average_cadence = avg_cadence_raw * 0.5
            offset += 2

        # Total Distance (uint24, meters)
        if flags & BIKE_FLAG_TOTAL_DISTANCE and offset + 3 <= len(data):
            distance_bytes = data[offset : offset + 3] + b"\x00"
            result.total_distance = struct.unpack("<I", distance_bytes)[0]
            offset += 3

        # Resistance Level (sint16)
        if flags & BIKE_FLAG_RESISTANCE_LEVEL and offset + 2 <= len(data):
            result.resistance_level = struct.unpack_from("<h", data, offset)[0]
            offset += 2

        # Instantaneous Power (sint16, watts)
        if flags & BIKE_FLAG_INSTANT_POWER and offset + 2 <= len(data):
            result.instant_power = struct.unpack_from("<h", data, offset)[0]
            offset += 2

        # Average Power (sint16, watts)
        if flags & BIKE_FLAG_AVG_POWER and offset + 2 <= len(data):
            result.average_power = struct.unpack_from("<h", data, offset)[0]
            offset += 2

        # Expended Energy
        if flags & BIKE_FLAG_EXPENDED_ENERGY and offset + 6 <= len(data):
            result.total_energy = struct.unpack_from("<H", data, offset)[0]
            result.energy_per_hour = struct.unpack_from("<H", data, offset + 2)[0]
            result.energy_per_minute = struct.unpack_from("<B", data, offset + 4)[0]
            offset += 5

        # Heart Rate (uint8, bpm)
        if flags & BIKE_FLAG_HEART_RATE and offset + 1 <= len(data):
            result.heart_rate = struct.unpack_from("<B", data, offset)[0]
            offset += 1

        # Metabolic Equivalent (uint8, resolution 0.1)
        if flags & BIKE_FLAG_METABOLIC_EQUIVALENT and offset + 1 <= len(data):
            met_raw = struct.unpack_from("<B", data, offset)[0]
            result.metabolic_equivalent = met_raw * 0.1
            offset += 1

        # Elapsed Time (uint16, seconds)
        if flags & BIKE_FLAG_ELAPSED_TIME and offset + 2 <= len(data):
            result.elapsed_time = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        # Remaining Time (uint16, seconds)
        if flags & BIKE_FLAG_REMAINING_TIME and offset + 2 <= len(data):
            result.remaining_time = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        return result

    @staticmethod
    def parse_rower_data(data: bytes) -> RowerData:
        """Parse rower data characteristic.
        
        Args:
            data: Raw bytes from FTMS Rower Data characteristic
            
        Returns:
            Parsed rower data
        """
        if len(data) < 3:
            return RowerData()

        result = RowerData()
        offset = 0

        # Parse flags (2 bytes, little endian)
        flags = struct.unpack_from("<H", data, offset)[0]
        offset += 2

        # Stroke Rate (uint8, resolution 0.5 strokes/min) - ALWAYS present
        # Stroke Count (uint16) - ALWAYS present
        if offset + 3 <= len(data):
            stroke_rate_raw = struct.unpack_from("<B", data, offset)[0]
            result.stroke_rate = stroke_rate_raw * 0.5
            result.stroke_count = struct.unpack_from("<H", data, offset + 1)[0]
            offset += 3

        # Average Stroke Rate (uint8, resolution 0.5 strokes/min)
        if flags & ROWER_FLAG_AVG_STROKE and offset + 1 <= len(data):
            avg_stroke_raw = struct.unpack_from("<B", data, offset)[0]
            result.average_stroke_rate = avg_stroke_raw * 0.5
            offset += 1

        # Total Distance (uint24, meters)
        if flags & ROWER_FLAG_TOTAL_DISTANCE and offset + 3 <= len(data):
            distance_bytes = data[offset : offset + 3] + b"\x00"
            result.total_distance = struct.unpack("<I", distance_bytes)[0]
            offset += 3

        # Instantaneous Pace (uint16, seconds per 500m)
        if flags & ROWER_FLAG_INSTANT_PACE and offset + 2 <= len(data):
            result.instant_pace = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        # Average Pace (uint16, seconds per 500m)
        if flags & ROWER_FLAG_AVG_PACE and offset + 2 <= len(data):
            result.average_pace = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        # Instantaneous Power (sint16, watts)
        if flags & ROWER_FLAG_INSTANT_POWER and offset + 2 <= len(data):
            result.instant_power = struct.unpack_from("<h", data, offset)[0]
            offset += 2

        # Average Power (sint16, watts)
        if flags & ROWER_FLAG_AVG_POWER and offset + 2 <= len(data):
            result.average_power = struct.unpack_from("<h", data, offset)[0]
            offset += 2

        # Resistance Level (sint16)
        if flags & ROWER_FLAG_RESISTANCE_LEVEL and offset + 2 <= len(data):
            result.resistance_level = struct.unpack_from("<h", data, offset)[0]
            offset += 2

        # Expended Energy
        if flags & ROWER_FLAG_EXPENDED_ENERGY and offset + 6 <= len(data):
            result.total_energy = struct.unpack_from("<H", data, offset)[0]
            result.energy_per_hour = struct.unpack_from("<H", data, offset + 2)[0]
            result.energy_per_minute = struct.unpack_from("<B", data, offset + 4)[0]
            offset += 5

        # Heart Rate (uint8, bpm)
        if flags & ROWER_FLAG_HEART_RATE and offset + 1 <= len(data):
            result.heart_rate = struct.unpack_from("<B", data, offset)[0]
            offset += 1

        # Metabolic Equivalent (uint8, resolution 0.1)
        if flags & ROWER_FLAG_METABOLIC_EQUIVALENT and offset + 1 <= len(data):
            met_raw = struct.unpack_from("<B", data, offset)[0]
            result.metabolic_equivalent = met_raw * 0.1
            offset += 1

        # Elapsed Time (uint16, seconds)
        if flags & ROWER_FLAG_ELAPSED_TIME and offset + 2 <= len(data):
            result.elapsed_time = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        # Remaining Time (uint16, seconds)
        if flags & ROWER_FLAG_REMAINING_TIME and offset + 2 <= len(data):
            result.remaining_time = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        return result
