#!/usr/bin/env python3
# --------------------------------------------------------------
# SDV Full Demo – Theory + Hands‑on Playground (single file)
# --------------------------------------------------------------
# Features:
#   • Overview & definition of SDV
#   • Developer Playground (HPC, Zonal, OS/MW, SOA, Adaptive‑AUTOSAR,
#     OTA, Cloud/Edge, Security)
#   • V&V Engineer page (unit tests, shift‑left)
#   • SIL & Virtualisation demo (multiprocessing)
#   • Infotainment + OTA (play‑store, app icons, version bump)
#   • ADAS page (lane‑departure, collision‑warning)
#   • Inside‑view of the car (interior SVG)
#   • Architecture Evolution diagram (UNO → DUO → Ethernet‑TSN → Service‑Based)
#   • Leaderboard & car‑theme page
#   • Secure Door‑Lock System page (automotive‑grade HW,
#     board‑images, playground controls)
#   • **Tire Pressure Monitoring System (TPMS)** page
# --------------------------------------------------------------
# Run:   streamlit run SDV_full_demo.py
# --------------------------------------------------------------

import unittest                      # global import for the V&V page
import io                            # capture unittest output
import os, json, time, hashlib, random, multiprocessing as mp
import numpy as np, pandas as pd, streamlit as st
from datetime import datetime, timedelta
from graphviz import Source          # for flow‑charts

# ------------------------------------------------------------------
# 0️⃣  Global constants & defaults
# ------------------------------------------------------------------
STATE_FILE      = "sdv_state.json"
MOCK_MQTT_FILE  = "mock_mqtt_latest.json"

DEFAULT_APPS = [
    {"id":"nav","name":"Navigation","version":"1.0","icon":"🧭",
     "description":"Maps, routing, and POI"},
    {"id":"media","name":"Media Player","version":"1.2","icon":"🎵",
     "description":"Audio & video playback"},
]

STORE_APPS = [
    {"id":"eco_drive","name":"EcoDrive","version":"1.0","icon":"🌱",
     "description":"Optimizes energy usage"},
    {"id":"predict_batt","name":"Battery","version":"0.9","icon":"🔋",
     "description":"Battery analytics"},
    {"id":"trip_logger","name":"TripLog","version":"0.6","icon":"🧾",
     "description":"Records trips"},
    {"id":"weather","name":"WeatherNow","version":"1.0","icon":"☁️",
     "description":"Local weather"},
]

# ------------------------------------------------------------------
# 1️⃣  Persistent state handling
# ------------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    # fresh default state
    state = {
        "installed_apps": DEFAULT_APPS.copy(),
        "created_at": datetime.utcnow().isoformat(),
        "missions": {f"m{i}": False for i in range(1, 10)},
        "badges": {
            "eco_champion": False, "ota_expert": False,
            "adas_specialist": False, "battery_guru": False,
            "drive_master": False, "data_analyst": False,
            "fleet_engineer": False,
        },
        "car_theme": "#2b4b6f",
        # --------------------------------------------------------------
        # Door‑Lock subsystem
        # --------------------------------------------------------------
        "door_lock": {
            "door_state": "LOCKED",
            "twin_state": "LOCKED",
            "firmware":    "v1.0.0",
            "log":         [],
            "network_up": True,
        },
        # --------------------------------------------------------------
        # TPMS (Tire Pressure Monitoring System)
        # --------------------------------------------------------------
        "tpms": {
            "tires": {
                "fl": {"pressure": 32.0, "temp": 35.0, "battery": 98, "health": 92},
                "fr": {"pressure": 33.0, "temp": 34.0, "battery": 97, "health": 89},
                "rl": {"pressure": 31.0, "temp": 36.0, "battery": 95, "health": 78},
                "rr": {"pressure": 32.0, "temp": 35.0, "battery": 96, "health": 85},
            },
            "thresholds": {
                "low": 28,
                "high": 38,
                "target": 32,
                "temp_warning": 55,
            },
            "firmware": "v2.1.4",
            "latest_firmware": "v2.2.0",
            "network_up": True,
            "cloud_synced": True,
            "log": [],
            "alerts": [],
            "history": {
                "fl": [], "fr": [], "rl": [], "rr": []
            },
            "simulation_running": True,
        },
        # --------------------------------------------------------------
        # OTA Firmware Update System stub
        # --------------------------------------------------------------
        "ota_project": {
            "firmware_version": "v1.0.0",
            "signature": "",
            "jobs": [],
            "device_firmware": "v1.0.0",
            "device_status": "Idle",
        },
    }
    save_state(state)
    return state

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ------------------------------------------------------------------
# 2️⃣  Application manager (install / uninstall / OTA)
# ------------------------------------------------------------------
class ApplicationManager:
    def __init__(self, state=None):
        self.state = state or load_state()

    def list_apps(self):
        return self.state.get("installed_apps", [])

    def install_app(self, app):
        ids = {a["id"] for a in self.list_apps()}
        if app["id"] in ids:
            return False, "already installed"
        self.state.setdefault("installed_apps", []).append(app.copy())
        save_state(self.state)
        return True, "installed"

    def uninstall_app(self, app_id):
        apps = self.list_apps()
        new = [a for a in apps if a["id"] != app_id]
        if len(new) == len(apps):
            return False, "not found"
        self.state["installed_apps"] = new
        save_state(self.state)
        return True, "uninstalled"

    def update_app_version(self, app_id, new_version):
        for a in self.state.setdefault("installed_apps", []):
            if a["id"] == app_id:
                a["version"] = new_version
                save_state(self.state)
                return True
        return False

# ------------------------------------------------------------------
# 3️⃣  Telemetry source & predictive maintenance
# ------------------------------------------------------------------
class TelemetrySource:
    def simulate(self, hours=48, freq_minutes=15, seed=None):
        if seed is not None:
            np.random.seed(int(seed))
        periods = max(2, int(hours * 60 / freq_minutes))
        now = datetime.now()
        ts = [now - timedelta(minutes=freq_minutes * i) for i in reversed(range(periods))]

        base_voltage = 400.0
        drift = np.linspace(0, -5, periods)
        noise_v = np.random.normal(0, 0.2, periods)

        temp_base = 30.0
        temp_trend = np.linspace(0, 8, periods) * (np.random.rand() * 1.0)
        temp_noise = np.random.normal(0, 0.6, periods)

        current = np.clip(np.random.normal(5, 2, periods), -50, 100)
        soc = np.clip(100 - np.cumsum(np.abs(current)) * 0.001, 10, 100)
        cycles = np.clip((np.cumsum(np.abs(current)) / 1000).astype(int), 0, 200)

        voltage = base_voltage + drift + noise_v - cycles * 0.01
        temperature = temp_base + temp_trend + temp_noise + cycles * 0.02

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(ts),
            "voltage": voltage,
            "current": current,
            "temperature": temperature,
            "soc": soc,
            "cycles": cycles,
        })
        return df

    def read_can_csv(self, fileobj):
        df = pd.read_csv(fileobj)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def start_mock_mqtt_publish(self):
        df = self.simulate(hours=6, freq_minutes=5, seed=99)
        with open(MOCK_MQTT_FILE, "w") as f:
            json.dump({"latest": df.tail(20).to_dict(orient="records")}, f, default=str)

    def read_mock_mqtt_latest(self):
        if not os.path.exists(MOCK_MQTT_FILE):
            return pd.DataFrame()
        with open(MOCK_MQTT_FILE) as f:
            j = json.load(f)
        df = pd.DataFrame(j.get("latest", []))
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

