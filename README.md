# Fitness Equipment Integration for Home Assistant

A custom Home Assistant integration that connects to Bluetooth Low Energy (BLE) fitness devices using the FTMS (Fitness Machine Service) protocol. Monitor workout data from treadmills, indoor bikes, rowing machines, and other fitness equipment in real-time.

## Features

- **Auto-discovery**: Automatically detects FTMS-compatible fitness devices
- **Real-time data**: Live updates via BLE notifications
- **Multiple device types**: Supports treadmills, indoor bikes, rowers, and more
- **Rich sensors**: Speed, distance, calories, heart rate, power, cadence, and more
- **Device information**: Reads manufacturer and model from Device Information Service
- **Automation ready**: Use workout data to control your smart home
- **Reliable connectivity**: Automatic reconnection with retry logic

## Supported Devices

Any fitness device that implements the Bluetooth FTMS (Fitness Machine Service) standard:
- Treadmills (e.g., Wahoo KICKR Run)
- Indoor bikes / Spin bikes
- Rowing machines
- Elliptical trainers
- Cross trainers

## Installation

### HACS (Recommended)

_Coming soon - integration not yet submitted to HACS_

### Manual Installation

1. Copy the `custom_components/fitness_equipment` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant
3. Go to Settings > Devices & Services
4. Click "+ Add Integration"
5. Search for "Fitness Equipment"
6. Select your device from the list

Alternatively, use the installation script:

```bash
# Download and run the installation script
wget https://raw.githubusercontent.com/yourusername/ha-fitness-equipment/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

### Requirements

- Home Assistant 2024.1 or newer (requires Python 3.12+)
- Bluetooth adapter (built-in or USB)
- FTMS-compatible fitness device

## Sensors

The integration creates sensors based on the device type and available data:

### Common Sensors (all devices)
- **Speed** (km/h) - Instantaneous speed
- **Average Speed** (km/h) - Session average speed
- **Distance** (meters) - Total distance covered
- **Calories** (kcal) - Energy expenditure
- **Heart Rate** (bpm) - Current heart rate (if device provides it)
- **Power** (watts) - Instantaneous power output (if available)
- **Elapsed Time** (seconds) - Workout duration
- **Workout Active** (binary sensor) - Whether workout is in progress

### Treadmill-Specific
- **Inclination** (%) - Treadmill incline angle
- **Pace** (min/km) - Running pace

### Indoor Bike-Specific
- **Cadence** (rpm) - Instantaneous pedaling cadence
- **Average Cadence** (rpm) - Session average cadence
- **Average Power** (watts) - Session average power output
- **Resistance Level** - Current resistance setting

### Rower-Specific
- **Stroke Rate** (strokes/min) - Instantaneous rowing rate
- **Average Stroke Rate** (strokes/min) - Session average stroke rate
- **Stroke Count** - Total strokes
- **Pace** (sec/500m) - Instantaneous pace per 500 meters
- **Average Pace** (sec/500m) - Session average pace
- **Average Power** (watts) - Session average power output

## Example Automations

### Adjust Fan Speed Based on Workout Intensity

```yaml
automation:
  - alias: "Adjust fan during workout"
    trigger:
      - platform: state
        entity_id: binary_sensor.treadmill_workout_active
        to: "on"
    action:
      - service: fan.turn_on
        target:
          entity_id: fan.bedroom_fan
      - repeat:
          while:
            - condition: state
              entity_id: binary_sensor.treadmill_workout_active
              state: "on"
          sequence:
            - service: fan.set_percentage
              target:
                entity_id: fan.bedroom_fan
              data:
                percentage: >
                  {% set power = states('sensor.treadmill_power') | float(0) %}
                  {{ min(100, max(30, (power / 3) | round)) }}
            - delay: "00:00:10"
```

### High Heart Rate Alert

```yaml
automation:
  - alias: "Alert on high heart rate"
    trigger:
      - platform: numeric_state
        entity_id: sensor.treadmill_heart_rate
        above: 180
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "Heart rate is {{ states('sensor.treadmill_heart_rate') }} BPM!"
          title: "High Heart Rate Alert"
