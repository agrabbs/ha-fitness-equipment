# AI Agent Instructions - Fitness Equipment Integration

## Project Overview

This is a **Home Assistant custom integration** for Bluetooth fitness equipment using the FTMS (Fitness Machine Service) protocol.

- **Domain**: `fitness_equipment`
- **Version**: 0.4.2
- **Status**: ✅ Working and deployed on vassar server
- **Location**: `/var/lib/homeassistant/homeassistant/custom_components/fitness_equipment/`

### Supported Devices
- Wahoo KICKR Run treadmill (primary test device)
- Any FTMS-compatible fitness equipment (treadmills, bikes, rowers, etc.)

### Key Features
- ✅ Bluetooth auto-discovery via FTMS service UUID (`00001826-0000-1000-8000-00805f9b34fb`)
- ✅ Manual device setup via config flow
- ✅ Real-time sensor updates (speed, pace, incline, heart rate, calories, etc.)
- ✅ Binary sensors (moving, paused)
- ✅ Enhanced error handling with retry logic
- ✅ Clean coordinator pattern (Phase 2 & 3 refactoring complete)

## Architecture

### Code Structure
```
custom_components/fitness_equipment/
├── __init__.py              # Entry point (53 lines) - runtime_data pattern
├── coordinator.py           # BLE coordinator with error handling (393 lines)
├── device.py                # Device helper functions (57 lines)
├── config_flow.py           # UI config flow (Bluetooth discovery + manual)
├── const.py                 # Constants and domain definition
├── ftms_parser.py           # FTMS protocol parser (kept in integration)
├── sensor.py                # Sensor entities
├── binary_sensor.py         # Binary sensor entities
├── manifest.json            # Integration metadata
├── strings.json             # UI strings
└── quality_scale.yaml       # Quality scale for diagnostics
```

### Key Patterns Used
- **Runtime Data Pattern**: `entry.runtime_data = coordinator`
- **Type Aliases**: `type FitnessEquipmentConfigEntry = ConfigEntry[FitnessEquipmentCoordinator]`
- **Coordinator Pattern**: `FitnessEquipmentCoordinator` handles BLE communication
- **Device Helpers**: Centralized device info functions in `device.py`

## Critical Configuration

### manifest.json Requirements

**CRITICAL**: Never remove `"integration_type": "device"` - it's required for Bluetooth device integrations!

```json
{
  "domain": "fitness_equipment",
  "name": "Fitness Equipment",
  "integration_type": "device",  ← CRITICAL - DO NOT REMOVE
  "config_flow": true,
  "dependencies": ["bluetooth_adapters"],
  "iot_class": "local_push",
  "requirements": ["bleak-retry-connector>=3.5.0"],
  "bluetooth": [
    {
      "service_uuid": "00001826-0000-1000-8000-00805f9b34fb",
      "connectable": true
    }
  ],
  "version": "0.4.2"
}
```

## Development History

### What Happened
1. **Original**: `ble_fitness` v0.2.1 (working)
2. **Phase 2**: Renamed to `fitness_equipment`, extracted coordinator, runtime_data pattern
3. **Phase 3**: Added error handling, logging, type hints, device helpers
4. **Issue**: Integration stopped appearing in HA after refactoring
5. **Root Cause**: Removed `integration_type` field + orphaned entities
6. **Fix**: Restored `integration_type`, cleaned orphaned entities
7. **Status**: ✅ Now working with all improvements

### Key Lesson Learned
**Never remove manifest.json fields without research!** The `"integration_type": "device"` field is critical for HA to recognize Bluetooth device integrations, even though all Python code was correct.

## Deployment

### Installation

Use the provided installation script:

```bash
# Clone the repository
git clone https://github.com/yourusername/ha-fitness-equipment.git
cd ha-fitness-equipment

# Run the installation script
./install.sh
```

The script will:
1. Detect your Home Assistant configuration directory
2. Copy files to `custom_components/fitness_equipment/`
3. Set proper permissions
4. Provide next steps for setup

### Manual Installation

```bash
# Copy integration to custom_components
cp -r custom_components/fitness_equipment /path/to/homeassistant/custom_components/

# Restart Home Assistant
# Then add the integration via UI
```