class PredictiveMaintenance:
    def compute_risk_score(self, df):
        if df is None or df.empty:
            return None, {}
        recent = df.tail(12)
        times = (recent["timestamp"].astype("int64") // 1_000_000_000).values
        volts = recent["voltage"].values
        dt = (times[-1] - times[0]) / 3600.0 if len(times) >= 2 else 1.0
        slope = (volts[-1] - volts[0]) / dt
        voltage_drop_rate = -slope if slope < 0 else 0.0
        temp_mean = float(recent["temperature"].mean())
        cycles = int(recent["cycles"].max())

        v_score = min(voltage_drop_rate * 40.0, 40.0)
        t_score = min(max((temp_mean - 25.0) / (60.0 - 25.0) * 35.0, 35.0))
        t_score = max(t_score, 0.0)
        c_score = min(cycles / 200.0 * 25.0, 25.0)

        risk = min(max(v_score + t_score + c_score, 0.0), 100.0)
        explanation = {
            "voltage_drop_rate_v_per_hr": round(float(voltage_drop_rate), 4),
            "temp_mean": round(float(temp_mean), 2),
            "cycles": cycles,
            "components": {
                "v_score": round(float(v_score), 2),
                "t_score": round(float(t_score), 2),
                "c_score": round(float(c_score), 2),
            },
        }
        return int(round(risk)), explanation

# ------------------------------------------------------------------
# 4️⃣  Drive‑step simulation (core physics)
# ------------------------------------------------------------------
def simulate_drive_step(state, throttle_pct=0.0, brake_pct=0.0,
                       dt_seconds=1.0, mode="Normal"):
    s = state.setdefault("drive", {})
    speed = s.get("speed", 0.0)
    soc = s.get("soc", 95.0)
    temp = s.get("temperature", 30.0)
    cycles = s.get("cycles", 0)

    accel = (throttle_pct / 100.0) * 3.5
    decel = (brake_pct / 100.0) * 6.0 + 0.1

    mode = mode.capitalize()
    if mode == "Eco":
        accel *= 0.7; cur_factor = 0.7; regen_factor = 1.1
    elif mode == "Sport":
        accel *= 1.4; cur_factor = 1.3; regen_factor = 0.9
    elif mode == "Snow":
        accel *= 0.6; cur_factor = 0.8; regen_factor = 1.0
    elif mode == "Regen":
        accel *= 0.9; cur_factor = 0.9; regen_factor = 1.4
    else:
        cur_factor = 1.0; regen_factor = 1.0

    speed_ms = speed / 3.6
    speed_ms = max(0.0, speed_ms + (accel - decel) * dt_seconds)
    speed = speed_ms * 3.6

    rpm = min(7000, 800 + (speed * 40) * (1 + throttle_pct / 100.0))
    base_current = (throttle_pct / 100.0) * 60.0 + max(0, speed / 20.0) * 2.0
    current = base_current * cur_factor

    soc_delta = (current * dt_seconds) * 0.0005
    if mode == "Regen" or (throttle_pct < 20 and brake_pct > 10):
        soc_delta *= (0.7 / regen_factor)

    soc = max(5.0, soc - soc_delta)
    temp = temp + (current * 0.001 * dt_seconds) + (throttle_pct / 100.0) * 0.01
    cycles = min(1000, cycles + int(abs(current) * dt_seconds / 100.0))

    ts = datetime.now()
    row = {"timestamp": ts.isoformat(),
           "speed": round(float(speed), 2),
           "rpm": int(rpm),
           "current": round(float(current), 3),
           "temperature": round(float(temp), 2),
           "soc": round(float(soc), 3),
           "cycles": int(cycles),
           "throttle": float(throttle_pct),
           "brake": float(brake_pct),
           "mode": mode}
    s.update({"speed": speed, "soc": soc, "temperature": temp,
              "cycles": cycles, "mode": mode})

    log = state.setdefault("drive_log", [])
    log.append(row)
    if len(log) > 2000:
        del log[:len(log) - 2000]
    return row

# ------------------------------------------------------------------
# 5️⃣  ECU snapshot (derived from drive state)
# ------------------------------------------------------------------
def compute_ecu_snapshot():
    drive = st.session_state.get(
        "drive",
        {"speed": 0.0, "soc": 95.0, "temperature": 30.0,
         "cycles": 0, "mode": "Normal"},
    )
    log = st.session_state.get("drive_log", [])
    speed = drive["speed"]
    mode = drive["mode"]
    idx = len(log)

    bcm = {"headlights_on": (speed < 5) or (idx % 20 >= 10),
           "doors_locked": idx % 7 != 0,
           "cabin_temp": 24 + max(0, (drive["temperature"] - 30) * 0.1)}
    
    cycles = drive["cycles"]; temp = drive["temperature"]
    soh = max(60.0, 100.0 - cycles * 0.02 - max(0, temp - 35) * 0.1)
    bms = {"soc": drive["soc"], "temp": temp, "cycles": cycles,
           "soh": soh,
           "status": "OK" if soh > 80 else ("Monitor" if soh > 70 else "Degraded")}
    
    tcu = {"network_status": "Online" if speed < 80 else "Offline",
           "signal_strength": max(1, 5 - int((abs(speed - 60) / 60) * 3)),
           "gps_fix": "3D" if speed > 1 else "2D/Static"}
    
    lane_offset = float(np.sin(idx / 15.0) * 0.4)
    adas = {"lane_offset": lane_offset,
            "lane_departure": abs(lane_offset) > 0.3,
            "obstacle_distance": max(5.0, 80.0 - speed * 0.5),
            "collision_warn": speed > 40.0 and max(5.0, 80.0 - speed * 0.5) < 20.0}
    return {"BCM": bcm, "BMS": bms, "TCU": tcu, "ADAS": adas,
            "meta": {"speed": speed, "mode": mode}}

# ------------------------------------------------------------------
# 6️⃣  SVG assets
# ------------------------------------------------------------------
CAR_SVG_TEMPLATE = """
<svg xmlns='http://www.w3.org/2000/svg' width='420' height='240' viewBox='0 0 420 240'>
  <defs>
    <filter id="s" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect rx="18" ry="18" x="10" y="30" width="400" height="180" fill='#f3f4f6'/>
  <g transform="translate(30,40)">
    <rect x="25" y="30" rx="18" ry="18" width="320" height="110" fill='{screen_color}' filter='url(#s)'/>
    <rect x="45" y="10" rx="10" ry="10" width="280" height="40" fill='#1f3a56'/>
    <rect x="70" y="25" width="100" height="30" rx='6' ry='6' fill='#cbe3ff' opacity='0.9'/>
    <rect x='190' y='25' width='80' height='30' rx='6' ry='6' fill='#cbe3ff' opacity='0.9'/>
    <circle cx='80' cy='150' r='18' fill='#0f1724'/>
    <circle cx='280' cy='150' r='18' fill='#0f1724'/>
  </g>
  <text x='20' y='18' font-family='sans-serif' font-size='14' fill='#0f1724'>SDV — Demo Vehicle (top view)</text>
</svg>
"""

def get_car_svg(color: str = "#2b4b6f") -> str:
    return CAR_SVG_TEMPLATE.format(screen_color=color)

INFOTAINMENT_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' width='320' height='200' viewBox='0 0 320 200'>
  <rect rx='12' ry='12' x='0' y='0' width='320' height='200' fill='#0f1724'/>
  <rect x='12' y='12' width='296' height='176' rx='8' fill='#ffffff'/>
  <rect x='22' y='22' width='276' height='40' rx='6' fill='#e6eef8'/>
  <text x='30' y='48' font-family='sans-serif' font-size='14' fill='#0f1724'>Infotainment</text>
  <g id='grid' transform='translate(22,70)'>
    <rect x='0'   y='0'  width='80' height='60' rx='8' fill='#f8fafc' stroke='#e2e8f0'/>
    <rect x='98'  y='0'  width='80' height='60' rx='8' fill='#f8fafc' stroke='#e2e8f0'/>
    <rect x='196' y='0'  width='80' height='60' rx='8' fill='#f8fafc' stroke='#e2e8f0'/>
    <rect x='0'   y='76' width='80' height='60' rx='8' fill='#f8fafc' stroke='#e2e8f0'/>
    <rect x='98'  y='76' width='80' height='60' rx='8' fill='#f8fafc' stroke='#e2e8f0'/>
    <rect x='196' y='76' width='80' height='60' rx='8' fill='#f8fafc' stroke='#e2e8f0'/>
  </g>
</svg>
"""

INTERIOR_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' width='420' height='300' viewBox='0 0 420 300'>
  <rect x='10' y='10' width='400' height='280' rx='15' ry='15' fill='#2b4b6f'/>
  <rect x='30' y='30' width='360' height='240' fill='#1f3a56'/>
  <circle cx='210' cy='150' r='30' fill='#cbe3ff'/>
  <line x1='210' y1='120' x2='210' y2='180' stroke='#0f1724' stroke-width='4'/>
  <line x1='180' y1='150' x2='240' y2='150' stroke='#0f1724' stroke-width='4'/>
  <circle cx='100' cy='200' r='50' fill='#cbe3ff'/>
  <text x='100' y='210' font-family='sans-serif' font-size='16' fill='#0f1724' text-anchor='middle'>SPD</text>
  <rect x='260' y='120' width='120' height='80' fill='#ffffff'/>
  <text x='320' y='155' font-family='sans-serif' font-size='12' fill='#0f1724' text-anchor='middle'>Screen</text>
</svg>
"""

def svg_to_html(svg_str, width=None):
    style = f"width:{width}px;" if width else ""
    return f"<div style='display:block; {style}'>{svg_str}</div>"

# ------------------------------------------------------------------
# 7️⃣  Flow‑chart helpers
# ------------------------------------------------------------------
def draw_sdv_stack():
    dot = """
    digraph Comparison {
        rankdir=LR;
        node [shape=box style=filled fontname="Helvetica" fontsize=10];
        edge [fontname="Helvetica" fontsize=9];
        subgraph cluster_trad {
            label="Traditional Vehicle";
            color=lightgrey;
            Sensors  [label="Sensors\\n(Cameras, Radar, LiDAR, GPS)" fillcolor="#FFEBCC"];
            ECUs     [label="Domain‑specific ECUs\\n(BCM, BMS, TCU, ADAS, …)" fillcolor="#FFE4E1"];
            CANBus   [label="CAN/LIN Bus\\n(Point‑to‑point wiring)" fillcolor="#E0F7FA"];
            Firmware [label="Static firmware per ECU\\n(Flashed via dealer tool)" fillcolor="#F3E5F5"];
            Sensors -> ECUs [label="raw signals"];
            ECUs -> CANBus [label="control & diagnostics"];
            CANBus -> ECUs [label="commands"];
            ECUs -> Firmware [label="update (rare)"];
        }
        subgraph cluster_sdv {
            label="Software‑Defined Vehicle";
            color=lightgrey;
            Sensors2   [label="Sensors\\n(Cameras, Radar, LiDAR, GPS)" fillcolor="#FFEBCC"];
            Compute    [label="Central Compute\\n(HPC, GPU/AI accelerator)" fillcolor="#FFE4E1"];
            Ethernet   [label="High‑speed Ethernet\\n(10 GbE, TSN, 5G)" fillcolor="#E0F7FA"];
            Applications [label="Application Layer\\n(Play Store, Infotainment, OTA, Services)" fillcolor="#E8F5E9"];
            Cloud      [label="Cloud Backend\\n(Data Lake, Model Training, Fleet Management)" fillcolor="#F3E5F5"];
            Sensors2 -> Compute [label="raw data"];
            Compute -> Ethernet [label="processed streams"];
            Ethernet -> Applications [label="network services"];
            Applications -> Cloud [label="telemetry / OTA"];
            Cloud -> Sensors2 [label="updates & config"];
        }
        edge [style=invis];
        Sensors -> Sensors2;
    }
    """
    return Source(dot)

def draw_arch_evolution():
    dot = """
    digraph Arch {
        rankdir=TB;
        node [shape=box style=filled fontname="Helvetica" fontsize=10];
        UNO   [label="UNO (single‑core MCU)\\nCAN/LIN" fillcolor="#FFEBCC"];
        DUO   [label="DUO (dual‑core)\\nCAN + FlexRay" fillcolor="#FFE4E1"];
        ETH   [label="Ethernet (10 GbE)\\nTSN" fillcolor="#E0F7FA"];
        SB    [label="Service‑Based\\nDDS/SOMEIP" fillcolor="#E8F5E9"];
        Cloud [label="Cloud\\nOTA, fleet analytics" fillcolor="#F3E5F5"];
        UNO -> DUO -> ETH -> SB -> Cloud;
    }
    """
    return Source(dot)

def draw_door_lock_arch():
    dot = """
    digraph DoorLock {
        rankdir=LR;
        node [shape=box style=filled fontname="Helvetica" fontsize=10];
        EdgeECU [label="Edge ECU\\n(NXP S32K‑144 EVB)\\nSensors + Actuator" fillcolor="#FFE4E1"];
        TCU    [label="TCU (NVIDIA Drive Orin)\\nWi‑Fi, CAN, Auth" fillcolor="#E0F7FA"];
        Cloud  [label="Cloud Server\\nDocker micro‑services" fillcolor="#E8F5E9"];
        Actor  [label="Actor (User)\\nWeb/Mobile UI" fillcolor="#FFEBCC"];
        EdgeECU -> TCU   [label="CAN"];
        TCU    -> Cloud [label="Wi‑Fi / MQTT / HTTPS"];
        Cloud  -> Actor [label="REST / MQTT"];
        Actor  -> Cloud [label="Command"];
        Cloud  -> TCU   [label="Control Msg"];
        TCU    -> EdgeECU [label="CAN Cmd"];
    }
    """
    return Source(dot)

def draw_tpms_arch():
    """TPMS system architecture diagram."""
    dot = """
    digraph TPMS {
        rankdir=LR;
        node [shape=box style=filled fontname="Helvetica" fontsize=10];
        
        subgraph cluster_sensors {
            label="Tire Sensors (RF 433MHz / BLE)";
            color=lightgrey;
            FL [label="Front Left\\nSensor" fillcolor="#FFEBCC"];
            FR [label="Front Right\\nSensor" fillcolor="#FFEBCC"];
            RL [label="Rear Left\\nSensor" fillcolor="#FFEBCC"];
            RR [label="Rear Right\\nSensor" fillcolor="#FFEBCC"];
        }
        
        Receiver [label="RF Receiver\\n(Antenna Module)" fillcolor="#E0F7FA"];
        EdgeECU [label="Edge ECU\\n(NXP S32K‑144)\\nPressure Processing" fillcolor="#FFE4E1"];
        CAN [label="CAN Bus" fillcolor="#E8F5E9"];
        TCU [label="TCU Gateway\\n(RPi / Orin)\\nWi‑Fi, MQTT" fillcolor="#E0F7FA"];
        Cloud [label="Cloud Platform\\nDigital Twin\\nAnalytics" fillcolor="#F3E5F5"];
        Dashboard [label="Driver Dashboard\\n+ Mobile App" fillcolor="#FFEBCC"];
        
        FL -> Receiver [label="RF"];
        FR -> Receiver [label="RF"];
        RL -> Receiver [label="RF"];
        RR -> Receiver [label="RF"];
        Receiver -> EdgeECU [label="SPI"];
        EdgeECU -> CAN [label="CAN FD"];
        CAN -> TCU [label=""];
        TCU -> Cloud [label="MQTT/TLS"];
        Cloud -> Dashboard [label="REST/WS"];
        Cloud -> TCU [label="OTA"];
    }
    """
    return Source(dot)

# ------------------------------------------------------------------
# 8️⃣  OTA helper (progress bar)
# ------------------------------------------------------------------
def simulate_ota_update(app_mgr, app_id, seconds=2.0):
    apps = app_mgr.list_apps()
    app = next((a for a in apps if a.get("id") == app_id), None)
    if app is None:
        return False, "app not installed"

    old_version = str(app.get("version", "1.0"))
    try:
        parts = [int(p) for p in old_version.split(".")]
        if len(parts) == 1:
            parts = [parts[0], 1]
        else:
            parts[-1] += 1
        new_version = ".".join(str(p) for p in parts)
    except Exception:
        new_version = old_version + ".1"

    pb = st.progress(0)
    status = st.empty()
    for i in range(0, 101, 5):
        pb.progress(i)
        status.text(f"Downloading… {i}%")
        time.sleep(seconds / 20.0)
    status.text("Installing…")
    time.sleep(0.4)

    ok = app_mgr.update_app_version(app_id, new_version)
    if ok:
        status.success(f"✅ Updated to {new_version}")
        pb.progress(100)
        time.sleep(0.4)
        return True, new_version
    else:
        status.error("Update failed")
        return False, "failed"

# ------------------------------------------------------------------
# 9️⃣  Global ECU process (picklable – used by SIL demo)
# ------------------------------------------------------------------
def ecu_process(q_cmd: mp.Queue, q_resp: mp.Queue):
    speed = 0.0
    while True:
        cmd = q_cmd.get()
        if cmd == "STOP":
            break
        throttle = cmd.get("throttle", 0.0)
        brake    = cmd.get("brake", 0.0)
        accel = (throttle / 100.0) * 3.5
        decel = (brake / 100.0) * 6.0 + 0.1
        speed_ms = speed / 3.6
        speed_ms = max(0.0, speed_ms + (accel - decel) * 0.1)
        speed = speed_ms * 3.6
        q_resp.put({"speed": round(speed, 2)})

# ------------------------------------------------------------------
# 10️⃣  SIL & Virtualisation demo
# ------------------------------------------------------------------
def sil_virtualization_demo():
    st.header("🔄 SIL & Virtualisation Demo")
    st.info(
        """
        *Software‑in‑the‑Loop (SIL)* – the host runs the **vehicle model**.  
        *Hardware‑in‑the‑Loop (HIL)* – an ECU runs in a **separate process**, communicating via queues.
        """
    )
    if "ecu_proc" not in st.session_state:
        cmd_q  = mp.Queue()
        resp_q = mp.Queue()
        proc = mp.Process(target=ecu_process, args=(cmd_q, resp_q), daemon=True)
        proc.start()
        st.session_state["ecu_proc"] = proc
        st.session_state["cmd_q"]   = cmd_q
        st.session_state["resp_q"]  = resp_q

    throttle = st.slider("Throttle (%)", 0, 100, 0, key="sil_throttle")
    brake    = st.slider("Brake (%)",    0, 100, 0, key="sil_brake")
    if st.button("Send command to ECU (SIL)"):
        st.session_state["cmd_q"].put({"throttle": throttle, "brake": brake})
        try:
            resp = st.session_state["resp_q"].get(timeout=1.0)
            st.success(f"ECU reported **speed = {resp['speed']} km/h**")
        except Exception:
            st.error("No response from ECU (timeout)")

    if st.button("Terminate ECU process (debug)"):
        st.session_state["cmd_q"].put("STOP")
        st.session_state["ecu_proc"].join()
        st.success("ECU process stopped – next visit will restart it.")
        for k in ["ecu_proc", "cmd_q", "resp_q"]:
            if k in st.session_state:
                del st.session_state[k]

# ------------------------------------------------------------------
# 11️⃣  Developer Playground
# ------------------------------------------------------------------
def developer_playground():
    st.header("👨‍💻 Developer Playground – SDV Core Concepts")
    tabs = st.tabs([
        "💻 HPC", "🧩 Zonal Architecture",
        "🖥️ OS / Middleware", "🛎️ SOA",
        "🔧 Adaptive AUTOSAR", "🚀 OTA", "☁️ Cloud / Edge",
        "🔐 Security & Signing"
    ])

    with tabs[0]:
        st.subheader("💻 High‑Performance Computing (HPC)")
        n = st.slider("Workload size (million ints)", 10, 200, 50, step=10, key="hpc_n")
        if st.button("Run benchmark"):
            start = time.perf_counter()
            total = sum(range(n * 1_000_000))
            elapsed = time.perf_counter() - start
            st.success(f"✅ Sum = {total:,}")
            st.info(f"⏱️ Execution time: **{elapsed:.3f}s**")

    with tabs[1]:
        st.subheader("🧩 Zonal Architecture – wiring reduction")
        ecus = st.slider("Original ECUs", 5, 200, 30, step=5, key="zonal_ecus")
        zones = st.slider("Number of zones", 1, 10, 2, key="zonal_z")
        orig_len = ecus * 1.0
        per_zone_len = (ecus / zones) ** 0.5
        new_len = zones * per_zone_len
        reduction = 100 * (orig_len - new_len) / orig_len
        col_a, col_b = st.columns(2)
        col_a.metric("Original wiring (m)", f"{orig_len:.1f}")
        col_b.metric("Zonal wiring (m)", f"{new_len:.1f}")
        st.success(f"🟢 Wiring reduced by **{reduction:.1f}%**")

    with tabs[2]:
        st.subheader("🖥️ OS & Middleware (light‑weight RTOS style)")
        code = """\
tasks = []
def register_task(name, period_ms, func):
    tasks.append(dict(name=name, period=period_ms/1000.0, fn=func, next=0.0))

def run_scheduler(runtime_s):
    t = 0.0
    while t < runtime_s:
        for task in tasks:
            if t >= task['next']:
                task['fn']()
                task['next'] = t + task['period']
        t += 0.001   # 1 ms tick
"""
        st.code(code, language="python")

    with tabs[3]:
        st.subheader("🛎️ Service‑Oriented Architecture (SOA) demo")
        class ServiceRegistry:
            def __init__(self):
                self._services = {}
            def register(self, name, func):
                self._services[name] = func
            def call(self, name, *a, **kw):
                if name not in self._services:
                    raise KeyError(f"Service {name!r} missing")
                return self._services[name](*a, **kw)

        if "svc_reg" not in st.session_state:
            reg = ServiceRegistry()
            def seat_heater(profile: str) -> dict:
                return {"status": "ok", "profile": profile}
            reg.register("seat_heater", seat_heater)
            st.session_state["svc_reg"] = reg

        profile = st.selectbox("Select seat‑heater profile", ["eco","comfort","sport"])
        if st.button("Call seat‑heater service"):
            try:
                resp = st.session_state["svc_reg"].call("seat_heater", profile)
                st.success("✅ Service responded")
                st.json(resp)
            except Exception as e:
                st.error(f"❌ {e}")

    with tabs[4]:
        st.subheader("🔧 Adaptive AUTOSAR (light‑weight mock)")
        class AdaptiveRuntime:
            def __init__(self):
                self.services = {}
            def register_service(self, name, handler):
                self.services[name] = handler
            def call(self, name, *a, **kw):
                if name not in self.services:
                    raise KeyError(f"Service {name!r} missing")
                return self.services[name](*a, **kw)

        if "ad_runtime" not in st.session_state:
            ar = AdaptiveRuntime()
            def get_vehicle_speed():
                drv = st.session_state.get("drive", {"speed":0.0})
                return {"speed_kmh": drv["speed"]}
            ar.register_service("VehicleSpeed", get_vehicle_speed)
            st.session_state["ad_runtime"] = ar

        if st.button("Query Adaptive AUTOSAR VehicleSpeed service"):
            try:
                out = st.session_state["ad_runtime"].call("VehicleSpeed")
                st.json(out)
            except Exception as e:
                st.error(f"❌ {e}")

    with tabs[5]:
        st.subheader("🚀 OTA – Over‑the‑Air update")
        installed = app_mgr.list_apps()
        if not installed:
            st.info("Install an app from the Play Store first.")
        else:
            choice = st.selectbox(
                "Pick an installed app to OTA‑update",
                [f"{a['name']} ({a['id']}) – v{a['version']}" for a in installed],
                key="ota_demo_select")
            app_id = choice.split("(")[1].split(")")[0]
            if st.button("Start OTA (demo)"):
                ok, info = simulate_ota_update(app_mgr, app_id, seconds=1.8)
                if ok:
                    st.success(f"✅ Updated to {info}")
                else:
                    st.error(info)

    with tabs[6]:
        st.subheader("☁️ Cloud & Edge Computing Integration")
        if st.button("Upload latest drive telemetry to cloud (simulated)"):
            telemetry = pd.DataFrame(st.session_state.get("drive_log", []))
            if telemetry.empty:
                st.warning("No drive data yet.")
            else:
                state["cloud_telemetry"] = telemetry.to_dict("records")
                save_state(state)
                st.success(f"🚀 Uploaded {len(telemetry)} samples to simulated cloud")
        if st.button("Download latest AI model from cloud (simulated)"):
            model_ver = state.get("cloud_model_version", "1.0")
            parts = [int(p) for p in model_ver.split(".")]
            parts[-1] += 1
            new_ver = ".".join(str(p) for p in parts)
            state["cloud_model_version"] = new_ver
            save_state(state)
            st.success(f"⬇️ Downloaded AI model v{new_ver}")

    with tabs[7]:
        st.subheader("🔐 Security & Signing (RSA‑2048)")
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa, padding
            from cryptography.hazmat.primitives import hashes
            crypto_available = True
        except ImportError:
            crypto_available = False
            st.warning("Install `cryptography` package for this demo: `pip install cryptography`")
        
        if crypto_available:
            if "private_key" not in st.session_state:
                if st.button("Generate RSA‑2048 key pair"):
                    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                    st.session_state["private_key"] = private_key
                    st.session_state["public_key"] = private_key.public_key()
                    st.success("🔑 Key pair generated")
            else:
                msg = st.text_area("Message to sign", "SDV demo message")
                if st.button("Sign message"):
                    private_key = st.session_state["private_key"]
                    signature = private_key.sign(
                        msg.encode(),
                        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                     salt_length=padding.PSS.MAX_LENGTH),
                        hashes.SHA256())
                    st.session_state["signature"] = signature
                    st.success("✍️ Message signed")
                    st.code(signature.hex())
                if "signature" in st.session_state and st.button("Verify signature"):
                    public_key = st.session_state["public_key"]
                    try:
                        public_key.verify(
                            st.session_state["signature"],
                            msg.encode(),
                            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                        salt_length=padding.PSS.MAX_LENGTH),
                            hashes.SHA256())
                        st.success("✅ Signature VALID")
                    except Exception as e:
                        st.error(f"❌ Verification failed: {e}")