```

### RGB Light Control Based on Power Output

```yaml
automation:
  - alias: "RGB lights track workout power"
    trigger:
      - platform: state
        entity_id: sensor.bike_power
    condition:
      - condition: state
        entity_id: binary_sensor.bike_workout_active
        state: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.workout_room_rgb
        data:
          brightness: 255
          transition: 2
          rgb_color: >
            {% set power = states('sensor.bike_power') | float(0) %}
            {% if power < 50 %}
              [0, 0, 255]     {# Blue - Low intensity #}
            {% elif power < 100 %}
              [0, 255, 0]     {# Green - Moderate #}
            {% elif power < 150 %}
              [255, 255, 0]   {# Yellow - Getting hard #}
            {% elif power < 200 %}
              [255, 128, 0]   {# Orange - Hard #}
            {% else %}
              [255, 0, 0]     {# Red - Maximum effort #}
            {% endif %}
```

More automation examples can be found in the [wiki](../../wiki).

## Technical Details

### FTMS Protocol

The integration implements the Bluetooth FTMS (Fitness Machine Service) specification:
- Service UUID: `00001826-0000-1000-8000-00805f9b34fb`
- Characteristics parsed:
  - Treadmill Data: `00002acd-0000-1000-8000-00805f9b34fb`
  - Indoor Bike Data: `00002ad2-0000-1000-8000-00805f9b34fb`
  - Rower Data: `00002ad1-0000-1000-8000-00805f9b34fb`
- Device Information Service: `0000180a-0000-1000-8000-00805f9b34fb`

### Architecture

- **Runtime Data Pattern**: Uses `entry.runtime_data` for coordinator access
- **DataUpdateCoordinator**: Manages BLE connection and data updates
- **Push-based updates**: Uses BLE notifications for real-time data
- **Automatic reconnection**: Handles disconnects gracefully with retry logic
- **Type-aware parsing**: Detects device type and parses appropriate characteristics
- **Device Information**: Reads manufacturer and model from Device Information Service

### Code Quality

This integration follows Home Assistant core standards:
- Python 3.12+ with modern features (type hints, pattern matching)
- Comprehensive async implementation
- Proper error handling with specific exception types
- Fresh BleakClient instances (never reused)
- Minimal try blocks with data processing outside
- Lazy logging for performance

## Troubleshooting

### Device Not Discovered

1. Ensure your fitness device is powered on and in pairing mode
2. Check that your Bluetooth adapter is working: Settings > System > Hardware
3. Make sure the device isn't already connected to another app
4. Try restarting the Bluetooth integration

### Connection Issues

1. Move your Bluetooth adapter closer to the fitness device
2. Remove the device and re-add it
3. Check Home Assistant logs for error messages
4. Ensure `bleak-retry-connector` is installed (should be automatic)

### No Data Showing

1. Verify the workout is active (start moving/pedaling)
2. Check that sensors are enabled in the device page
3. Some devices only send data when certain conditions are met
4. Review logs for parsing errors

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.fitness_equipment: debug
```

## Development

See [AGENTS.md](AGENTS.md) for detailed development instructions and coding standards.

### File Structure

```
custom_components/fitness_equipment/
├── __init__.py           # Entry point (runtime_data pattern)
├── coordinator.py        # BLE coordinator with error handling
├── device.py             # Device helper functions
├── binary_sensor.py      # Workout active sensor
├── config_flow.py        # Discovery and configuration
├── const.py              # Constants and UUIDs
├── ftms_parser.py        # FTMS protocol parser
├── manifest.json         # Integration metadata
├── sensor.py             # Sensor entities
├── strings.json          # UI translations
└── quality_scale.yaml    # Quality scale for diagnostics
```

## Credits

- FTMS Specification: [Bluetooth SIG](https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/)
- Built with [Bleak](https://github.com/hbldh/bleak) BLE library
- Inspired by the Home Assistant Bluetooth integration architecture

## License

MIT License - See [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Follow the coding standards in [AGENTS.md](AGENTS.md)
4. Submit a pull request

## Support

For issues, questions, or feature requests, please [open an issue](../../issues) on GitHub.

## Changelog

### v0.4.3 (Current)
- Added manufacturer and model reading from Device Information Service
- Improved device info display

### v0.4.2
- Restored `integration_type: device` in manifest
- Fixed integration not appearing in UI

### v0.2.1 (Original)
- Initial working version as `ble_fitness`
