"""
Web interface for the HVAC controller — stdlib only (no pip installs).

Run:  python3 app.py [--port 8080] [--sim]
Open http://localhost:8080
"""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from controller import HVACController, SimDriver

PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>HVAC Control</title>
<style>
 body{font-family:sans-serif;background:#111;color:#eee;max-width:720px;margin:2em auto;padding:0 1em}
 h1{font-size:1.4em}
 .big{font-size:3em;font-weight:bold}
 .row{display:flex;gap:1em;margin:1em 0;flex-wrap:wrap}
 .card{background:#1c1c1c;border:1px solid #333;border-radius:8px;padding:1em;flex:1;min-width:140px;text-align:center}
 .on{border-color:#2a2;color:#6f6}
 .off{border-color:#444;color:#888}
 button{padding:.6em 1.2em;border-radius:6px;border:1px solid #555;background:#222;color:#eee;cursor:pointer}
 button:hover{background:#333}
 input[type=number]{width:6em;padding:.4em;background:#222;color:#eee;border:1px solid #555;border-radius:4px}
 select{padding:.5em;background:#222;color:#eee;border:1px solid #555;border-radius:4px}
 .evt{font-family:monospace;font-size:.8em;color:#999;white-space:pre-wrap}
</style>
</head>
<body>
<h1>HVAC Control</h1>
<div class="row">
 <div class="card"><div>Current Temp</div><div class="big">%(temp).1f&deg;C</div></div>
 <div class="card"><div>Min</div><div class="big">%(min_t).1f&deg;C</div></div>
 <div class="card"><div>Max</div><div class="big">%(max_t).1f&deg;C</div></div>
 <div class="card"><div>Setpoint</div><div class="big">%(sp).1f&deg;C</div></div>
</div>
<div class="row">
 <div class="card %(ac_cls)"><div>AC</div><h2>%(ac_txt)s</h2>
   <form method=post><input type=hidden name=act value=switch><input type=hidden name=name value=ac>
   <input type=hidden name=on value=%(ac_next)s><button>Turn %(ac_next)s</button></form></div>
 <div class="card %(fan_cls)"><div>Fan</div><h2>%(fan_txt)s</h2>
   <form method=post><input type=hidden name=act value=switch><input type=hidden name=name value=fan>
   <input type=hidden name=on value=%(fan_next)s><button>Turn %(fan_next)s</button></form></div>
 <div class="card %(heat_cls)"><div>Heater</div><h2>%(heat_txt)s</h2>
   <form method=post><input type=hidden name=act value=switch><input type=hidden name=name value=heater>
   <input type=hidden name=on value=%(heat_next)s><button>Turn %(heat_next)s</button></form></div>
</div>
<div class="row">
 <div class="card">
   <form method=post>
     <input type=hidden name=act value=setpoint>
     Setpoint: <input type=number name=value step=0.5 min=5 max=40 value="%(sp)s">
     <button>Set</button>
   </form>
 </div>
 <div class="card">
   <form method=post>
     <input type=hidden name=act value=mode>
     Mode: <select name=value>%(mode_opts)s</select> <button>Apply</button>
   </form>
 </div>
</div>
<h3>Recent events</h3>
<div class="evt">%(events)s</div>
<p style="color:#666">log: hvac_log.csv &middot; auto-refresh 5s</p>
</body></html>"""


def render(st):
    def cls(on):
        return "on" if on else "off"
    modes = ["off", "heat", "cool", "auto"]
    mode_opts = "".join(
        f'<option value="{m}" {"selected" if st["mode"]==m else ""}>{m}</option>'
        for m in modes)
    return PAGE % {
        "temp": st["temp"], "min_t": st["min_temp"], "max_t": st["max_temp"],
        "sp": st["setpoint"],
        "ac_txt": "ON" if st["ac_on"] else "OFF",
        "fan_txt": "ON" if st["fan_on"] else "OFF",
        "heat_txt": "ON" if st["heater_on"] else "OFF",
        "ac_cls": cls(st["ac_on"]), "fan_cls": cls(st["fan_on"]),
        "heat_cls": cls(st["heater_on"]),
        "ac_next": "off" if st["ac_on"] else "on",
        "fan_next": "off" if st["fan_on"] else "on",
        "heat_next": "off" if st["heater_on"] else "on",
        "mode_opts": mode_opts,
        "events": "\n".join(st["events"][-10:]) or "(none)",
    }


class Handler(BaseHTTPRequestHandler):
    ctrl = None

    def _html(self, body, code=200):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            data = json.dumps(self.ctrl.status()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif path in ("/", "/index.html"):
            self._html(render(self.ctrl.status()))
        else:
            self._html("<h1>404</h1>", 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode())
        act = form.get("act", [""])[0]
        try:
            if act == "switch":
                self.ctrl.set_switch(form["name"][0], form["on"][0] == "on")
            elif act == "setpoint":
                self.ctrl.set_setpoint(form["value"][0])
            elif act == "mode":
                self.ctrl.set_mode(form["value"][0])
        except (ValueError, KeyError) as e:
            self._html(f"<h1>error</h1><p>{e}</p><a href=/>back</a>", 400)
            return
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass  # quiet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--sim", action="store_true", help="use simulated HVAC hardware")
    args = ap.parse_args()

    if args.sim:
        driver = SimDriver(start_temp=24.0, ambient=31.0)
    else:
        # TODO: swap in BacnetDriver for the .183 unit once green-lit:
        #   # driver = BacnetDriver('<CONTROLLER_IP>', <device_id>, {...points...})
        #   driver.connect()
        driver = SimDriver(start_temp=24.0, ambient=31.0)
        print("NOTE: no hardware driver configured — running simulation.")

    ctrl = HVACController(driver, mode="cool", setpoint=21.0, deadband=1.0)
    ctrl.ac_manual = True
    ctrl.heat_manual = True
    ctrl.start()
    Handler.ctrl = ctrl

    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"HVAC interface on http://localhost:{args.port}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ctrl.stop()


if __name__ == "__main__":
    main()
