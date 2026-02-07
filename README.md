# JAAM

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

<!--
Uncomment and customize these badges if you want to use them:

[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
[![Discord][discord-shield]][discord]
-->

**✨ Develop in the cloud:** Want to contribute or customize this integration? Open it directly in GitHub Codespaces - no local setup required!

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/J-A-A-M/jaam_ha?quickstart=1)

## ✨ Features

- **Easy Setup**: Simple configuration through the UI - no YAML required
- **Real-time Monitoring**: WebSocket connection for instant updates
- **Alert System**: 11 separate binary sensors for different threat types
- **Location Info**: Track home district name and temperature
- **System Diagnostics**: Monitor device health (memory, uptime, WiFi signal, CPU temperature)
- **Smart Light Control**: Control integrated lamp with brightness and color
- **Map Display**: Select different map visualization modes
- **Reconfigurable**: Change host/port anytime without removing the integration

**This integration will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | WebSocket connection status and 11 alert type sensors
`light` | Lamp control with brightness and color
`select` | Map mode selection
`sensor` | Home district, temperature, and system diagnostics (6 sensors)

## 🚀 Quick Start

### Step 1: Install the Integration

**Prerequisites:** This integration requires [HACS](https://hacs.xyz/) (Home Assistant Community Store) to be installed.

Click the button below to open the integration directly in HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jpawlowski&repository=jaam_ha&category=integration)

Then:

1. Click "Download" to install the integration
2. **Restart Home Assistant** (required after installation)

> **Note:** The My Home Assistant redirect will first take you to a landing page. Click the button there to open your Home Assistant instance.

<details>
<summary>**Manual Installation (Advanced)**</summary>

If you prefer not to use HACS:

1. Download the `custom_components/jaam_ha/` folder from this repository
2. Copy it to your Home Assistant's `custom_components/` directory
3. Restart Home Assistant

</details>

### Step 2: Add and Configure the Integration

**Important:** You must have installed the integration first (see Step 1) and restarted Home Assistant!

#### Option 1: One-Click Setup (Quick)

Click the button below to open the configuration dialog:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=jaam_ha)

Follow the setup wizard:

1. Enter your device **Host** (IP address or hostname)
2. Enter the **Port** (default: 81)
3. Click Submit

That's it! The integration will connect to your JAAM device via WebSocket.

#### Option 2: Manual Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for "JAAM"
4. Follow the same setup steps as Option 1

### Step 3: Reconfigure Connection (Optional)

You can change the device connection settings anytime:

1. Go to **Settings** → **Devices & Services**
2. Find **JAAM**
3. Click the **3 dots menu** → **Reconfigure**
4. Update host/port as needed

### Step 4: Start Using!

The integration creates several entities for your JAAM device:

- **Binary Sensors**: WebSocket connection status + 11 alert type sensors
- **Light**: Lamp control with brightness and color
- **Select**: Map display mode selection
- **Sensors**: Home district, temperature, and 6 system diagnostic sensors

Find all entities in **Settings** → **Devices & Services** → **JAAM** → click on the device.

## Available Entities

### Binary Sensors

#### WebSocket Status (Diagnostic)
- Shows real-time WebSocket connection status
- **On**: Connected and receiving updates
- **Off**: Connection lost or device offline

#### Alert Sensors
11 separate binary sensors for different threat types (updated in real-time):

- **Air Alert**: General air raid alert
- **Artillery**: Artillery threat alert
- **Urban Combat**: Urban combat operations alert
- **Chemical**: Chemical hazard alert
- **Nuclear**: Nuclear threat alert
- **Drones**: Drone attack alert
- **Missiles**: Missile threat alert
- **KAB (Air Bombs)**: Guided air bomb alert
- **Ballistic Missiles**: Ballistic missile alert
- **Explosion Hazard**: Explosion danger alert
- **Reconnaissance**: Reconnaissance drone alert

Each alert sensor:
- Shows active state (On/Off)
- Dynamic icon based on alert state
- Can be used in automations for notifications

### Light

- **Lamp**: Control integrated lamp
  - Turn on/off
  - Adjust brightness
  - Change color (if supported)

### Select

- **Map Mode**: Choose map visualization mode
  - Different display options for the device map
  - Real-time sync with device

### Sensors

#### Location & Temperature

- **Home District**: Current home district/region name
  - Updates when location changes
- **Home District Temperature**: Temperature in your district (°C)
  - Real-time temperature monitoring

#### System Diagnostics (All Diagnostic Category)

- **Used Memory**: Current memory usage (MB)
  - Monitor device memory consumption