# ------------------------------------------------------------------
# 12️⃣  Overview / Theory page
# ------------------------------------------------------------------
def overview_page():
    st.header("🏠 Software‑Defined Vehicle (SDV) – Overview")
    st.markdown(
        """
        ### 📖 What is an SDV?
        A **Software‑Defined Vehicle** is a vehicle whose **functions are delivered as software services** that run on **high‑performance compute platforms** and are **delivered/updated over the air**.

        ### 🎯 Why do we need SDV?
        * **Reduced wiring & weight** – fewer ECUs → lighter vehicle.  
        * **Faster time‑to‑market** – OTA can deliver new features in weeks, not years.  
        * **Scalable compute** – one platform can host ADAS, infotainment, V2X, etc.  
        * **Continuous improvement** – AI models are updated from the cloud.
        """
    )
    st.subheader("📊 SDV Stack – visual overview")
    st.graphviz_chart(draw_sdv_stack())

# ------------------------------------------------------------------
# 13️⃣  V&V Engineer page
# ------------------------------------------------------------------
def vver_page():
    st.header("🔧 V&V Engineer – Verification & Validation")
    st.markdown(
        """
        **Verification** – "Are we building the system right?"  
        **Validation** – "Did we build the right system?"
        """
    )

    def square(x: int) -> int:
        return x * x

    class TestSquare(unittest.TestCase):
        def test_positive(self): self.assertEqual(square(3), 9)
        def test_zero(self):     self.assertEqual(square(0), 0)
        def test_negative(self): self.assertEqual(square(-4), 16)

    if st.button("Run V&V unit‑tests"):
        suite = unittest.TestLoader().loadTestsFromTestCase(TestSquare)
        buf = io.StringIO()
        runner = unittest.TextTestRunner(stream=buf, verbosity=2)
        result = runner.run(suite)
        st.code(buf.getvalue(), language="text")
        if result.wasSuccessful():
            st.success("✅ All tests passed")
        else:
            st.error("❌ Some tests failed")

