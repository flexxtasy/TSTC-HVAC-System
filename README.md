# TSTC-HVAC-System

A Python control interface for a lab HVAC system, built as part of an authorized
TSTC cyber-club project. The project has two halves: **break into a locked-down
controller** as an authorized red-team exercise, then **build the BACnet control
layer and software interface** for it.

This repository holds the **interface software and architecture** only. The
offensive/defensive security work (recon, testing methodology, findings) is kept
in private notes, not here — see [Scope & sanitization](#scope--sanitization).

## Team & authorization

- **Ramiro** and **Carlos** — TSTC cybersecurity students, building the software.
- **Rick** — mentor (former TSTC student), who set up the target controller and is
  coaching the pentest.
- Work is performed on **lab equipment we are authorized to test**, with the
  professor's and mentor's sign-off. Nothing here is run against systems outside
  that authorized lab.

## What it does

A software interface to monitor and control a classroom HVAC unit:

- Switch **AC / Fan / Heater** on and off.
- Change the **trigger temperature (setpoint)**.
- Display **current temperature** with running **min/max**.
- **Log** readings and output states to CSV.

## Architecture

One engine, two interchangeable UI "skins":

```
protocol layer  (SimDriver now; BacnetDriver later, via BAC0/BACpypes3)
   -> control loop  (background thread, 2s poll, 10s log)
   -> CSV log + in-memory event feed
   -> UI skin:  web (stdlib HTTP server)  OR  Tkinter desktop
```

Both UIs share the same `controller.py`, so the control logic is written once and
reused. Hardware sits behind a small **Driver interface**, which is the single
swap-in point when the project moves from simulation to a real controller.

### Components

- **`controller.py`** — core engine.
  - `SimDriver` — a simulated HVAC unit (temperature drifts toward ambient; AC
    cools, heater warms, fan adds circulation) so the UI can be developed and
    demoed with no hardware attached.
  - `BacnetDriver` — swap-in stub for the real unit. Takes an address, device id,
    and a point map; reads/writes BACnet points via BAC0. **Inactive until the
    hardware phase** — this is where real discovered point names will plug in.
  - `HVACController` — the control loop. Setpoint ± **deadband** trigger logic
    (AC fires above `setpoint + deadband`, heater below `setpoint − deadband`) to
    prevent short-cycling; off/heat/cool/auto modes; manual overrides; setpoint
    clamped to a safe range; min/max tracking; CSV logging.
- **`app.py`** — web interface (Python standard library only; no JS build step).
  Serves a dashboard and a small JSON status API, with form controls for the
  switches, setpoint, and mode. Preferred for final deployment (the target is
  headless).
- **`gui.py`** — Tkinter desktop app over the same engine, for local use on a
  workstation with a display.
- **`hvac_log.csv`** — sample simulation log
  (`timestamp, temp_c, setpoint_c, mode, ac, heater, fan`).

> **Note:** the source files are added in a follow-up commit by the authors; this
> README documents the design.

## Running (simulation)

```bash
# Web UI
python3 app.py --sim --port 8090      # then open http://localhost:8090

# Desktop UI
python3 gui.py --sim
```

No hardware or network access is required in simulation mode.

## Roadmap

- [x] Research reference BACnet/HVAC interfaces; extract a common architecture.
- [x] Build and test the control interface in simulation (web + desktop).
- [ ] **Security phase (authorized):** gain access to the lab controller.
- [ ] Passive BACnet discovery; map real point names.
- [ ] Implement `BacnetDriver` against the live unit.
- [ ] Deploy the interface on the controller / lab network.
- [ ] **Defensive write-up:** detection rules for the attack paths used
      (e.g. BACnet write monitoring, SSH brute-force detection) — turning the
      red-team work into a blue-team artifact.

## Scope & sanitization

This is a **public** repository. It must never contain real network details or
secrets:

- No real IPs, MAC addresses, or hostnames — use placeholders
  (`<CONTROLLER_IP>`, `<LAB_SUBNET>`).
- No credentials, keys, or tokens of any kind.
- No raw packet captures, attack logs, or scan output from the lab network.

All offensive and defensive security notes, target details, and evidence live in
**private** notes outside this repo. See `.gitignore` for the blocked patterns.