- **System Uptime**: How long the system has been running
  - Reset after device reboot
- **WiFi Uptime**: WiFi connection uptime
  - Shows WiFi connection stability
- **WiFi Signal**: WiFi signal strength (dBm or %)
  - Monitor connection quality
- **CPU Temperature**: Device CPU temperature (°C)
  - Monitor device thermal status
- **WebSocket Uptime**: WebSocket connection uptime
  - How long current WebSocket session is active

## Configuration Options

### During Setup

Name | Required | Default | Description
-- | -- | -- | --
Host | Yes | - | Device IP address or hostname
Port | No | 81 | WebSocket port number

### Reconfiguration

You can change connection settings anytime:

1. Go to **Settings** → **Devices & Services**
2. Find **JAAM**
3. Click **3 dots menu** → **Reconfigure**
4. Update host/port
5. Submit

## Troubleshooting

### Connection Issues

#### WebSocket Connection Status

Monitor your connection status with the **WebSocket Status** binary sensor:

- **On** (Connected): Integration is receiving real-time updates
- **Off** (Disconnected): Connection lost or device offline
  - Check the binary sensor attributes for diagnostic information
  - Verify device is powered on and connected to network
  - Check host/port settings are correct
  - Check network connectivity

#### Reconfigure Connection

If your device IP or port changes:

1. Go to **Settings** → **Devices & Services**
2. Find **JAAM**
3. Click the **3 dots menu** → **Reconfigure**
4. Enter new host/port
5. Click Submit

The integration will automatically reconnect with the new settings.

### Enable Debug Logging

To enable debug logging for this integration, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.jaam_ha: debug
```

### Common Issues

#### Device Not Responding

If your device is not responding:

1. Check the **WebSocket Status** binary sensor - it should be "On"
2. Verify device IP address is correct (try pinging the device)
3. Verify port 81 is accessible (or your configured port)
4. Check your network connection - device and Home Assistant on same network?
5. Verify the device is powered on
6. Check the integration diagnostics (Settings → Devices & Services → **JAAM** → 3 dots → Download diagnostics)

#### Alert Sensors Not Updating

If alert sensors are not showing correct states:

1. Check **WebSocket Status** is "On" (connection required for real-time updates)
2. Verify device is receiving alert data from server
3. Check system diagnostic sensors are updating (proves WebSocket is working)
4. Enable debug logging (see below) and check for error messages

## 🤝 Contributing

Contributions are welcome! Please open an issue or pull request if you have suggestions or improvements.

### 🛠️ Development Setup

Want to contribute or customize this integration? You have two options:

#### Cloud Development (Recommended)

The easiest way to get started - develop directly in your browser with GitHub Codespaces:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/J-A-A-M/jaam_ha?quickstart=1)

- ✅ Zero local setup required
- ✅ Pre-configured development environment
- ✅ Home Assistant included for testing
- ✅ 60 hours/month free for personal accounts

#### Local Development

Prefer working on your machine? You'll need:

- Docker Desktop
- VS Code with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

Then:

1. Clone this repository
2. Open in VS Code
3. Click "Reopen in Container" when prompted

Both options give you the same fully-configured development environment with Home Assistant, Python 3.13, and all necessary tools.

---

## 🤖 AI-Assisted Development

> **ℹ️ Transparency Notice**
>
> This integration was developed with assistance from AI coding agents (GitHub Copilot, Claude, and others). While the codebase follows Home Assistant Core standards, AI-generated code may not be reviewed or tested to the same extent as manually written code.
>
> AI tools were used to:
>
> - Generate boilerplate code following Home Assistant patterns
> - Implement standard integration features (config flow, coordinator, entities)
> - Ensure code quality and type safety
> - Write documentation and comments
>
> Please be aware that AI-assisted development may result in unexpected behavior or edge cases that haven't been thoroughly tested. If you encounter any issues, please [open an issue](../../issues) on GitHub.
>
> *Note: This section can be removed or modified if AI assistance was not used in your integration's development.*

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ by [@J-A-A-M][user_profile]**

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/J-A-A-M/jaam_ha.svg?style=for-the-badge
[commits]: https://github.com/J-A-A-M/jaam_ha/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/J-A-A-M/jaam_ha.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40J-A-A-M-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/J-A-A-M/jaam_ha.svg?style=for-the-badge
[releases]: https://github.com/J-A-A-M/jaam_ha/releases
[user_profile]: https://github.com/jpawlowski

<!-- Optional badge definitions - uncomment if needed:
[buymecoffee]: https://www.buymeacoffee.com/jpawlowski
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
-->