# ------------------------------------------------------------------
# 14️⃣  ADAS page
# ------------------------------------------------------------------
def adas_page():
    st.header("🧭 ADAS – Driver Assistance Overview")
    ecu = compute_ecu_snapshot()
    adas = ecu["ADAS"]
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Lane offset (m)", f"{adas['lane_offset']:+.2f}")
        st.metric("Lane departure", "YES" if adas["lane_departure"] else "NO")
    with col2:
        st.metric("Obstacle distance (m)", f"{adas['obstacle_distance']:.1f}")
        st.metric("Collision warning", "⚠️" if adas["collision_warn"] else "OK")

# ------------------------------------------------------------------
# 15️⃣  Inside‑view of the car
# ------------------------------------------------------------------
def interior_view_page():
    st.header("🚗 Inside View – Car Interior")
    st.markdown(svg_to_html(INTERIOR_SVG, width=480), unsafe_allow_html=True)
    drv = st.session_state.get("drive", {"speed":0.0,"soc":95.0,"temperature":30.0,"mode":"Normal"})
    st.metric("Current speed (km/h)", f"{drv['speed']:.1f}")
    st.metric("Current mode", drv["mode"])

# ------------------------------------------------------------------
# 16️⃣  Infotainment & OTA page
# ------------------------------------------------------------------
def infotainment_ota_page():
    st.header("📱 Infotainment & OTA – App Store + In‑Vehicle UI")
    st.subheader("🛒 Play Store – install demo apps")
    cols = st.columns(3)
    installed_ids = {a["id"] for a in app_mgr.list_apps()}
    for i, app in enumerate(STORE_APPS):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div style="border:1px solid #e5e7eb; border-radius:10px; padding:8px; margin-bottom:8px; background:#fff;">
                  <div style="display:flex; align-items:center;">
                    <span style="font-size:1.4rem; margin-right:6px;">{app['icon']}</span>
                    <strong>{app['name']}</strong>
                  </div>
                  <p style="font-size:0.85rem; color:#555;">{app['description']}</p>
                  <small>v{app['version']}</small>
                </div>
                """, unsafe_allow_html=True)
            if app["id"] in installed_ids:
                st.button("Installed ✓", key=f"inf_inst_{app['id']}", disabled=True)
            else:
                if st.button("Install", key=f"inf_inst_{app['id']}"):
                    ok, msg = app_mgr.install_app(app)
                    if ok:
                        st.success(f"{app['name']} installed")
                        st.rerun()
                    else:
                        st.error(msg)

# ------------------------------------------------------------------
# 17️⃣  Predictive Maintenance page
# ------------------------------------------------------------------
def predictive_page():
    st.header("🔮 Predictive Maintenance – Battery health")
    source = st.selectbox("Telemetry source", ["Simulate","Load CSV","Mock MQTT","Driving Log"])
    df = None
    if source == "Simulate":
        hrs = st.slider("Hours", 6, 168, 48)
        freq = st.selectbox("Sample interval (min)", [5,15,30,60], index=1)
        seed = st.number_input("Seed", value=42)
        if st.button("Generate"):
            df = telemetry_source.simulate(hours=hrs, freq_minutes=freq, seed=int(seed))
            st.session_state["telemetry"] = df.to_dict("records")
            st.rerun()
    elif source == "Load CSV":
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded:
            df = telemetry_source.read_can_csv(uploaded)
            st.session_state["telemetry"] = df.to_dict("records")
            st.rerun()
    elif source == "Mock MQTT":
        if st.button("Fetch MQTT mock"):
            telemetry_source.start_mock_mqtt_publish()
            df = telemetry_source.read_mock_mqtt_latest()
            st.session_state["telemetry"] = df.to_dict("records")
            st.rerun()
    else:
        if st.session_state.get("drive_log"):
            dl = pd.DataFrame(st.session_state["drive_log"])
            dl["voltage"] = 350 + (dl["soc"]/100)*60 + np.random.normal(0,0.2,len(dl))
            df = dl[["timestamp","voltage","temperature","cycles"]]
        else:
            st.info("No drive log – run the Driving Dashboard first.")

    if df is not None and not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        st.subheader("Telemetry preview")
        st.dataframe(df.tail(10))
        score, expl = pm.compute_risk_score(df)
        st.success(f"🔋 Battery Risk Score: **{score}/100**")

# ------------------------------------------------------------------
# 18️⃣  Architecture Evolution diagram
# ------------------------------------------------------------------
def arch_evolution_page():
    st.header("🗺️ Architecture Evolution")
    st.graphviz_chart(draw_arch_evolution())

# ------------------------------------------------------------------
# 19️⃣  Leaderboard page
# ------------------------------------------------------------------
def leaderboard_page():
    st.header("🏆 Leaderboard & Car Theme")
    missions = state["missions"]
    badges   = state["badges"]
    missions_completed = sum(1 for v in missions.values() if v)
    total_missions = len(missions)
    badges_earned = sum(1 for v in badges.values() if v)
    total_badges = len(badges)
    points = missions_completed * 10 + badges_earned * 5
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Missions", f"{missions_completed}/{total_missions}")
    col2.metric("Badges",   f"{badges_earned}/{total_badges}")
    col3.metric("Points",   points)

# ------------------------------------------------------------------
# 20️⃣  Secure Door‑Lock System page
# ------------------------------------------------------------------
def door_lock_project_page():
    st.header("🔐 Secure Door‑Lock System – SDV Project")
    
    st.subheader("🚪 Use‑case")
    st.markdown(
        """
        Modern vehicles must let the owner **lock / unlock doors remotely**, while guaranteeing that 
        only authorised users can trigger the actuation and firmware cannot be tampered with.
        """
    )
    
    st.subheader("Architecture Overview")
    st.graphviz_chart(draw_door_lock_arch())
    
    dl_state = state["door_lock"]
    
    def add_log(src: str, action: str):
        entry = {"timestamp": datetime.now().strftime("%H:%M:%S"), "source": src, "action": action}
        dl_state["log"].append(entry)
        if len(dl_state["log"]) > 30:
            dl_state["log"] = dl_state["log"][-30:]
        save_state(state)
    
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("🚪 Physical Door (Edge ECU)")
        door_icon = "🔒" if dl_state["door_state"] == "LOCKED" else "🔓"
        st.markdown(f"### Status: {door_icon} **{dl_state['door_state']}**")
        
        if st.button("Toggle Door sensor"):
            new_state = "UNLOCKED" if dl_state["door_state"] == "LOCKED" else "LOCKED"
            dl_state["door_state"] = new_state
            dl_state["twin_state"] = new_state
            add_log("Edge‑ECU", f"Door {new_state}")
            st.rerun()
    
    with col_right:
        st.subheader("☁️ Cloud & Digital Twin")
        twin_icon = "🔒" if dl_state["twin_state"] == "LOCKED" else "🔓"
        st.markdown(f"### Twin: {twin_icon} **{dl_state['twin_state']}**")
        
        if dl_state["door_state"] != dl_state["twin_state"]:
            st.warning("⚠️ **Twin mismatch detected!**")
    
    if dl_state["log"]:
        st.subheader("📜 Event Log")
        log_df = pd.DataFrame(dl_state["log"])
        st.dataframe(log_df.iloc[::-1].reset_index(drop=True))

# ------------------------------------------------------------------
# 21️⃣  TPMS (Tire Pressure Monitoring System) Project Page
# ------------------------------------------------------------------
def tpms_project_page():
    """🛞 Tire Pressure Monitoring System – SDV Project"""
    st.header("🛞 Tire Pressure Monitoring System (TPMS)")
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .tire-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .tire-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 10px 0;
    }
    .tire-label {
        font-size: 0.9rem;
        opacity: 0.8;
    }
    .status-ok { color: #4ade80; }
    .status-warning { color: #fbbf24; }
    .status-danger { color: #f87171; }
    .sensor-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        margin: 20px 0;
    }
    .info-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize TPMS state if not exists
    if "tpms" not in state:
        state["tpms"] = {
            "tires": {
                "fl": {"pressure": 32.0, "temp": 35.0, "battery": 98, "health": 92},
                "fr": {"pressure": 33.0, "temp": 34.0, "battery": 97, "health": 89},
                "rl": {"pressure": 31.0, "temp": 36.0, "battery": 95, "health": 78},
                "rr": {"pressure": 32.0, "temp": 35.0, "battery": 96, "health": 85},
            },
            "thresholds": {"low": 28, "high": 38, "target": 32, "temp_warning": 55},
            "firmware": "v2.1.4",
            "latest_firmware": "v2.2.0",
            "network_up": True,
            "cloud_synced": True,
            "log": [],
            "simulation_running": True,
        }
        save_state(state)
    
    tpms = state["tpms"]
    
    def add_tpms_log(source: str, action: str):
        entry = {"timestamp": datetime.now().strftime("%H:%M:%S"), "source": source, "action": action}
        tpms["log"].append(entry)
        if len(tpms["log"]) > 50:
            tpms["log"] = tpms["log"][-50:]
        save_state(state)
    
    def get_pressure_status(pressure):
        if pressure < tpms["thresholds"]["low"]:
            return "danger", "🔴 LOW"
        elif pressure > tpms["thresholds"]["high"]:
            return "warning", "🟠 HIGH"
        else:
            return "ok", "🟢 OK"
    
    def get_temp_status(temp):
        if temp > tpms["thresholds"]["temp_warning"]:
            return "warning", "🌡️ HOT"
        return "ok", "🌡️ OK"
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", "📈 Analytics", "🏗️ Architecture", "⚙️ Settings & OTA", "📚 Documentation"
    ])
    
    # ============== TAB 1: DASHBOARD ==============
    with tab1:
        st.subheader("🚗 Vehicle Overview")
        
        # System status row
        status_cols = st.columns(4)
        with status_cols[0]:
            net_status = "🟢 Online" if tpms.get("network_up", True) else "🔴 Offline"
            st.metric("Network (TCU)", net_status)
        with status_cols[1]:
            sync_status = "🟢 Synced" if tpms.get("cloud_synced", True) else "🟡 Pending"
            st.metric("Cloud Sync", sync_status)
        with status_cols[2]:
            st.metric("Firmware", tpms.get("firmware", "v2.1.4"))
        with status_cols[3]:
            avg_battery = sum(t["battery"] for t in tpms["tires"].values()) / 4
            st.metric("Avg Battery", f"{avg_battery:.0f}%")
        
        st.markdown("---")
        
        # Tire pressure display - 2x2 grid
        st.subheader("🛞 Tire Status")
        
        tire_names = {"fl": "Front Left", "fr": "Front Right", "rl": "Rear Left", "rr": "Rear Right"}
        
        # Row 1: Front tires
        front_cols = st.columns(2)
        for i, (key, name) in enumerate([("fl", "Front Left"), ("fr", "Front Right")]):
            with front_cols[i]:
                tire = tpms["tires"][key]
                p_status, p_label = get_pressure_status(tire["pressure"])
                t_status, t_label = get_temp_status(tire["temp"])
                
                status_color = "#4ade80" if p_status == "ok" else ("#fbbf24" if p_status == "warning" else "#f87171")
                
                st.markdown(f"""
                <div class="tire-card" style="border: 3px solid {status_color};">
                    <div class="tire-label">{name}</div>
                    <div class="tire-value">{tire['pressure']:.1f} <span style="font-size:1rem;">PSI</span></div>
                    <div style="display:flex; justify-content:space-around; margin-top:10px;">
                        <span>{p_label}</span>
                        <span>{t_label} {tire['temp']:.0f}°C</span>
                    </div>
                    <div style="margin-top:10px; font-size:0.8rem; opacity:0.7;">
                        🔋 {tire['battery']}% | Health: {tire['health']}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Row 2: Rear tires
        rear_cols = st.columns(2)
        for i, (key, name) in enumerate([("rl", "Rear Left"), ("rr", "Rear Right")]):
            with rear_cols[i]:
                tire = tpms["tires"][key]
                p_status, p_label = get_pressure_status(tire["pressure"])
                t_status, t_label = get_temp_status(tire["temp"])
                
                status_color = "#4ade80" if p_status == "ok" else ("#fbbf24" if p_status == "warning" else "#f87171")
                
                st.markdown(f"""
                <div class="tire-card" style="border: 3px solid {status_color};">
                    <div class="tire-label">{name}</div>
                    <div class="tire-value">{tire['pressure']:.1f} <span style="font-size:1rem;">PSI</span></div>
                    <div style="display:flex; justify-content:space-around; margin-top:10px;">
                        <span>{p_label}</span>
                        <span>{t_label} {tire['temp']:.0f}°C</span>
                    </div>
                    <div style="margin-top:10px; font-size:0.8rem; opacity:0.7;">
                        🔋 {tire['battery']}% | Health: {tire['health']}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Simulation Controls
        st.subheader("🎮 Simulation Controls")
        sim_cols = st.columns(4)
        
        with sim_cols[0]:
            if st.button("🔴 Simulate Leak (FL)", use_container_width=True):
                tpms["tires"]["fl"]["pressure"] = 22.0
                add_tpms_log("Simulation", "Leak triggered on Front Left tire")
                save_state(state)
                st.rerun()
        
        with sim_cols[1]:
            if st.button("🟠 Overpressure (FR)", use_container_width=True):
                tpms["tires"]["fr"]["pressure"] = 42.0
                add_tpms_log("Simulation", "Overpressure on Front Right tire")
                save_state(state)
                st.rerun()
        
        with sim_cols[2]:
            if st.button("🌡️ Temp Spike (All)", use_container_width=True):
                for key in tpms["tires"]:
                    tpms["tires"][key]["temp"] = 60.0 + random.uniform(0, 5)
                add_tpms_log("Simulation", "Temperature spike on all tires")
                save_state(state)
                st.rerun()
        
        with sim_cols[3]:
            if st.button("♻️ Reset All", use_container_width=True):
                tpms["tires"] = {
                    "fl": {"pressure": 32.0, "temp": 35.0, "battery": 98, "health": 92},
                    "fr": {"pressure": 33.0, "temp": 34.0, "battery": 97, "health": 89},
                    "rl": {"pressure": 31.0, "temp": 36.0, "battery": 95, "health": 78},
                    "rr": {"pressure": 32.0, "temp": 35.0, "battery": 96, "health": 85},
                }
                add_tpms_log("System", "All tires reset to normal")
                save_state(state)
                st.rerun()
        
        # Natural fluctuation simulation
        if st.button("📡 Simulate Sensor Reading (natural fluctuation)"):
            for key in tpms["tires"]:
                tpms["tires"][key]["pressure"] += random.uniform(-0.3, 0.3)
                tpms["tires"][key]["temp"] += random.uniform(-0.5, 0.5)
                # Keep within bounds
                tpms["tires"][key]["pressure"] = max(15, min(50, tpms["tires"][key]["pressure"]))
                tpms["tires"][key]["temp"] = max(20, min(80, tpms["tires"][key]["temp"]))
            add_tpms_log("Sensor", "New readings received from all sensors")
            save_state(state)
            st.rerun()
        
        # Event Log
        st.markdown("---")
        st.subheader("📜 Event Log")
        if tpms["log"]:
            log_df = pd.DataFrame(tpms["log"])
            st.dataframe(log_df.iloc[::-1].reset_index(drop=True), use_container_width=True)
        else:
            st.info("No events recorded yet. Use the simulation controls above.")
    
    # ============== TAB 2: ANALYTICS ==============
    with tab2:
        st.subheader("📈 Tire Analytics & Trends")
        
        # Generate sample historical data
        if st.button("Generate Sample History (24h)"):
            for key in tpms["tires"]:
                if "history" not in tpms:
                    tpms["history"] = {}
                base_pressure = tpms["tires"][key]["pressure"]
                base_temp = tpms["tires"][key]["temp"]
                tpms["history"][key] = {
                    "pressure": [base_pressure + random.uniform(-1, 1) for _ in range(24)],
                    "temp": [base_temp + random.uniform(-3, 3) for _ in range(24)]
                }
            save_state(state)
            st.success("Generated 24-hour sample history")
            st.rerun()
        
        if "history" in tpms and tpms["history"]:
            # Pressure chart
            st.subheader("Pressure History (24h)")
            pressure_data = pd.DataFrame({
                "Hour": list(range(24)),
                "FL": tpms["history"].get("fl", {}).get("pressure", [32]*24),
                "FR": tpms["history"].get("fr", {}).get("pressure", [32]*24),
                "RL": tpms["history"].get("rl", {}).get("pressure", [32]*24),
                "RR": tpms["history"].get("rr", {}).get("pressure", [32]*24),
            })
            st.line_chart(pressure_data.set_index("Hour"))
            
            # Temperature chart
            st.subheader("Temperature History (24h)")
            temp_data = pd.DataFrame({
                "Hour": list(range(24)),
                "FL": tpms["history"].get("fl", {}).get("temp", [35]*24),
                "FR": tpms["history"].get("fr", {}).get("temp", [35]*24),
                "RL": tpms["history"].get("rl", {}).get("temp", [35]*24),
                "RR": tpms["history"].get("rr", {}).get("temp", [35]*24),
            })
            st.line_chart(temp_data.set_index("Hour"))
        else:
            st.info("Click 'Generate Sample History' to create trend data")
        
        # Statistics
        st.subheader("📊 Current Statistics")
        stats_cols = st.columns(4)
        
        pressures = [t["pressure"] for t in tpms["tires"].values()]
        temps = [t["temp"] for t in tpms["tires"].values()]
        
        with stats_cols[0]:
            st.metric("Avg Pressure", f"{sum(pressures)/4:.1f} PSI")
        with stats_cols[1]:
            st.metric("Avg Temperature", f"{sum(temps)/4:.1f}°C")
        with stats_cols[2]:
            st.metric("Min Pressure", f"{min(pressures):.1f} PSI")
        with stats_cols[3]:
            st.metric("Max Pressure", f"{max(pressures):.1f} PSI")
        
        # Predictive Maintenance
        st.subheader("🔮 Predictive Maintenance")
        for key, name in tire_names.items():
            tire = tpms["tires"][key]
            health = tire["health"]
            color = "green" if health > 80 else ("orange" if health > 60 else "red")
            st.progress(health/100, text=f"{name}: {health}% health")
    
    # ============== TAB 3: ARCHITECTURE ==============
    with tab3:
        st.subheader("🏗️ TPMS System Architecture")
        st.graphviz_chart(draw_tpms_arch())
        
        st.markdown("---")
        st.subheader("🔧 Hardware Components")
        
        hw_cols = st.columns(3)
        with hw_cols[0]:
            st.markdown("""
            **📡 TPMS Sensor Module**
            - NXP FXTH87 Series
            - Pressure & temperature sensing
            - 433 MHz / BLE 5.0
            - 10-year battery life
            - -40°C to +125°C range
            """)
        
        with hw_cols[1]:
            st.markdown("""
            **🖥️ Edge ECU**
            - NXP S32K144 EVB
            - ARM Cortex-M4F @ 112 MHz
            - CAN FD, LIN, SPI
            - ISO 26262 ASIL-B
            - Real-time processing
            """)
        
        with hw_cols[2]:
            st.markdown("""
            **🌐 TCU Gateway**
            - Raspberry Pi 4 / Jetson
            - Wi-Fi / LTE connectivity
            - MQTT/HTTPS to cloud
            - OTA update management
            - Data aggregation
            """)
        
        st.markdown("---")
        st.subheader("🔄 Data Flow Pipeline")
        st.markdown("""
        ```
        Sensor (RF) → Receiver → Edge ECU → CAN Bus → TCU → Cloud → Dashboard/App
                                    ↓
                              Local Display
        ```
        """)
    
    # ============== TAB 4: SETTINGS & OTA ==============
    with tab4:
        st.subheader("⚙️ Pressure Thresholds")
        
        thresholds = tpms["thresholds"]
        
        col1, col2 = st.columns(2)
        with col1:
            new_low = st.slider("Low Pressure Warning (PSI)", 20, 30, thresholds["low"])
            new_target = st.slider("Target Pressure (PSI)", 30, 35, thresholds["target"])
        with col2:
            new_high = st.slider("High Pressure Warning (PSI)", 35, 45, thresholds["high"])
            new_temp = st.slider("Temperature Warning (°C)", 45, 70, thresholds["temp_warning"])
        
        if st.button("💾 Save Thresholds"):
            tpms["thresholds"] = {"low": new_low, "high": new_high, "target": new_target, "temp_warning": new_temp}
            add_tpms_log("Settings", f"Thresholds updated: Low={new_low}, High={new_high}, Target={new_target}")
            save_state(state)
            st.success("Thresholds saved!")
        
        st.markdown("---")
        st.subheader("🚀 OTA Firmware Update")
        
        ota_cols = st.columns(2)
        with ota_cols[0]:
            st.metric("Current Firmware", tpms.get("firmware", "v2.1.4"))
        with ota_cols[1]:
            st.metric("Latest Available", tpms.get("latest_firmware", "v2.2.0"))
        
        if tpms.get("firmware") != tpms.get("latest_firmware"):
            st.info("🆕 New firmware update available!")
            st.markdown("""
            **Release Notes (v2.2.0):**
            - Improved pressure accuracy ±0.1 PSI
            - New temperature compensation algorithm
            - Battery optimization (+15% life)
            - Security patches
            """)
            
            if st.button("⬇️ Download & Install Update"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i in range(101):
                    progress_bar.progress(i)
                    if i < 30:
                        status_text.text(f"Downloading... {i}%")
                    elif i < 60:
                        status_text.text(f"Verifying signature... {i}%")
                    elif i < 90:
                        status_text.text(f"Installing... {i}%")
                    else:
                        status_text.text(f"Finalizing... {i}%")
                    time.sleep(0.03)
                
                tpms["firmware"] = tpms["latest_firmware"]
                add_tpms_log("OTA", f"Firmware updated to {tpms['firmware']}")
                save_state(state)
                status_text.success(f"✅ Updated to {tpms['firmware']}")
                time.sleep(1)
                st.rerun()
        else:
            st.success("✅ Firmware is up to date!")
        
        st.markdown("---")
        st.subheader("🔔 Notification Settings")
        
        notif_cols = st.columns(2)
        with notif_cols[0]:
            st.checkbox("Low Pressure Alerts", value=True)
            st.checkbox("High Temperature Alerts", value=True)
            st.checkbox("Sensor Battery Low", value=True)
        with notif_cols[1]:
            st.checkbox("Daily Summary Report", value=False)
            st.checkbox("Push to Mobile App", value=True)
            st.checkbox("Email Notifications", value=False)
        
        st.markdown("---")
        st.subheader("📋 Device Information")
        
        info_data = {
            "Device ID": "TPMS-2024-X7K9",
            "ECU Serial": "S32K-00A1B2C3",
            "Install Date": "2024-01-15",
            "Last Calibration": "2024-12-01",
            "Total Distance": "45,230 km",
            "Sensor Protocol": "433 MHz + BLE 5.0",
        }
        
        for key, value in info_data.items():
            st.markdown(f"**{key}:** `{value}`")
    
    # ============== TAB 5: DOCUMENTATION ==============
    with tab5:
        st.subheader("📖 What is TPMS?")
        st.markdown("""
        A **Tire Pressure Monitoring System (TPMS)** is an electronic system designed to monitor 
        the air pressure inside pneumatic tires. The system reports real-time tire pressure information 
        to the driver via a dashboard display, smartphone app, or warning light.
        
        > 💡 TPMS is mandatory in the US (since 2007), EU (since 2014), and many other countries.
        """)
        
        st.subheader("✅ Key Benefits")
        benefits = {
            "🛡️ Safety": "Prevents blowouts and loss of vehicle control",
            "⛽ Fuel Efficiency": "Proper inflation reduces rolling resistance by 3-5%",
            "🛞 Tire Longevity": "Even wear extends tire life by up to 25%",
            "🌍 Environmental": "Reduces CO2 emissions through better fuel economy",
        }
        for icon_title, desc in benefits.items():
            st.markdown(f"- **{icon_title}:** {desc}")
        
        st.subheader("🔄 Direct vs Indirect TPMS")
        
        type_cols = st.columns(2)
        with type_cols[0]:
            st.markdown("""
            **Direct TPMS (dTPMS)**
            - Uses pressure sensors inside each tire
            - Provides accurate real-time readings
            - This project implements dTPMS
            - RF/BLE communication
            """)
        with type_cols[1]:
            st.markdown("""
            **Indirect TPMS (iTPMS)**
            - Uses ABS wheel speed sensors
            - Detects pressure via rotation differences
            - Less accurate
            - No additional sensors needed
            """)
        
        st.subheader("🚗 SDV Integration")
        st.markdown("""
        In a Software-Defined Vehicle, TPMS becomes a connected service:
        - **Cloud Analytics:** Historical data & predictive maintenance
        - **Digital Twin:** Real-time tire state mirroring
        - **OTA Updates:** Remote firmware upgrades
        - **Fleet Management:** Multi-vehicle tire health dashboard
        - **AI/ML:** Anomaly detection & remaining life prediction
        """)
        
        st.subheader("📐 Technical Specifications")
        specs = pd.DataFrame({
            "Parameter": ["Pressure Range", "Accuracy", "Temperature Range", "RF Frequency", "Update Interval", "Battery Life"],
            "Specification": ["0 - 100 PSI", "±1.5 PSI", "-40°C to +125°C", "433.92 MHz", "15 sec - 1 min", "7-10 years"],
            "Notes": ["Typical: 28-36 PSI", "At 25°C reference", "Operating range", "ISM band", "Motion-triggered", "CR2032 or similar"],
        })
        st.dataframe(specs, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# 22️⃣  Navigation setup
# ------------------------------------------------------------------
st.set_page_config(page_title="SDV Full Demo", layout="wide", page_icon="🚗")
st.title("🚗 Software‑Defined Vehicle – Full Demo & Knowledge Hub")

nav_options = {
    "🏠 Overview": "overview",
    "👨‍💻 Developer Playground": "developer",
    "🔧 V&V Engineer": "vver",
    "🔄 SIL & Virtualisation": "sil",
    "🧭 ADAS": "adas",
    "🚗 Inside View": "interior",
    "📱 Infotainment & OTA": "infotainment_ota",
    "🛒 Play Store": "playstore",
    "📱 Installed Apps": "installed",
    "🕹️ Driving Dashboard": "drive",
    "🧠 ECU Monitor": "ecu",
    "🔮 Predictive": "predict",
    "🗺️ Architecture Evolution": "arch",
    "🏆 Leaderboard": "leaderboard",
    "🔐 Door‑Lock System": "doorlock",
    "🛞 TPMS Project": "tpms",  # NEW ENTRY
}
choice = st.sidebar.radio("Select section", list(nav_options.keys()))
view = nav_options[choice]

# Load state
state = load_state()
app_mgr = ApplicationManager(state)
telemetry_source = TelemetrySource()
pm = PredictiveMaintenance()

# ------------------------------------------------------------------
# Page dispatch
# ------------------------------------------------------------------
if view == "overview":
    overview_page()
elif view == "developer":
    developer_playground()
elif view == "vver":
    vver_page()
elif view == "sil":
    sil_virtualization_demo()
elif view == "adas":
    adas_page()
elif view == "interior":
    interior_view_page()
elif view == "infotainment_ota":
    infotainment_ota_page()
elif view == "playstore":
    st.header("🛒 Play Store – Install Demo Apps")
    cols = st.columns(3)
    installed_ids = {a["id"] for a in app_mgr.list_apps()}
    for i, app in enumerate(STORE_APPS):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="border:1px solid #e5e7eb; border-radius:10px; padding:8px; margin-bottom:8px; background:#fff;">
              <div style="display:flex; align-items:center;">
                <span style="font-size:1.4rem; margin-right:6px;">{app['icon']}</span>
                <strong>{app['name']}</strong>
              </div>
              <p style="font-size:0.85rem; color:#555;">{app['description']}</p>
              <small>v{app['version']}</small>
            </div>
            """, unsafe_allow_html=True)
            if app["id"] in installed_ids:
                st.button("Installed ✓", key=f"ps_{app['id']}", disabled=True)
            else:
                if st.button("Install", key=f"ps_{app['id']}"):
                    ok, msg = app_mgr.install_app(app)
                    if ok:
                        st.success(f"{app['name']} installed")
                        st.rerun()
                    else:
                        st.error(msg)
