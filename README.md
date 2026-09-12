# KlikAanKlikUit ICS2000 — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/Cyclone47/ha-kaku-ics2000.svg)](https://github.com/Cyclone47/ha-kaku-ics2000/releases)

A proper Home Assistant custom integration for the **KlikAanKlikUit / Trust ICS2000** smart home hub.

Unlike existing integrations that map everything as a light, this integration correctly identifies **all device types** — lights, dimmers, switches, shutters/rolluiken, sensors, and more.

---

## ✅ Supported Device Types

| ICS2000 device | Home Assistant entity | Notes |
|---|---|---|
| Aan/uit schakelaar (type 1) | `switch` | Generic on/off switch |
| Dimmer (type 2) | `light` | Full brightness slider (0–255) |
| Garage motor (type 3) | `cover` | Open / close |
| Contact/motion sensor (type 4) | `binary_sensor` | Door open / motion |
| Rolluik / shutter (type 23) | `cover` | ▲ Open · MY Stop · ▼ Close |
| Simple lamp (type 24) | `light` | On / off only |
| Switch group (type 27) | `switch` | Group on/off |
| Zigbee temp+humidity (type 46) | `sensor` | °C + % RH |
| **Scenes (Scenarios)** | `scene` | Native HA scene activation |
| **Scene Play / Stop** | `button` | Explicit ▶ Play and ⏹ Stop buttons |

---

## 🚀 Installation via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Cyclone47&repository=ha-kaku-ics2000&category=integration)

1. Click the button above **or** open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/Cyclone47/ha-kaku-ics2000` as an **Integration**
3. Search for **KlikAanKlikUit ICS2000** and click **Download**
4. Restart Home Assistant

---

## ⚙️ Setup

After installation and restart:

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **KlikAanKlikUit ICS2000**
3. Enter:
   - **MAC address** — printed on the label of your ICS2000 hub (e.g. `AA:BB:CC:DD:EE:FF`)
   - **Email** — your KlikAanKlikUit / Trust Smart Cloud account email
   - **Password** — your account password

All devices will be discovered automatically and grouped by type.

---

## 🪟 Shutter / Rolluik Control

Shutters appear as **Cover** entities in HA with three buttons:

| Button | ICS2000 | Action |
|---|---|---|
| ▲ | Up | Open the shutter |
| ⏹ | MY | Stop at favourite position |
| ▼ | Down | Close the shutter |

> **Note:** The ICS2000 does not report shutter position (0–100%). State is tracked optimistically based on the last command.

---

## 🔄 Polling

Devices are polled every **30 seconds** via the ICS2000 cloud API. The integration requires internet access.

---

## 🏗️ Architecture

```
custom_components/kaku_ics2000/
├── __init__.py        — Integration setup + DataUpdateCoordinator
├── manifest.json      — HA / HACS metadata
├── config_flow.py     — UI-based setup (no YAML required)
├── const.py           — Device type map, API constants, command codes
├── hub.py             — ICS2000 cloud API client
├── entity.py          — Shared base entity
├── light.py           — Dimmer + on/off light
├── switch.py          — Switch
├── cover.py           — Shutter (rolluik) + garage door
├── sensor.py          — Temperature / humidity
└── binary_sensor.py   — Door / motion sensor
```

---

## 📝 Credits

Reverse-engineered from the ICS2000 cloud API with device type discovery performed directly against a live hub.

Based on prior art by [@rdegraafwhizzkit](https://github.com/rdegraafwhizzkit) and [@Stijn-Jacobs](https://github.com/Stijn-Jacobs).
