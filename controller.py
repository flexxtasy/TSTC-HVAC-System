"""
HVAC controller core — protocol-agnostic.

Switches:   ac, fan, heater  (on/off)
Trigger:    setpoint (target temp) + deadband
Display:    current temp, plus min/max seen since start
Logs:       CSV row every log_interval seconds

Hardware access goes through a Driver interface so this same core can
drive GPIO relays on a Pi, Modbus, or BAC0/BACnet later without changes.
"""

import csv
import os
import random
import threading
import time
from datetime import datetime


# ---------------------------------------------------------------- drivers

class SimDriver:
    """Fake HVAC box: room temp drifts toward ambient, outputs push it."""

    def __init__(self, start_temp=22.0, ambient=30.0):
        self.temp = start_temp
        self.ambient = ambient
        self.ac_on = self.heater_on = self.fan_on = False

    def read_temp(self):
        # drift toward ambient
        self.temp += (self.ambient - self.temp) * 0.02
        # outputs fight the drift
        if self.ac_on:
            self.temp -= 0.15
        if self.heater_on:
            self.temp += 0.20
        if self.fan_on:
            self.temp += (self.ambient - self.temp) * 0.01
        self.temp += random.uniform(-0.02, 0.02)
        return round(self.temp, 2)

    def set_output(self, name, on):
        setattr(self, name + "_on", bool(on))


class BacnetDriver:
    """BAC0/BACnet driver — fill in device address + point names for .183.

    Not active yet: passive-only rule. Kept as the swap-in point.
    """

    def __init__(self, address, device_id, points):
        self.address = address          # e.g. '192.168.x.x' or '3:4'
        self.device_id = device_id      # BACnet device instance
        self.points = points            # {'temp': 'analog-input,2', 'ac': 'binary-value,1', ...}

    def connect(self):
        import BAC0  # lazy: only needed when actually going live
        self.bacnet = BAC0.start()
        self.dev = BAC0.device(self.address, self.device_id, self.bacnet)

    def read_temp(self):
        return float(self.dev[self.points["temp"]].value)

    def set_output(self, name, on):
        self.dev[self.points[name]].value = 1 if on else 0


# ---------------------------------------------------------------- controller

class HVACController:
    def __init__(self, driver, log_path="hvac_log.csv",
                 log_interval=10.0, poll_interval=2.0,
                 setpoint=21.0, deadband=1.0, mode="auto"):
        self.driver = driver
        self.log_path = log_path
        self.log_interval = log_interval
        self.poll_interval = poll_interval

        # state
        self.mode = mode              # 'off' | 'heat' | 'cool' | 'auto'
        self.setpoint = setpoint      # trigger temperature
        self.deadband = deadband      # +/- around setpoint before firing
        self.fan_manual = False       # fan switch: manual ON (else auto w/ calls)
        self.ac_on = False
        self.heater_on = False
        self.fan_on = False

        self.temp = driver.read_temp()
        self.min_temp = self.temp
        self.max_temp = self.temp

        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        self._last_log = 0.0
        self.events = []              # in-memory event log (recent)

    # ---- public controls (what the UI calls) ----

    def set_switch(self, name, on):
        with self._lock:
            if name == "ac":
                self.ac_manual = bool(on)
                if not on and self.ac_on:
                    self.ac_on = False
                    self.driver.set_output("ac", False)
                    self._event("AC off (manual)")
            elif name == "heater":
                self.heat_manual = bool(on)
                if not on and self.heater_on:
                    self.heater_on = False
                    self.driver.set_output("heater", False)
                    self._event("Heater off (manual)")
            elif name == "fan":
                self.fan_manual = bool(on)
                self._event("Fan manual " + ("on" if on else "off"))
            else:
                raise ValueError("unknown switch: " + name)

    def get_switch(self, name):
        if name == "ac":
            return self.ac_on
        if name == "heater":
            return self.heater_on
        if name == "fan":
            return self.fan_on
        raise ValueError("unknown switch: " + name)

    def set_setpoint(self, value):
        value = float(value)
        if not (5.0 <= value <= 40.0):
            raise ValueError("setpoint out of range 5-40 C")
        with self._lock:
            self.setpoint = value
            self._event(f"Setpoint -> {value:.1f} C")

    def set_mode(self, mode):
        if mode not in ("off", "heat", "cool", "auto"):
            raise ValueError("mode must be off/heat/cool/auto")
        with self._lock:
            self.mode = mode
            if mode == "off":
                self._all_off()
            self._event(f"Mode -> {mode}")

    def status(self):
        return {
            "temp": self.temp,
            "min_temp": self.min_temp,
            "max_temp": self.max_temp,
            "setpoint": self.setpoint,
            "deadband": self.deadband,
            "mode": self.mode,
            "ac_on": self.ac_on,
            "heater_on": self.heater_on,
            "fan_on": self.fan_on,
            "fan_manual": self.fan_manual,
            "ac_manual": getattr(self, "ac_manual", True),
            "heat_manual": getattr(self, "heat_manual", True),
            "events": list(self.events[-20:]),
        }

    # ---- internals ----

    def _all_off(self):
        for name in ("ac", "heater", "fan"):
            self.driver.set_output(name, False)
        self.ac_on = self.heater_on = self.fan_on = False

    def _event(self, msg):
        stamp = datetime.now().isoformat(timespec="seconds")
        self.events.append(f"{stamp}  {msg}")
        del self.events[:-50]

    def _control_loop(self):
        while not self._stop.is_set():
            with self._lock:
                self.temp = self.driver.read_temp()
                self.min_temp = min(self.min_temp, self.temp)
                self.max_temp = max(self.max_temp, self.temp)

                if self.mode == "off":
                    want_ac = want_heat = False
                else:
                    lo = self.setpoint - self.deadband
                    hi = self.setpoint + self.deadband
                    want_ac = (self.mode in ("cool", "auto")
                               and self.temp > hi
                               and getattr(self, "ac_manual", True))
                    want_heat = (self.mode in ("heat", "auto")
                                 and self.temp < lo
                                 and getattr(self, "heat_manual", True))

                want_fan = self.fan_manual or want_ac or want_heat

                for name, want in (("ac", want_ac), ("heater", want_heat),
                                   ("fan", want_fan)):
                    cur = getattr(self, name + "_on")
                    if want != cur:
                        setattr(self, name + "_on", want)
                        self.driver.set_output(name, want)
                        self._event(f"{name.upper()} {'ON' if want else 'OFF'} "
                                    f"(temp={self.temp:.1f} sp={self.setpoint:.1f})")

            now = time.time()
            if now - self._last_log >= self.log_interval:
                self._write_log()
                self._last_log = now
            self._stop.wait(self.poll_interval)

    def _write_log(self):
        new = not os.path.exists(self.log_path)
        with open(self.log_path, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["timestamp", "temp_c", "setpoint_c", "mode",
                            "ac", "heater", "fan"])
            w.writerow([datetime.now().isoformat(timespec="seconds"),
                        self.temp, self.setpoint, self.mode,
                        int(self.ac_on), int(self.heater_on), int(self.fan_on)])

    def start(self):
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        with self._lock:
            self._all_off()