elif view == "installed":
    st.header("📱 Installed Applications")
    apps = app_mgr.list_apps()
    if not apps:
        st.info("No apps installed.")
    else:
        cols = st.columns(3)
        for i, app in enumerate(apps):
            with cols[i % 3]:
                st.markdown(f"""
                <div style="border:1px solid #e5e7eb; border-radius:10px; padding:8px; margin-bottom:8px; background:#fff;">
                  <div style="display:flex; align-items:center;">
                    <span style="font-size:1.4rem; margin-right:6px;">{app.get('icon','📦')}</span>
                    <strong>{app.get('name','App')}</strong>
                  </div>
                  <p style="font-size:0.85rem; color:#555;">{app.get('description','')}</p>
                  <small>v{app.get('version','')}</small>
                </div>
                """, unsafe_allow_html=True)
                c_un, c_up = st.columns(2)
                with c_un:
                    if st.button("Uninstall", key=f"un_{app['id']}"):
                        ok, msg = app_mgr.uninstall_app(app["id"])
                        if ok:
                            st.success("Removed")
                            st.rerun()
                        else:
                            st.error(msg)
                with c_up:
                    if st.button("OTA Update", key=f"ota_{app['id']}"):
                        ok, info = simulate_ota_update(app_mgr, app["id"], seconds=2.0)
                        if ok:
                            st.success(f"Updated to {info}")
                            st.rerun()
                        else:
                            st.error(info)