## Code Quality Standards

Follow **Home Assistant Core** standards (see `ha-core/AGENTS.md` for full details):

### Critical Rules
- ✅ **Python 3.12+** with modern features (type hints, pattern matching, walrus operator)
- ✅ **Async everything** - no blocking I/O in event loop
- ✅ **Type hints required** - comprehensive typing on all functions/methods
- ✅ **Specific exceptions** - use `ConfigEntryNotReady`, `ConfigEntryAuthFailed`, etc.
- ✅ **Lazy logging** - `_LOGGER.debug("Message with %s", variable)`
- ✅ **Fresh BleakClient instances** - don't reuse
- ✅ **Minimal try blocks** - process data outside try/catch
- ✅ **No bare exceptions** in regular code (only in config_flow and background tasks)

### Anti-Patterns to Avoid
```python
# ❌ DON'T: Block event loop
data = requests.get(url)
time.sleep(5)

# ✅ DO: Use async
data = await hass.async_add_executor_job(requests.get, url)
await asyncio.sleep(5)

# ❌ DON'T: Reuse BleakClient
self.client = BleakClient(address)
await self.client.connect()

# ✅ DO: Fresh instance each time
client = BleakClient(address)
await client.connect()

# ❌ DON'T: Too much in try block
try:
    data = await device.get_data()
    processed = data["value"] * 100  # ❌ Process outside
except DeviceError:
    _LOGGER.error("Failed")

# ✅ DO: Minimal try block
try:
    data = await device.get_data()
except DeviceError:
    _LOGGER.error("Failed")
    return
processed = data["value"] * 100  # ✅ Process outside
```

## Future Phases (Optional)

### Phase 4: Translations
- Add `translations/en.json`
- Support multiple languages

### Phase 5: Testing
- Unit tests for FTMS parser
- Integration tests with mocked devices
- pytest fixtures

### Long-term: Core Integration Submission
- Extract FTMS parser to separate PyPI library
- Add comprehensive tests (required)
- Follow HA core quality requirements
- Submit PR to `home-assistant/core`

## Quick Reference

### Common Tasks

**Make code changes:**
1. Edit files in `custom_components/fitness_equipment/`
2. Run `./install.sh` to copy to Home Assistant
3. Restart Home Assistant
4. Test the changes

**Check logs:**
```bash
# Home Assistant OS / Supervised
ha core logs | grep -i fitness

# Home Assistant Core
journalctl -u home-assistant@homeassistant -f | grep -i fitness
```

**Verify integration loaded:**
- Check Settings > System > Logs
- Look for "fitness_equipment" mentions
- Verify integration appears in "Add Integration" list

### Important Files to Never Delete
- `manifest.json` - Integration metadata (KEEP `integration_type`!)
- `strings.json` - UI translations
- `__init__.py` - Entry point
- `config_flow.py` - Setup flow
- `coordinator.py` - BLE communication
- `ftms_parser.py` - FTMS protocol parser

### Safe to Modify
- `sensor.py` - Add/remove sensors
- `binary_sensor.py` - Add/remove binary sensors
- `const.py` - Add constants
- `device.py` - Device helper functions
- `quality_scale.yaml` - Diagnostics quality scale

## Troubleshooting

### Integration Not Appearing
1. Check `integration_type: device` is in manifest.json
2. Run diagnostics: `sudo bash /tmp/full_diagnostic.sh`
3. Check logs for Python errors
4. Verify file permissions (homeassistant:homeassistant)

### Bluetooth Not Working
1. Check Bluetooth adapter: `hciconfig`
2. Scan for devices: `sudo hcitool lescan`
3. Verify device is advertising FTMS UUID
4. Check HA logs for bluetooth errors

### Import Errors
1. Test Python import: `python3 /tmp/test_import.py`
2. Check Python version (requires 3.12+)
3. Verify all files exist in integration directory

## Resources

- **FTMS Spec**: Bluetooth SIG FTMS service (UUID 0x1826)
- **Bleak Library**: https://github.com/hbldh/bleak
- **Home Assistant Dev Docs**: https://developers.home-assistant.io/

---

**Status**: ✅ Integration working as of v0.4.2  
**Last Updated**: After successful cleanup and manifest fix
