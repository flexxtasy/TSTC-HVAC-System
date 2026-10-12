# TSTC-HVAC-System

A BACnet control interface for a lab HVAC system — built as a collaborative
TSTC cyber-club project. *Credit for the underlying HVAC controller belongs to
[Ricardo "Rick" De Leon Jr.](https://www.linkedin.com/in/ricardo-de-leon-jr-225b5756) (see below).*

A protocol-agnostic control engine drives the unit through a swappable driver —
a built-in simulator for development (**runs with no hardware**), and a BACnet
driver for the live controller — behind a web or desktop UI.

## Credit

The HVAC controller this project builds on was designed and built by
**Ricardo "Rick" De Leon Jr.**
([LinkedIn](https://www.linkedin.com/in/ricardo-de-leon-jr-225b5756)) — a TSTC
cybersecurity student and SkillsUSA medalist. He wired the Raspberry Pi
controller, its relay board and temperature sensor, and the BACnet stack, and
set it up as a SkillsUSA pentest-practice lab. Our team (Ramiro and Carlos)
built the control interface, dashboard, and integration work documented here on
top of Rick's system, with his permission. Any credit for "the HVAC system"
itself belongs to Rick first.

## What this is

Software to monitor and control an HVAC unit (AC, fan, heater, temperature
setpoint) over a clean, testable architecture:

- **`controller.py`** — protocol-agnostic control core: off/heat/cool/auto
  modes, setpoint + deadband trigger logic (anti short-cycling), min/max
  tracking, manual overrides, an in-memory event log, and CSV logging. Hardware
  sits behind a **driver interface**:
  - `SimDriver` — a simulated HVAC unit (room temp drifts toward ambient; AC
    cools, heater warms, fan circulates) so the whole system runs with no
    hardware.
  - `BacnetDriver` — the swap-in point for a real BACnet unit (address, device
    id, and a point map supplied as local config — never committed).
- **`app.py`** — web UI (Python standard library only, no dependencies).
- **`gui.py`** — Tkinter desktop UI on the same engine.

## Run it (simulation — no hardware needed)

​```bash
# Web UI
python3 app.py --sim          # then open http://localhost:8080

# Desktop UI
python3 gui.py
​```

Both drive the simulated unit end-to-end: thermostat logic, setpoint changes,
AC/fan/heater, live readings, and CSV logging.

## Architecture

​```
driver layer   (SimDriver for dev, BacnetDriver for the live unit)
   -> control loop   (deadband thermostat logic + manual overrides)
   -> CSV log + in-memory event feed
   -> UI skin:  web (stdlib)  OR  Tkinter desktop
​```

One engine, swappable UI skins and swappable driver — the same control logic
runs against the simulator or a live BACnet device.

## Progress update — 2026-10-12: live control working

The authorized security phase is complete, and the project moved to the build
half — our software now drives the real HVAC unit over BACnet.

- Studied the controller's original scripts, then consolidated several separate
  programs into one clean single-file control engine (kept in private lab
  notes — see the security-lab note below).
- **Fixed 5 real bugs caused by BACnet library drift** (the reference code was
  written against older BAC0 / bacpypes3 versions) — full writeup in
  [`docs/bac0-integration-notes.md`](docs/bac0-integration-notes.md).
- **Deployed and verified on real hardware** — exercised remote output control
  over BACnet end-to-end, then released everything back to auto.
- **Built a web dashboard** (Flask + BAC0): polls the unit every 2 s, with
  AC / Fan / setpoint / trip-point controls and a °F display (BACnet stays °C
  internally). *(The live dashboard talks to real lab addresses, so it's kept
  in private notes, not here.)*

### Roadmap
- [x] Control interface + simulator (web + desktop)
- [x] Authorized security phase complete
- [x] BACnet integration working against the live unit
- [~] Wire this `controller.py` interface to the live BACnet points

## Security-lab note

The underlying controller is a **SkillsUSA pentest-practice target** — a lab
built to be assessed, not a production system. To keep it usable as a challenge
for future students, this repository intentionally contains **no** lab
specifics: no credentials, addresses, device internals, detection/deception
details, or exploitation steps. That material is kept in private notes only.
This repo is about the *engineering* — the control software and BACnet
integration.

## Sanitization

Public repository — never commit real IPs, hostnames, MACs, credentials, keys,
or lab-challenge internals (point maps, device IDs, honeypot details). Real
values live in private notes. See `.gitignore` for blocked patterns.
