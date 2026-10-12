"""
HVAC desktop interface — pure Python (Tkinter), runs as a window on this PC.

Run:  python3 gui.py
Uses the same HVACController core as the web version.
"""

import tkinter as tk
from tkinter import ttk

from controller import HVACController, SimDriver


class HVACGui:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.root = tk.Tk()
        self.root.title("HVAC Control")
        self.root.configure(bg="#111")
        self.root.geometry("560x520")

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TButton", padding=10, font=("Sans", 11))
        style.configure("TLabel", background="#111", foreground="#eee")

        # ---- display row: current / min / max / setpoint ----
        disp = tk.Frame(self.root, bg="#111")
        disp.pack(pady=12)
        self.temp_lbl = self._big(disp, "Current", 0)
        self.min_lbl = self._big(disp, "Min", 1)
        self.max_lbl = self._big(disp, "Max", 2)
        self.sp_lbl = self._big(disp, "Setpoint", 3)

        # ---- switches row ----
        sw = tk.Frame(self.root, bg="#111")
        sw.pack(pady=10)
        self.ac_btn = self._switch(sw, "AC", 0)
        self.fan_btn = self._switch(sw, "Fan", 1)
        self.heat_btn = self._switch(sw, "Heater", 2)

        # ---- setpoint + mode row ----
        ctl = tk.Frame(self.root, bg="#111")
        ctl.pack(pady=10)
        tk.Label(ctl, text="Setpoint °C", bg="#111", fg="#eee").grid(row=0, column=0, padx=6)
        self.sp_var = tk.StringVar(value=str(self.ctrl.setpoint))
        tk.Entry(ctl, textvariable=self.sp_var, width=6,
                 bg="#222", fg="#eee", insertbackground="#eee").grid(row=0, column=1)
        ttk.Button(ctl, text="Set", command=self.apply_setpoint).grid(row=0, column=2, padx=6)

        tk.Label(ctl, text="Mode", bg="#111", fg="#eee").grid(row=0, column=3, padx=6)
        self.mode_var = tk.StringVar(value=self.ctrl.mode)
        ttk.Combobox(ctl, textvariable=self.mode_var, width=7, state="readonly",
                     values=["off", "heat", "cool", "auto"]).grid(row=0, column=4)
        ttk.Button(ctl, text="Apply", command=self.apply_mode).grid(row=0, column=5, padx=6)

        # ---- events feed ----
        tk.Label(self.root, text="Recent events", bg="#111", fg="#888").pack(anchor="w", padx=14)
        self.evt = tk.Text(self.root, height=10, bg="#1c1c1c", fg="#9a9",
                           font=("Monospace", 9), relief="flat")
        self.evt.pack(fill="both", expand=True, padx=14, pady=(2, 10))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()

    def _big(self, parent, title, col):
        f = tk.Frame(parent, bg="#1c1c1c", highlightbackground="#333",
                     highlightthickness=1)
        f.grid(row=0, column=col, padx=6)
        tk.Label(f, text=title, bg="#1c1c1c", fg="#888").pack()
        lbl = tk.Label(f, text="--", bg="#1c1c1c", fg="#eee",
                       font=("Sans", 22, "bold"))
        lbl.pack(padx=12, pady=4)
        return lbl

    def _switch(self, parent, name, col):
        f = tk.Frame(parent, bg="#1c1c1c", highlightbackground="#333",
                     highlightthickness=1)
        f.grid(row=0, column=col, padx=6)
        tk.Label(f, text=name, bg="#1c1c1c", fg="#eee").pack(pady=(6, 0))
        state = tk.Label(f, text="", bg="#1c1c1c", fg="#888", font=("Sans", 12, "bold"))
        state.pack()
        key = {"AC": "ac", "Fan": "fan", "Heater": "heater"}[name]
        btn = ttk.Button(f, text="Toggle", width=10,
                         command=lambda k=key: self.toggle(k))
        btn.pack(pady=6)
        f.state_lbl = state
        return f

    def toggle(self, name):
        self.ctrl.set_switch(name, "on" if not self.ctrl.get_switch(name) else "off")
        # manual override semantics: toggling AC/heater re-enables them
        if name == "ac":
            self.ctrl.ac_manual = True
        if name == "heater":
            self.ctrl.heat_manual = True

    def apply_setpoint(self):
        try:
            self.ctrl.set_setpoint(self.sp_var.get())
        except ValueError as e:
            self.evt.insert("1.0", f"ERROR: {e}\n")

    def apply_mode(self):
        self.ctrl.set_mode(self.mode_var.get())

    def refresh(self):
        st = self.ctrl.status()
        self.temp_lbl.config(text=f"{st['temp']:.1f}")
        self.min_lbl.config(text=f"{st['min_temp']:.1f}")
        self.max_lbl.config(text=f"{st['max_temp']:.1f}")
        self.sp_lbl.config(text=f"{st['setpoint']:.1f}")
        for name, frame in (("ac", self.ac_btn), ("fan", self.fan_btn),
                            ("heater", self.heat_btn)):
            on = st[name + "_on"]
            frame.state_lbl.config(text="ON" if on else "OFF",
                                   fg="#6f6" if on else "#666")
            frame.config(highlightbackground="#2a2" if on else "#333")
        self.evt.delete("1.0", "end")
        self.evt.insert("1.0", "\n".join(st["events"][-12:]))
        self.root.after(1000, self.refresh)

    def on_close(self):
        self.ctrl.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    driver = SimDriver(start_temp=24.0, ambient=31.0)
    ctrl = HVACController(driver, mode="cool", setpoint=21.0, deadband=1.0)
    ctrl.ac_manual = True
    ctrl.heat_manual = True
    ctrl.start()
    HVACGui(ctrl).run()


if __name__ == "__main__":
    main()