elif view == "drive":
    st.header("🕹️ Driving Dashboard")
    left, right = st.columns([2, 1])
    with left:
        mode = st.selectbox("Driving mode", ["Normal","Eco","Sport","Snow","Regen"])
        throttle = st.slider("Throttle (%)", 0, 100, 0)
        brake = st.slider("Brake (%)", 0, 100, 0)
        steps = st.number_input("Steps", min_value=1, max_value=200, value=6)
        dt = st.selectbox("Step duration (s)", [0.2,0.5,1.0], index=1)
        if st.button("Step"):
            row = simulate_drive_step(st.session_state, throttle_pct=throttle, brake_pct=brake, dt_seconds=dt, mode=mode)
            st.json(row)
        if st.button("Run"):
            prog = st.progress(0)
            for i in range(int(steps)):
                simulate_drive_step(st.session_state, throttle_pct=throttle, brake_pct=brake, dt_seconds=dt, mode=mode)
                prog.progress(int((i+1)/steps*100))
                time.sleep(max(0.01, dt/5.0))
            st.success(f"Ran {steps} steps")
    with right:
        drv = st.session_state.get("drive", {"speed":0.0,"soc":95.0,"temperature":30.0,"mode":"Normal"})
        st.metric("Speed", f"{drv['speed']:.1f} km/h")
        st.metric("SOC", f"{drv['soc']:.2f} %")
        st.metric("Temp", f"{drv['temperature']:.1f} °C")
        st.metric("Mode", drv["mode"])
    log_df = pd.DataFrame(st.session_state.get("drive_log", []))
    if not log_df.empty:
        log_df["timestamp"] = pd.to_datetime(log_df["timestamp"])
        log_df = log_df.set_index("timestamp")
        cols_chart = [c for c in ["speed","soc","temperature"] if c in log_df.columns]
        if cols_chart:
            st.line_chart(log_df[cols_chart].tail(200))
elif view == "ecu":
    st.header("🧠 ECU Monitor")
    ecu = compute_ecu_snapshot()
    meta = ecu["meta"]
    st.metric("Vehicle speed", f"{meta['speed']:.1f} km/h")
    st.metric("Mode", meta["mode"])
    c1,c2 = st.columns(2)
    with c1:
        with st.expander("🚗 BCM", expanded=True):
            bcm = ecu["BCM"]
            st.metric("Headlights", "ON" if bcm["headlights_on"] else "OFF")
            st.metric("Doors", "Locked" if bcm["doors_locked"] else "Unlocked")
    with c2:
        with st.expander("🔋 BMS", expanded=True):
            bms = ecu["BMS"]
            st.metric("SOC", f"{bms['soc']:.1f} %")
            st.metric("SOH", f"{bms['soh']:.1f} %")
elif view == "predict":
    predictive_page()
elif view == "arch":
    arch_evolution_page()
elif view == "leaderboard":
    leaderboard_page()
elif view == "doorlock":
    door_lock_project_page()
elif view == "tpms":
    tpms_project_page()
else:
    st.error("Unknown page")

# ------------------------------------------------------------------
# End of file
# ------------------------------------------------------------------
