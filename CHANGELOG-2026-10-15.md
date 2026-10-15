# HVAC Interface — Update Log: 2026-10-15

Everything done today on the CyberHVAC Raspberry Pi (`cyberclub@<PI_LAN_IP>`). All changes were run and **live-verified on the Pi** over BACnet before being saved.

## 1. Access recovery (Rick's relab)
- SSH username on the Pi changed from `pi` → **`cyberclub`** during Rick's relab. Our SSH public key survived; documented password also still works.
- Home directory and all previous files (including Oct-12 `master_code.py`) intact — not a re-image.

## 2. New lab docs from Rick
- `FIRST BOOT.docx` and `master and updates.docx` uploaded to the Pi this morning; copied into the project and extracted.

## 3. Master script recreated: `hvac_master_2026.py`
Rebuilt the docx master so it actually runs on this Pi. Fixes vs. the docx code:
- `BAC0.lite(ip='<PI_LAN_IP>', deviceId=1234)` — docx used a placeholder IP and the wrong param name (`address=`; correct is `ip=` in BAC0 2025.9.15).
- Imports pinned to what works in `bac0env`: `BAC0.core.devices.local.factory` (analog_input / analog_value / binary_output), `gpiozero` with the **RPi.GPIO factory pinned explicitly** (bac0env's `lgpio==0.0.0.2` is older than gpiozero 2.0.1 expects and produced a silent-fallback warning; RPi.GPIO 0.7.1 is what the Oct-12 scripts used).
- Verified on the Pi with its own `~/bac0env` interpreter: COMPILE_OK + IMPORT_OK.

## 4. FIRST BOOT self-test: `first_boot.py`
- Extracted Rick's FIRST BOOT self-test into a runnable script; ran clean on the Pi (exit 0), zero warnings after the RPi.GPIO pin fix.

## 5. OLED display brought online
- Installed `luma` + Pillow in `bac0env`, enabled I2C in `/boot/firmware/config.txt` (Pi has passwordless sudo).
- I2C scan confirmed the SSD1306 OLED at **0x3C on bus 1**; the master now shows live temperature on the display.

## 6. Control logic updates (all live-verified over BACnet)
- **Heater**: ON when room temp falls below `Heating_Setpoint` (AV:2, default **20.0 °C**), off again at cutoff + 1.0 °C hysteresis. Relay on In3/GPIO22; status mirrored to BO:3. Caught a real cold event during testing.
- **Alarm**: ON **only** above `Alarm_Trippoint` (AV:3, default **40.1 °C** — TripNew.py's value). The AC trip never sounds the alarm (earlier build had it tied to the AC trip; corrected per spec). Relay In4/GPIO23; status mirrored to BO:4.
- **Fan**: ON when **neither** AC nor heater is calling, OFF otherwise — replaces the docx manual fan override; state mirrored to BO:2. All three states verified live.

## 7. BACnet object map (deviceId 1234, "BMS_Controller_01")
| Object | Name | Notes |
|---|---|---|
| AI:1 | Room_Temperature | DS18B20 1-Wire sensor |
| AV:1 | Temperature_Setpoint | default 24.0 °C (AC on above) — hackable via BACnet |
| AV:2 | Heating_Setpoint | default 20.0 °C — hackable |
| AV:3 | Alarm_Trippoint | default 40.1 °C — hackable |
| BO:1 | AC_Compressor_Blue | In1 / GPIO17 |
| BO:2 | Blower_Fan_White | In2 / GPIO27, mirrors auto-fan state |
| BO:3 | Heater_Status | In3 / GPIO22 (added today) |
| BO:4 | Alarm_Status | In4 / GPIO23 |
| AV:99 | honeypot | Honey-Object instance for intrusion watching |

Relays are **active-low** on this board. Hardware watchdog heartbeat is **enabled** (`dtparam=watchdog=on` confirmed in config.txt) — stop the script with **SIGINT/Ctrl-C**, not SIGTERM, so relays turn off and the watchdog magic-close runs (otherwise the Pi hard-reboots in ~16 s).

## 8. File locations
- Repo: `pi/hvac_master_2026.py`, `pi/first_boot.py` (public copies — real LAN IP replaced by `HVAC_BIND_IP` env var per the secrets policy).
- Pi: `/home/cyberclub/` — the live copies with the real bind IP, executable.
- Run on the Pi: `./hvac_master_2026.py` or `./first_boot.py` (shebang points at `~/bac0env/bin/python3`).
  - `ModuleNotFoundError: No module named 'BAC0'` = ran with system `python3` instead of the bac0env one; use the `./script.py` form or `source ~/bac0env/bin/activate` first.
