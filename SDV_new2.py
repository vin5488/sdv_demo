#!/usr/bin/env python3
# --------------------------------------------------------------
# SDV Full Demo – Theory + Hands‑on Playground (single file)
# --------------------------------------------------------------
# Features:
#   • Overview & definition of SDV
#   • Developer Playground (HPC, Zonal, OS/MW, SOA, Adaptive‑AUTOSAR,
#     OTA, Cloud/Edge, Security)
#   • V&V Engineer page (unit tests, shift‑left)
#   • SIL & Virtualization demo (multiprocessing)
#   • Infotainment + OTA (play‑store, app icons, version bump)
#   • ADAS page (lane‑departure, collision‑warning)
#   • Inside‑view of the car (interior SVG)
#   • Architecture Evolution diagram (UNO → DUO → Ethernet‑TSN → Service‑Based)
#   • Missions & Badges (unchanged)
#   • Original pages (Play Store, Driving Dashboard, ECU Monitor,
#     Predictive Maintenance, …)
# --------------------------------------------------------------
# Run:   streamlit run SDV_full_demo.py
# --------------------------------------------------------------

import unittest                      # global import for the V&V page
import io                            # capture unittest output
import os, json, time, multiprocessing as mp
import numpy as np, pandas as pd, streamlit as st
from datetime import datetime, timedelta
##from graphviz import Source          # for flow‑charts

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
            return None
        recent = df.tail(12)
        times = (recent["timestamp"].astype("int64") // 1_000_000_000).values
        volts = recent["voltage"].values
        dt = (times[-1] - times[0]) / 3600.0 if len(times) >= 2 else 1.0
        slope = (volts[-1] - volts[0]) / dt
        voltage_drop_rate = -slope if slope < 0 else 0.0
        temp_mean = float(recent["temperature"].mean())
        cycles = int(recent["cycles"].max())

        v_score = min(voltage_drop_rate * 40.0, 40.0)
        t_score = min(max((temp_mean - 25.0) / (60.0 - 25.0) * 35.0, 0.0), 35.0)
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
    speed = s.get("speed", 0.0)          # km/h
    soc = s.get("soc", 95.0)
    temp = s.get("temperature", 30.0)
    cycles = s.get("cycles", 0)

    # base accelerations (simple linear model)
    accel = (throttle_pct / 100.0) * 3.5
    decel = (brake_pct / 100.0) * 6.0 + 0.1

    # mode multipliers
    mode = mode.capitalize()
    if mode == "Eco":
        accel *= 0.7; cur_factor = 0.7; regen_factor = 1.1
    elif mode == "Sport":
        accel *= 1.4; cur_factor = 1.3; regen_factor = 0.9
    elif mode == "Snow":
        accel *= 0.6; cur_factor = 0.8; regen_factor = 1.0
    elif mode == "Regen":
        accel *= 0.9; cur_factor = 0.9; regen_factor = 1.4
    else:   # Normal
        cur_factor = 1.0; regen_factor = 1.0

    # speed update (km/h ↔ m/s)
    speed_ms = speed / 3.6
    speed_ms = max(0.0, speed_ms + (accel - decel) * dt_seconds)
    speed = speed_ms * 3.6

    # battery / power model
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

    # BCM
    bcm = {"headlights_on": (speed < 5) or (idx % 20 >= 10),
           "doors_locked": idx % 7 != 0,
           "cabin_temp": 24 + max(0, (drive["temperature"] - 30) * 0.1)}
    # BMS
    cycles = drive["cycles"]; temp = drive["temperature"]
    soh = max(60.0, 100.0 - cycles * 0.02 - max(0, temp - 35) * 0.1)
    bms = {"soc": drive["soc"], "temp": temp, "cycles": cycles,
           "soh": soh,
           "status": "OK" if soh > 80 else ("Monitor" if soh > 70 else "Degraded")}
    # TCU
    tcu = {"network_status": "Online" if speed < 80 else "Offline",
           "signal_strength": max(1, 5 - int((abs(speed - 60) / 60) * 3)),
           "gps_fix": "3D" if speed > 1 else "2D/Static"}
    # ADAS
    lane_offset = float(np.sin(idx / 15.0) * 0.4)
    adas = {"lane_offset": lane_offset,
            "lane_departure": abs(lane_offset) > 0.3,
            "obstacle_distance": max(5.0, 80.0 - speed * 0.5),
            "collision_warn": speed > 40.0 and max(5.0, 80.0 - speed * 0.5) < 20.0}
    return {"BCM": bcm, "BMS": bms, "TCU": tcu, "ADAS": adas,
            "meta": {"speed": speed, "mode": mode}}

# ------------------------------------------------------------------
# 6️⃣  SVG assets (car top‑view, infotainment screen, interior)
# ------------------------------------------------------------------
CAR_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' width='420' height='240' viewBox='0 0 420 240'>
  <defs>
    <filter id="s" x="-50%" y="-50%" width="200%" height="200%'>
      <feGaussianBlur stdDeviation="6" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect rx="18" ry="18" x="10" y="30" width="400" height="180' fill='#f3f4f6'/>
  <g transform="translate(30,40)">
    <rect x="25" y="30" rx="18" ry="18" width="320" height="110' fill='#2b4b6f' filter='url(#s)'/>
    <rect x="45" y="10" rx="10" ry="10" width="280" height="40' fill='#1f3a56'/>
    <rect x="70" y="25" width="100" height="30' rx='6' ry='6' fill='#cbe3ff' opacity='0.9'/>
    <rect x="190" y="25" width='80' height='30' rx='6' ry='6' fill='#cbe3ff' opacity='0.9'/>
    <circle cx='80' cy='150' r='18' fill='#0f1724'/>
    <circle cx='280' cy='150' r='18' fill='#0f1724'/>
  </g>
  <text x='20' y='18' font-family='sans-serif' font-size='14' fill='#0f1724'>SDV — Demo Vehicle (top view)</text>
</svg>
"""

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
  <!-- steering wheel -->
  <circle cx='210' cy='150' r='30' fill='#cbe3ff'/>
  <line x1='210' y1='120' x2='210' y2='180' stroke='#0f1724' stroke-width='4'/>
  <line x1='180' y1='150' x2='240' y2='150' stroke='#0f1724' stroke-width='4'/>
  <!-- speedometer -->
  <circle cx='100' cy='200' r='50' fill='#cbe3ff'/>
  <text x='100' y='210' font-family='sans-serif' font-size='16' fill='#0f1724' text-anchor='middle'>SPD</text>
  <!-- infotainment screen -->
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
    """Side‑by‑side traditional vs Software‑Defined Vehicle stack."""
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
            Ethernet   [label="High‑speed Ethernet\\n(10 GbE, TSN, 5G)" fillcolor="#E0F7FA"];
            Applications [label="Application Layer\\n(Play Store, Infotainment, OTA, Services)" fillcolor="#E8F5E9"];
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
    """UNO → DUO → Ethernet‑TSN → Service‑Based."""
    dot = """
    digraph Arch {
        rankdir=TB;
        node [shape=box style=filled fontname="Helvetica" fontsize=10];
        UNO   [label="UNO (single‑core MCU)\\nCAN/LIN" fillcolor="#FFEBCC"];
        DUO   [label="DUO (dual‑core)\\nCAN + FlexRay" fillcolor="#FFE4E1"];
        ETH   [label="Ethernet (10 GbE)\\nTSN" fillcolor="#E0F7FA"];
        SB    [label="Service‑Based\\nDDS/SOMEIP" fillcolor="#E8F5E9"];
        Cloud [label="Cloud\\nOTA, fleet analytics" fillcolor="#F3E5F5"];
        UNO -> DUO -> ETH -> SB -> Cloud;
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
    """Simple simulated ECU that receives throttle/brake and returns speed."""
    speed = 0.0                                    # km/h inside the child
    while True:
        cmd = q_cmd.get()
        if cmd == "STOP":
            break
        throttle = cmd.get("throttle", 0.0)
        brake    = cmd.get("brake", 0.0)
        # very small physics (same idea as main model)
        accel = (throttle / 100.0) * 3.5
        decel = (brake / 100.0) * 6.0 + 0.1
        speed_ms = speed / 3.6
        speed_ms = max(0.0, speed_ms + (accel - decel) * 0.1)   # 0.1 s step
        speed = speed_ms * 3.6
        q_resp.put({"speed": round(speed, 2)})

# ------------------------------------------------------------------
# 10️⃣  SIL & Virtualisation demo (multiprocessing)
# ------------------------------------------------------------------
def sil_virtualization_demo():
    st.header("🔄 SIL & Virtualisation Demo")
    st.info(
        """
        *Software‑in‑the‑Loop (SIL)* – the host runs the **vehicle model**.  
        *Hardware‑in‑the‑Loop (HIL)* – an ECU runs in a **separate process**, communicating via queues.  
        This mimics a lightweight container/VM isolation.
        """
    )
    # Create queues (only once, stored in session_state)
    if "ecu_proc" not in st.session_state:
        cmd_q  = mp.Queue()
        resp_q = mp.Queue()
        proc = mp.Process(target=ecu_process, args=(cmd_q, resp_q), daemon=True)
        proc.start()
        st.session_state["ecu_proc"] = proc
        st.session_state["cmd_q"]   = cmd_q
        st.session_state["resp_q"]  = resp_q

    # UI to send commands
    throttle = st.slider("Throttle (%)", 0, 100, 0, key="sil_throttle")
    brake    = st.slider("Brake (%)",    0, 100, 0, key="sil_brake")
    if st.button("Send command to ECU (SIL)"):
        st.session_state["cmd_q"].put({"throttle": throttle, "brake": brake})
        try:
            resp = st.session_state["resp_q"].get(timeout=1.0)
            st.success(f"ECU reported **speed = {resp['speed']} km/h**")
        except Exception:
            st.error("No response from ECU (timeout)")

    # Optional clean‑up
    if st.button("Terminate ECU process (debug)"):
        st.session_state["cmd_q"].put("STOP")
        st.session_state["ecu_proc"].join()
        st.success("ECU process stopped – next visit will restart it.")
        for k in ["ecu_proc", "cmd_q", "resp_q"]:
            if k in st.session_state:
                del st.session_state[k]

# ------------------------------------------------------------------
# 11️⃣  Developer Playground – mini‑demos for each core concept
# ------------------------------------------------------------------
def developer_playground():
    st.header("👨‍💻 Developer Playground – SDV Core Concepts")
    tabs = st.tabs([
        "💻 HPC", "🧩 Zonal Architecture",
        "🖥️ OS / Middleware", "🛎️ SOA",
        "🔧 Adaptive AUTOSAR", "🚀 OTA", "☁️ Cloud / Edge",
        "🔐 Security & Signing"
    ])

    # 1️⃣ HPC -------------------------------------------------
    with tabs[0]:
        st.subheader("💻 High‑Performance Computing (HPC)")
        n = st.slider("Workload size (million ints)", 10, 200, 50, step=10, key="hpc_n")
        if st.button("Run benchmark"):
            start = time.perf_counter()
            total = sum(range(n * 1_000_000))
            elapsed = time.perf_counter() - start
            st.success(f"✅ Sum = {total:,}")
            st.info(f"⏱️ Execution time: **{elapsed:.3f}s**")

    # 2️⃣ Zonal Architecture ---------------------------------
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

    # 3️⃣ OS / Middleware ---------------------------------------
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
        t += 0.001   # 1 ms tick
"""
        st.code(code, language="python")
        st.info("Copy‑paste into a Python REPL to see the simple scheduler in action.")

    # 4️⃣ SOA -------------------------------------------------
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

    # 5️⃣ Adaptive AUTOSAR (mock) -------------------------------
    with tabs[4]:
        st.subheader("🔧 Adaptive AUTOSAR (light‑weight mock)")
        class AdaptiveRuntime:
            def __init__(self):
                self.services = {}
            def register_service(self, name, handler):
                self.services[name] = handler
            def call(self, name, *a, **kw):
                if name not in self.services:
                    raise KeyError(f"Service {name} not registered")
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

    # 6️⃣ OTA -------------------------------------------------
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
                ok, new_ver = simulate_ota_update(app_mgr, app_id, seconds=1.8)
                if ok:
                    st.success(f"✅ Updated to {new_ver}")
                else:
                    st.error(new_ver)

    # 7️⃣ Cloud / Edge -----------------------------------------
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

    # 8️⃣ Security --------------------------------------------
    with tabs[7]:
        st.subheader("🔐 Security & Signing (RSA‑2048)")
        if "private_key" not in st.session_state:
            if st.button("Generate RSA‑2048 key pair"):
                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import padding
                private_key = rsa.generate_private_key(public_exponent=65537,
                                                      key_size=2048)
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
# 🧩 Scenarios helper + catalogues (Easy + Advanced) + page
# ------------------------------------------------------------------

def build_scenario_report(scenario, answers):
    """
    Build a markdown report string for a given scenario.
    `answers` is a dict with keys like "<scenario_id>_<metric_name>" plus
    free-text fields "<scenario_id>_obs", "_interpret", "_recommend".
    """
    md = f"# Scenario {scenario['id']}: {scenario['title']}\n\n"
    md += "## Objective\n"
    md += f"{scenario['objective']}\n\n"

    md += "## Steps (as performed)\n"
    for i, step in enumerate(scenario["steps"], start=1):
        md += f"{i}. {step}\n"
    md += "\n"

    md += "## Collected Metrics\n"
    for metric in scenario["metrics"]:
        key = f"{scenario['id']}_{metric['name']}"
        value = answers.get(key, "")
        md += f"- **{metric['label']}** : {value} {metric.get('unit','')}\n"
    md += "\n"

    obs_key = f"{scenario['id']}_obs"
    int_key = f"{scenario['id']}_interpret"
    rec_key = f"{scenario['id']}_recommend"

    md += "## Observations / Anomalies\n"
    md += f"{answers.get(obs_key, '')}\n\n"

    md += "## Interpretation (Tier‑1 view)\n"
    md += f"{answers.get(int_key, '')}\n\n"

    md += "## Recommendations / Next Steps\n"
    md += f"{answers.get(rec_key, '')}\n"
    return md


# --------------------------------------------------------------
#  Scenarios – Advanced Tier‑1 catalogue (8 challenges)
# --------------------------------------------------------------
SCENARIOS = [
    {
        "id": "1",
        "title": "Compute‑Performance & Power‑Budget",
        "objective": "Show how a compute‑intensive workload influences SOC (energy) and peak speed.",
        "steps": [
            "Developer → HPC: set workload = 100 M ints, press Run benchmark.",
            "Driving Dashboard: Mode = Sport, Throttle = 60 %, Brake = 0, Steps = 30, Step‑duration = 0.5 s, press Run.",
            "Read the benchmark time, the final Speed, the final SOC and the ΔSOC."
        ],
        "metrics": [
            {"name":"bench_time","label":"Benchmark runtime","unit":"ms"},
            {"name":"peak_speed","label":"Peak speed","unit":"km/h"},
            {"name":"soc_start","label":"SOC before drive","unit":"%"},
            {"name":"soc_end","label":"SOC after drive","unit":"%"},
            {"name":"soc_delta","label":"SOC drop (Δ)","unit":"%"},
        ],
    },
    {
        "id": "2",
        "title": "Zonal‑Architecture Wiring & Bandwidth",
        "objective": "Quantify wiring savings when moving from a monolithic ECU layout to a zonal Ethernet architecture.",
        "steps": [
            "Developer → Zonal Architecture: set Original ECUs = 120, Zones = 3, note Original & Zonal wiring and % reduction.",
            "Driving Dashboard: Mode = Normal, Throttle = 50 %, Steps = 20, Step‑duration = 0.5 s, press Run.",
            "ECU Monitor → TCU: read ‘Signal strength’ (proxy for Ethernet‑TSN bandwidth)."
        ],
        "metrics": [
            {"name":"orig_wiring","label":"Original wiring length","unit":"m"},
            {"name":"zonal_wiring","label":"Zonal wiring length","unit":"m"},
            {"name":"reduction","label":"Wiring reduction","unit":"%"},
            {"name":"bandwidth","label":"Simulated bandwidth (speed×0.2)","unit":"Mbps"},
            {"name":"signal_strength","label":"TSN signal strength","unit":""},
        ],
    },
    {
        "id": "3",
        "title": "Adaptive‑AUTOSAR Service Latency",
        "objective": "Measure round‑trip latency of two example services (seat‑heater & VehicleSpeed).",
        "steps": [
            "Developer → SOA: call seat‑heater service 10 times, note latency (ms) each run.",
            "Developer → Adaptive AUTOSAR: query VehicleSpeed service 10 times, note latency."
        ],
        "metrics": [
            {"name":"lat_seat_min","label":"Seat‑heater latency (min)","unit":"ms"},
            {"name":"lat_seat_max","label":"Seat‑heater latency (max)","unit":"ms"},
            {"name":"lat_seat_avg","label":"Seat‑heater latency (avg)","unit":"ms"},
            {"name":"lat_vspeed_min","label":"VehicleSpeed latency (min)","unit":"ms"},
            {"name":"lat_vspeed_max","label":"VehicleSpeed latency (max)","unit":"ms"},
            {"name":"lat_vspeed_avg","label":"VehicleSpeed latency (avg)","unit":"ms"},
        ],
    },
    {
        "id": "4",
        "title": "OTA Transaction Reliability & SLA",
        "objective": "Demonstrate OTA timing and success‑rate under normal and delayed‑network conditions.",
        "steps": [
            "Infotainment & OTA → Play Store: install EcoDrive, Battery, Weather.",
            "Infotainment & OTA → Infotainment screen: start OTA for each app, record total time.",
            "(Optional) edit the source to add a 2 s delay before the OTA progress loop, reload the app and repeat the OTA steps."
        ],
        "metrics": [
            {"name":"ota_time_app1","label":"OTA time – EcoDrive","unit":"s"},
            {"name":"ota_time_app2","label":"OTA time – Battery","unit":"s"},
            {"name":"ota_time_app3","label":"OTA time – Weather","unit":"s"},
            {"name":"ota_total","label":"Total OTA time (sum)","unit":"s"},
            {"name":"sla_target","label":"SLA target per app","unit":"s"},
        ],
    },
    {
        "id": "5",
        "title": "Security – Signature Chain & Tamper Detection",
        "objective": "Show that a signed OTA payload can be verified and that any modification is detected instantly.",
        "steps": [
            "Security & Signing: generate RSA‑2048 key pair.",
            "Sign a short message (e.g., “VehiclePackageV1”).",
            "Verify the signature – should be VALID.",
            "Modify two hex characters of the signature, verify again – should be INVALID."
        ],
        "metrics": [
            {"name":"verify_time_valid","label":"Verification time (valid)","unit":"ms"},
            {"name":"verify_time_invalid","label":"Verification time (invalid)","unit":"ms"},
            {"name":"signature_size","label":"Signature size","unit":"bytes"},
        ],
    },
    {
        "id": "6",
        "title": "ADAS – Lane‑Departure & Collision‑Warning",
        "objective": "Identify at which step the ADAS logic raises lane‑departure and collision warnings during a high‑dynamic drive.",
        "steps": [
            "Driving Dashboard: Mode = Sport, Throttle = 40 %, Brake = 0, Steps = 40, Step‑duration = 0.5 s, press Run.",
            "ADAS page: watch the two flags and note the step number when each flips to YES/⚠️.",
            "ECU Monitor → ADAS (optional): read the numeric lane_offset and obstacle_distance at the warning moments."
        ],
        "metrics": [
            {"name":"step_lane_departure","label":"Step index – lane‑departure","unit":""},
            {"name":"speed_at_lane_departure","label":"Speed at lane‑departure","unit":"km/h"},
            {"name":"step_collision_warn","label":"Step index – collision warning","unit":""},
            {"name":"speed_at_collision","label":"Speed at collision warn","unit":"km/h"},
            {"name":"obstacle_at_warn","label":"Obstacle distance at warning","unit":"m"},
        ],
    },
    {
        "id": "7",
        "title": "Predictive‑Maintenance – Model‑Update Impact",
        "objective": "Quantify how downloading a new AI model changes the battery‑risk score for the same telemetry set.",
        "steps": [
            "Predictive: generate 48 h of telemetry (default settings).",
            "Compute the risk score – note overall score and component breakdown.",
            "Cloud & Edge → Download latest AI model (simulated).",
            "Re‑compute the risk score on the same telemetry data."
        ],
        "metrics": [
            {"name":"risk_before","label":"Risk score before update","unit":""},
            {"name":"risk_after","label":"Risk score after update","unit":""},
            {"name":"risk_delta","label":"Risk Δ (after‑before)","unit":"%"},
            {"name":"model_version_before","label":"Model version before","unit":""},
            {"name":"model_version_after","label":"Model version after","unit":""},
        ],
    },
    {
        "id": "8",
        "title": "System‑Integration – End‑to‑End Feature‑Launch (Capstone)",
        "objective": "Execute a full SDV flow from app install to OTA, ADAS validation and predictive‑maintenance re‑score.",
        "steps": [
            "Play Store → install EcoDrive.",
            "Driving Dashboard → run a 30‑step Sport drive.",
            "ADAS → verify that lane‑departure / collision warnings appear.",
            "Infotainment screen → start OTA for EcoDrive.",
            "Predictive → compute risk score BEFORE OTA.",
            "Predictive → compute risk score AFTER OTA (same telemetry).",
            "Missions → mark Mission 1 (install + OTA) and Mission 3 (ADAS) completed."
        ],
        "metrics": [
            {"name":"total_elapsed","label":"Total elapsed time (install → OTA complete)","unit":"s"},
            {"name":"warnings_before","label":"Number of ADAS warnings before OTA","unit":""},
            {"name":"warnings_after","label":"Number of ADAS warnings after OTA","unit":""},
            {"name":"risk_before","label":"Risk score before OTA","unit":""},
            {"name":"risk_after","label":"Risk score after OTA","unit":""},
            {"name":"badge_earned","label":"Badge(s) earned","unit":""},
        ],
    },
]


# --------------------------------------------------------------
#  EASY Scenario catalogue – beginner-friendly exercises
# --------------------------------------------------------------
EASY_SCENARIOS = [
    {
        "id": "E1",
        "title": "Basic Drive & SOC Drop",
        "objective": "Understand how speed and battery SOC change during a simple drive.",
        "steps": [
            "Driving Dashboard: Mode = Normal, Throttle = 40%, Brake = 0%.",
            "Steps = 10, Duration = 0.5 sec → press Run.",
            "Record Peak Speed, SOC before, SOC after."
        ],
        "metrics": [
            {"name": "peak_speed", "label": "Peak Speed", "unit": "km/h"},
            {"name": "soc_before", "label": "SOC Before", "unit": "%"},
            {"name": "soc_after", "label": "SOC After", "unit": "%"},
        ]
    },
    {
        "id": "E2",
        "title": "Eco vs Sport Comparison",
        "objective": "Compare energy usage between Eco and Sport modes.",
        "steps": [
            "Run 10 steps in ECO mode (Throttle = 40%).",
            "Run 10 steps in SPORT mode (Throttle = 40%).",
            "Record speeds and SOC drops."
        ],
        "metrics": [
            {"name": "eco_speed", "label": "Peak Speed (Eco)", "unit": "km/h"},
            {"name": "eco_soc_drop", "label": "SOC Drop (Eco)", "unit": "%"},
            {"name": "sport_speed", "label": "Peak Speed (Sport)", "unit": "km/h"},
            {"name": "sport_soc_drop", "label": "SOC Drop (Sport)", "unit": "%"},
        ]
    },
    {
        "id": "E3",
        "title": "ADAS Alerts (Beginner)",
        "objective": "Identify whether the ADAS logic flags lane departure or collision warning.",
        "steps": [
            "Driving Dashboard: Mode = Normal, Throttle = 30%, Steps = 20.",
            "After run → ADAS page: Note alerts.",
        ],
        "metrics": [
            {"name": "lane_depart", "label": "Lane Departure Alert (YES/NO)", "unit": ""},
            {"name": "collision", "label": "Collision Warning Alert (YES/NO)", "unit": ""},
        ]
    },
    {
        "id": "E4",
        "title": "Install & OTA Update",
        "objective": "Complete a basic install + OTA update flow.",
        "steps": [
            "Play Store → Install EcoDrive.",
            "Infotainment → OTA update EcoDrive.",
            "Record old version, new version, and time taken."
        ],
        "metrics": [
            {"name": "old_version", "label": "Old Version", "unit": ""},
            {"name": "new_version", "label": "New Version", "unit": ""},
            {"name": "ota_time", "label": "OTA Time", "unit": "s"},
        ]
    },
    {
        "id": "E5",
        "title": "Predictive Battery Risk (Simple)",
        "objective": "Generate a basic risk score using default telemetry.",
        "steps": [
            "Predictive → Use Driving Log telemetry.",
            "Press Compute Risk Score.",
            "Record risk score and temperature.",
        ],
        "metrics": [
            {"name": "risk_score", "label": "Risk Score", "unit": ""},
            {"name": "temp_mean", "label": "Temperature Mean", "unit": "°C"},
            {"name": "voltage_drop", "label": "Voltage Drop Indicator", "unit": "%"},
        ]
    },
]


# --------------------------------------------------------------
#  Scenarios & Report page (Easy + Advanced + Examples)
# --------------------------------------------------------------
def scenarios_page():
    """🧩 Scenarios & Report – trainer‑driven challenges (easy + advanced)."""
    st.header("🧩 Scenarios & Report – Tier 1 Challenges")
    st.caption(
        """
        Each box below describes a real‑world SDV use case.
        Follow the *Steps* in the app, fill the fields with the numbers you obtain,
        add short observations/interpretations, then click **Generate report**.
        The generated **Markdown** file can be downloaded and later submitted.
        """
    )

    # Difficulty selector
    difficulty = st.radio(
        "Choose difficulty level:",
        ["Easy scenarios (beginner)", "Advanced scenarios (Tier‑1)"],
        horizontal=True,
    )

    # Example walkthrough
    with st.expander("📌 Example – How a scenario works (with sample report)"):
        st.markdown(
            """
### Step 1 – Run the scenario in the app
For example:  
*Driving Dashboard → Mode = Normal, Throttle = 40%, 10 steps, 0.5 s each.*

### Step 2 – Enter the metrics
Copy the Peak Speed and SOC values into the **Collected metrics** fields.
Write 2–3 short sentences in **Observations**, **Interpretation** and **Recommendations**.

### Step 3 – Generate the markdown
Click **Generate report** – the app builds a ready‑to‑submit `.md` file.
Below is what a simple report could look like:
"""
        )
        st.code(
            """# Scenario 1: Basic Drive & SOC Drop

## Objective
Understand how speed and battery SOC change during a simple drive.

## Collected Metrics
- **Peak Speed** : 57 km/h
- **SOC Before** : 94.3 %
- **SOC After** : 93.8 %

## Observations / Anomalies
Smooth acceleration; SOC reduced by ~0.5% which looks reasonable for a short Normal‑mode drive.

## Interpretation (Tier‑1 view)
Higher throttle and more aggressive drive modes will increase energy usage. Even simple benchmarks like this help a Tier‑1 to size the power‑budget for the ECU and cooling system.

## Recommendations / Next Steps
Repeat the test in Sport mode and compare SOC drop and peak speed.
""",
            language="markdown",
        )

    st.markdown("---")

    # Template download – for participants who prefer to work offline
    template_md = """# Scenario X – <Title>

## Objective
<Write the objective in your own words.>

## Steps (as performed)
1. …
2. …
3. …

## Collected Metrics
- **Metric 1** : <value> <unit>
- **Metric 2** : <value> <unit>
- …

## Observations / Anomalies
<Free‑text>

## Interpretation (Tier‑1 view)
<Free‑text – why does the result matter for a supplier?>

## Recommendations / Next Steps
<Free‑text>
"""
    st.download_button(
        label="📥 Download empty report template (Markdown)",
        data=template_md,
        file_name="scenario_template.md",
        mime="text/markdown",
    )

    st.markdown("---")

    # Pick scenario set based on difficulty
    scenarios = EASY_SCENARIOS if "Easy" in difficulty else SCENARIOS

    # Loop over each scenario and present a form
    for sc in scenarios:
        with st.expander(f"Scenario {sc['id']}: {sc['title']}"):
            st.subheader("Objective")
            st.write(sc["objective"])

            st.subheader("Steps (what you have to do in the app)")
            for i, step in enumerate(sc["steps"], start=1):
                st.markdown(f"{i}. {step}")

            # ------- FORM ----------
            with st.form(key=f"form_{sc['id']}"):
                st.subheader("Collected Metrics")
                # generate a widget for each metric
                for met in sc["metrics"]:
                    widget_key = f"{sc['id']}_{met['name']}"
                    st.text_input(
                        f"{met['label']} ({met.get('unit','')})",
                        key=widget_key,
                    )

                obs_key = f"{sc['id']}_obs"
                int_key = f"{sc['id']}_interpret"
                rec_key = f"{sc['id']}_recommend"

                st.subheader("Observations / Anomalies")
                st.text_area("Free‑text", key=obs_key, height=80)

                st.subheader("Interpretation (Tier‑1 view)")
                st.text_area("Free‑text", key=int_key, height=80)

                st.subheader("Recommendations / Next Steps")
                st.text_area("Free‑text", key=rec_key, height=80)

                submitted = st.form_submit_button("📝 Generate report")
                if submitted:
                    # gather the answers
                    answers = {}
                    for met in sc["metrics"]:
                        answers[f"{sc['id']}_{met['name']}"] = st.session_state.get(
                            f"{sc['id']}_{met['name']}", ""
                        )
                    answers[obs_key] = st.session_state.get(obs_key, "")
                    answers[int_key] = st.session_state.get(int_key, "")
                    answers[rec_key] = st.session_state.get(rec_key, "")

                    markdown_report = build_scenario_report(sc, answers)

                    st.success("✅ Report generated – download it below.")
                    st.download_button(
                        label="⬇️ Download your report (Markdown)",
                        data=markdown_report,
                        file_name=f"scenario_{sc['id']}_report.md",
                        mime="text/markdown",
                    )

    st.markdown("---")


# ------------------------------------------------------------------
# 12️⃣  Overview / Theory page
# ------------------------------------------------------------------
def overview_page():
    st.header("🏠 Software‑Defined Vehicle (SDV) – Overview")
    st.markdown(
        """
        ### 📖 What is an SDV?
        A **Software‑Defined Vehicle** is a vehicle whose **functions are delivered as software services** that run on **high‑performance compute platforms** and are **delivered/updated over the air**.  
        Instead of dozens of hard‑wired ECUs, an SDV has a **central compute + a thin Ethernet‑TSN backbone** and can **install or replace services at runtime** – exactly like a smartphone.

        ### 🎯 Why do we need SDV?
        * **Reduced wiring & weight** – fewer ECUs → lighter vehicle.  
        * **Faster time‑to‑market** – OTA can deliver new features in weeks, not years.  
        * **Scalable compute** – one platform can host ADAS, infotainment, V2X, etc.  
        * **Continuous improvement** – AI models are updated from the cloud, improving safety/performance over the vehicle’s lifetime.  
        * **Better data & analytics** – telemetry streams enable predictive maintenance and fleet optimisation.

        ### 🧩 Core building blocks (high‑level stack)
        ```text
        Sensors → Compute (HPC/AI) → Connectivity (Ethernet/TSN/5G)
                 ↓
           Application Layer (Play‑Store, OTA, Services, Micro‑apps)
                 ↓
                Cloud (fleet analytics, OTA server, model training)
        ```
        """
    )
    st.subheader("📊 SDV Stack – visual overview")
    st.graphviz_chart(draw_sdv_stack())

    st.markdown("---")
    st.subheader("🧑‍💻 Developer Perspective – Where can a developer work?")
    st.markdown(
        """
        | Area | What the developer does | Typical tech / example |
        |------|------------------------|------------------------|
        | **HPC / Edge‑AI** | Write perception / sensor‑fusion algorithms, optimise GPU kernels. | CUDA, TensorRT, ONNX, PyTorch‑Lite |
        | **Zonal Architecture** | Define zone boundaries, configure Ethernet‑TSN traffic classes. | AUTOSAR Zonal, IEEE 802.1TSN |
        | **OS & Middleware** | Extend Linux services, add Diagnostics, Time‑Sync, Secure‑Onboard‑Communication. | Linux, AUTOSAR Adaptive, ROS 2 |
        | **SOA / Micro‑services** | Create small, stateless services (e.g. “lane‑keep”) and register them. | SOME/IP, DDS, gRPC |
        | **Adaptive AUTOSAR** | Package services as AUTOSAR Adaptive applications, use the Execution Management (EM). | AUTOSAR Adaptive API |
        | **OTA** | Produce signed update packages, integrate with the OTA server, verify signatures on‑board. | OTA‑Server, CSM, Cryptographic signing |
        | **Cloud / Edge** | Build CI/CD pipelines that push container images, write fleet‑analytics jobs. | Docker, Kubernetes, Azure IoT Edge |
        | **Security** | Add Secure Boot, Runtime Integrity, and signed OTA payloads. | ISO‑SAE 21434, AUTOSAR Secure On‑board Communication |
        | **Virtualisation** | Run multiple OS instances (Linux, QNX) side‑by‑side using containers or hyper‑visors. | Docker, LXC, Hypervisor‑based isolation |
        """
    )
    st.info(
        """
        The **Developer Playground** page (next on the left) lets you experiment with all of these areas in a few minutes.
        """
    )

# ------------------------------------------------------------------
# 13️⃣  V&V Engineer page (unit‑tests, shift‑left)
# ------------------------------------------------------------------
def vver_page():
    """V&V Engineer – Verification & Validation page (unit‑test demo)."""
    st.header("🔧 V&V Engineer – Verification & Validation")
    st.markdown(
        """
        **Verification** – “Are we building the system right?”  
        **Validation** – “Did we build the right system?”  

        In an SDV the **software‑in‑the‑loop (SIL)** can run on a developer laptop,
        allowing early‑stage testing before any hardware exists.  
        Classic **hardware‑in‑the‑loop (HIL)** is still used for safety‑critical parts,
        but the bulk of testing now runs in pure software.
        """
    )

    # tiny function to test
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

    st.markdown("---")
    st.subheader("🛠️ Shift‑Left – SIL demo")
    if st.button("Run drive SIL (5 steps)"):
        for _ in range(5):
            simulate_drive_step(st.session_state,
                                throttle_pct=30,
                                brake_pct=0,
                                dt_seconds=0.5,
                                mode="Normal")
        st.success("✅ SIL run finished – data stored in *Drive Log*")

# ------------------------------------------------------------------
# 14️⃣  ADAS page (visualise lane‑departure & collision warning)
# ------------------------------------------------------------------
def adas_page():
    st.header("🧭 ADAS – Driver Assistance Overview")
    st.info(
        """
        The ADAS block monitors lane‑offset, detects lane‑departure and checks for imminent collisions based on the simulated obstacle distance.
        """
    )
    ecu = compute_ecu_snapshot()
    adas = ecu["ADAS"]
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Lane offset (m)", f"{adas['lane_offset']:+.2f}")
        st.metric("Lane departure", "YES" if adas["lane_departure"] else "NO")
    with col2:
        st.metric("Obstacle distance (m)", f"{adas['obstacle_distance']:.1f}")
        st.metric("Collision warning", "⚠️" if adas["collision_warn"] else "OK")
    st.caption("Values are synthesized from the same simple vehicle model used by the Driving Dashboard.")

# ------------------------------------------------------------------
# 15️⃣  Inside‑view of the car (simple interior SVG)
# ------------------------------------------------------------------
def interior_view_page():
    st.header("🚗 Inside View – Car Interior")
    st.markdown(
        """
        A very simplified top‑down view of a car interior – steering wheel, speedometer and infotainment screen.  
        The UI updates dynamically when you install OTA updates or change the speed via the Driving Dashboard.
        """
    )
    # Show the interior SVG
    st.markdown(svg_to_html(INTERIOR_SVG, width=480), unsafe_allow_html=True)

    # Show current speed / mode as it would appear on the speedometer
    drv = st.session_state.get(
        "drive",
        {"speed":0.0,"soc":95.0,"temperature":30.0,"mode":"Normal"},
    )
    st.metric("Current speed (km/h)", f"{drv['speed']:.1f}")
    st.metric("Current mode", drv["mode"])

# ------------------------------------------------------------------
# 16️⃣  Infotainment & OTA page (play‑store + in‑vehicle UI)
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
                <div class="app-card" style="border:1px solid #e5e7eb;
                     border-radius:10px; padding:8px; margin-bottom:8px;
                     background:#fff;">
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

    st.markdown("---")
    st.subheader("🚗 Vehicle‑side view")
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.markdown(svg_to_html(CAR_SVG, width=480), unsafe_allow_html=True)
        drv = st.session_state.get(
            "drive",
            {"speed":0.0,"soc":95.0,"temperature":30.0,"mode":"Normal"},
        )
        st.metric("Speed (km/h)", f"{drv['speed']:.1f}")
        st.metric("SOC (%)", f"{drv['soc']:.2f}")
        st.metric("Battery Temp (°C)", f"{drv['temperature']:.1f}")
        st.metric("Mode", drv["mode"])
    with col_right:
        st.markdown(svg_to_html(INFOTAINMENT_SVG, width=320), unsafe_allow_html=True)
        # Up to 6 installed apps on the infotainment grid
        apps = app_mgr.list_apps()[:6]
        slots = [(28,92),(126,92),(224,92),(28,168),(126,168),(224,168)]
        html = "<div style='position:relative; left:0; top:-220px; width:320px;'>"
        for i, (x, y) in enumerate(slots):
            if i < len(apps):
                a = apps[i]
                html += f"""
                <div style='position:absolute; left:{x}px; top:{y}px;
                            width:80px; height:60px; border-radius:8px;
                            background:#fff; box-shadow:0 2px 6px rgba(0,0,0,0.15);
                            display:flex; flex-direction:column; align-items:center;
                            justify-content:center; font-family:sans-serif; text-align:center;'>
                  <div style='font-size:20px'>{a.get('icon','📦')}</div>
                  <div style='font-size:11px; margin-top:4px'>{a.get('name','')}</div>
                  <div style='font-size:9px; color:#444'>v{a.get('version','')}</div>
                </div>
                """
            else:
                html += f"<div style='position:absolute; left:{x}px; top:{y}px; width:80px; height:60px;'></div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("🛠️ OTA update from the infotainment screen")
        if apps:
            sel = st.selectbox(
                "Select an installed app to OTA‑update",
                [f"{a['name']} ({a['id']}) – v{a['version']}" for a in apps],
                key="inf_ota_sel")
            app_id = sel.split("(")[1].split(")")[0]
            if st.button("Start OTA (demo)"):
                ok, info = simulate_ota_update(app_mgr, app_id, seconds=2.0)
                if ok:
                    st.success(f"✅ Updated to {info}")
                    st.rerun()
                else:
                    st.error(info)
        else:
            st.info("No apps installed – install from Play Store first.")

# ------------------------------------------------------------------
# 17️⃣  Docs page – all theory you requested
# ------------------------------------------------------------------
def docs_page():
    st.header("📖 Documentation – All SDV Topics")
    st.subheader("🔎 SDV – Definition & Perspectives")
    st.markdown(
        """
        **Software‑Defined Vehicle (SDV)** – a vehicle whose functions are realised as **software services** running on a **central high‑performance compute platform** and delivered/updated via an **over‑the‑air (OTA)** mechanism.  
        It replaces the classic “many ECUs, many wires” paradigm with a **service‑oriented, cloud‑connected** architecture.

        **Key perspectives**
        * **Developer:** writes micro‑services / containers, uses CI/CD, integrates with AUTOSAR Adaptive.  
        * **V&V Engineer:** builds SIL/HIL rigs, runs automated unit‑tests, validates functional safety (ISO‑26262).  
        * **OEM:** defines zone layout, Ethernet‑TSN backbone, decides which functions stay on dedicated ECUs vs migrate to the central compute.  
        * **Customer:** sees a **car‑app store**, can install new features like a smartphone.
        """
    )
    st.subheader("💡 Why SDV is needed & benefits")
    st.markdown(
        """
        | Benefit | Explanation |
        |---------|-------------|
        | **Reduced wiring & weight** | One Ethernet backbone replaces dozens of CAN/LIN lines. |
        | **Faster time‑to‑market** | OTA can deliver new features in weeks, not years. |
        | **Scalable compute** | Central HPC can host many workloads (ADAS, infotainment, V2X). |
        | **Continuous improvement** | AI models are updated from the cloud, improving safety/performance over the vehicle’s lifetime. |
        | **Better data & analytics** | Telemetry streams enable predictive maintenance, fleet optimisation. |
        """
    )
    st.subheader("🧱 SDV ecosystem components")
    st.markdown(
        """
        1. **Sensors** – cameras, radar, LiDAR, ultrasonic, GPS.  
        2. **High‑Performance Compute (HPC / Edge‑AI)** – GPU/CPU/TPU, runs perception, path‑planning.  
        3. **Zonal Architecture** – physical zones (front, rear, power) connected via high‑speed Ethernet/TSN.  
        4. **OS & Middleware** – Linux + AUTOSAR Adaptive, service discovery, diagnostics, time‑sync.  
        5. **SOA / Micro‑services** – SOME/IP, DDS, gRPC; enable hot‑swap of functionality.  
        6. **Play‑Store & Infotainment** – user‑facing app marketplace; OTA updates occur per app.  
        7. **Cloud & Edge** – fleet management, OTA server, AI‑model training, data lake.  
        8. **Cybersecurity Framework** – signed OTA, secure boot, ISO‑SAE 21434 compliance.  
        """
    )
    st.subheader("🚀 Approaches to achieve SDV")
    st.markdown(
        """
        * **Do I need Adaptive AUTOSAR?** – If you need a standardized service‑oriented runtime, Adaptive AUTOSAR gives you a compliant middleware (SOME/IP, time sync).  
        * **Shift‑North** – Move compute north (up) from the ECU level to the central compute, while still keeping safety‑critical functions on dedicated hardware if required.  
        * **AI‑driven processing** – Run deep‑learning models on‑edge; update them OTA.  
        * **Virtualisation & Multi‑OS** – Run Linux + QNX containers side‑by‑side, each isolated but sharing the same hardware.  
        * **Homologation – Today vs OTA** – Traditional certification freezes the software at launch; OTA‑enabled vehicles must also certify the **update process** (secure boot, signed images, rollback).  
        """
    )
    st.subheader("🗂️ Additional reading (short list)")
    st.markdown(
        """
        * AUTOSAR Adaptive Platform – https://www.autosar.org/standards/adaptive/  
        * ISO 26262 – Road vehicles – Functional safety.  
        * SAE 21434 – Cybersecurity engineering for vehicles.  
        * “Time‑Sensitive Networking” – IEEE 802.1TSN.  
        * “Software‑Defined Vehicles – The Next Generation” – IEEE Tech. 
        """
    )
    st.info("All the theory above is linked to the interactive pages – jump to *Developer Playground*, *V&V Engineer*, *ADAS*, *Inside View* or *Infotainment & OTA* to see the concepts in action.")

# ------------------------------------------------------------------
# 18️⃣  Navigation setup (sidebar)
# ------------------------------------------------------------------
st.set_page_config(page_title="SDV Full Demo", layout="wide", page_icon="🚗")
st.title("🚗 Software‑Defined Vehicle – Full Demo & Knowledge Hub")
st.caption(
    "Hands‑on playground **+** theory pages covering the entire SDV ecosystem."
)

nav_options = {
    "🏠 Overview": "overview",
    "👨‍💻 Developer Playground": "developer",
    "🔧 V&V Engineer": "vver",
    "🔄 SIL & Virtualisation": "sil",
    "🧭 ADAS": "adas",
    "🚗 Inside View": "interior",
    "📱 Infotainment & OTA": "infotainment_ota",
    "🧩 Scenarios & Report": "scenarios",
    "🛒 Play Store": "playstore",
    "📱 Installed Apps": "installed",
    "🕹️ Driving Dashboard": "drive",
    "🧠 ECU Monitor": "ecu",
    "🔮 Predictive": "predict",
    "🗺️ Architecture Evolution": "arch",
    "🎯 Missions": "missions",
    "📖 Docs": "docs",
}
choice = st.sidebar.radio("Select section", list(nav_options.keys()))
view = nav_options[choice]

# Load / init the global state once for the whole session
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
elif view == "scenarios":
    scenarios_page()
elif view == "playstore":
    # ---- Play Store (original) ----
    st.header("🛒 Play Store – Install Demo Apps")
    cols = st.columns(3)
    installed_ids = {a["id"] for a in app_mgr.list_apps()}
    for i, app in enumerate(STORE_APPS):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="app-card" style="border:1px solid #e5e7eb;
                     border-radius:10px; padding:8px; margin-bottom:8px;
                     background:#fff;">
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
    # ---- Installed Apps (original) ----
    st.header("📱 Installed Applications")
    apps = app_mgr.list_apps()
    if not apps:
        st.info("No apps installed.")
    else:
        cols = st.columns(3)
        for i, app in enumerate(apps):
            with cols[i % 3]:
                st.markdown(
                    f"""
                    <div class="app-card" style="border:1px solid #e5e7eb;
                         border-radius:10px; padding:8px; margin-bottom:8px;
                         background:#fff;">
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
    # ---- Driving Dashboard (original) ----
    st.header("🕹️ Driving Dashboard")
    left, right = st.columns([2, 1])

    with left:
        mode = st.selectbox("Driving mode", ["Normal","Eco","Sport","Snow","Regen"])
        throttle = st.slider("Throttle (%)", 0, 100, 0)
        brake = st.slider("Brake (%)", 0, 100, 0)
        steps = st.number_input("Steps", min_value=1, max_value=200, value=6)
        dt = st.selectbox("Step duration (s)", [0.2,0.5,1.0], index=1)

        if st.button("Step"):
            row = simulate_drive_step(st.session_state,
                                      throttle_pct=throttle,
                                      brake_pct=brake,
                                      dt_seconds=dt,
                                      mode=mode)
            st.json(row)

        if st.button("Run"):
            prog = st.progress(0)
            for i in range(steps):
                simulate_drive_step(st.session_state,
                                   throttle_pct=throttle,
                                   brake_pct=brake,
                                   dt_seconds=dt,
                                   mode=mode)
                prog.progress(int((i+1)/steps*100))
                time.sleep(max(0.01, dt/5.0))
            st.success(f"Ran {steps} steps")

    with right:
        drv = st.session_state.get(
            "drive",
            {"speed":0.0,"soc":95.0,"temperature":30.0,"mode":"Normal"},
        )
        st.metric("Speed", f"{drv['speed']:.1f} km/h")
        st.metric("SOC", f"{drv['soc']:.2f} %")
        st.metric("Temp", f"{drv['temperature']:.1f} °C")
        st.metric("Mode", drv["mode"])

    log_df = pd.DataFrame(st.session_state.get("drive_log", []))
    if not log_df.empty:
        log_df["timestamp"] = pd.to_datetime(log_df["timestamp"])
        log_df = log_df.set_index("timestamp")
        tab_chart, tab_table = st.tabs(["📈 Telemetry charts", "📋 Recent rows"])
        with tab_chart:
            cols_chart = [c for c in ["speed","soc","temperature"] if c in log_df.columns]
            if cols_chart:
                st.line_chart(log_df[cols_chart].tail(200))
        with tab_table:
            st.dataframe(log_df.tail(30))
    else:
        st.info("No drive data yet – press **Step** or **Run** above.")

elif view == "ecu":
    # ---- ECU Monitor (original) ----
    st.header("🧠 ECU Monitor")
    ecu = compute_ecu_snapshot()
    meta = ecu["meta"]
    st.metric("Vehicle speed", f"{meta['speed']:.1f} km/h")
    st.metric("Mode", meta["mode"])
    st.metric("SOC", f"{ecu['BMS']['soc']:.1f} %")
    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        with st.expander("🚗 BCM – Body Control Module", expanded=True):
            bcm = ecu["BCM"]
            st.metric("Headlights", "ON" if bcm["headlights_on"] else "OFF")
            st.metric("Doors locked", "Locked" if bcm["doors_locked"] else "Unlocked")
            st.metric("Cabin temp (°C)", f"{bcm['cabin_temp']:.1f}")
    with c2:
        with st.expander("🔋 BMS – Battery Management System", expanded=True):
            bms = ecu["BMS"]
            st.metric("SOC", f"{bms['soc']:.1f} %")
            st.metric("Battery temp (°C)", f"{bms['temp']:.1f}")
            st.metric("Cycles", bms["cycles"])
            st.metric("SOH", f"{bms['soh']:.1f} %")
            st.metric("Status", bms["status"])
    c3,c4 = st.columns(2)
    with c3:
        with st.expander("📡 TCU – Telematics Control Unit", expanded=True):
            tcu = ecu["TCU"]
            st.metric("Network", tcu["network_status"])
            st.metric("Signal strength", tcu["signal_strength"])
            st.metric("GPS fix", tcu["gps_fix"])
    with c4:
        with st.expander("🧭 ADAS – Driver Assistance", expanded=True):
            adas = ecu["ADAS"]
            st.metric("Lane offset (m)", f"{adas['lane_offset']:+.2f}")
            st.metric("Lane departure", "YES" if adas["lane_departure"] else "NO")
            st.metric("Obstacle distance (m)", f"{adas['obstacle_distance']:.1f}")
            st.metric("Collision warn", "⚠️" if adas["collision_warn"] else "OK")
    st.info("All values are synthetic and derived from the same drive model.")

elif view == "predict":
    # ---- Predictive Maintenance (original) ----
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
    else:  # Driving Log
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
        tab_chart, tab_detail = st.tabs(["📊 Component breakdown", "📝 Full explanation"])
        with tab_chart:
            comps = expl["components"]
            comp_df = pd.DataFrame({
                "Component": ["Voltage","Temperature","Cycles"],
                "Score": [comps["v_score"], comps["t_score"], comps["c_score"]]
            }).set_index("Component")
            st.bar_chart(comp_df)
        with tab_detail:
            st.json(expl)
    else:
        st.info("No telemetry loaded yet.")

elif view == "arch":
    st.header("🗺️ Architecture Evolution")
    st.graphviz_chart(draw_arch_evolution())
    st.markdown(
        """
        The path **UNO → DUO → Ethernet‑TSN → Service‑Based** is the typical migration many OEMs follow today.
        """
    )

elif view == "missions":
    # ---- Missions & Badges (unchanged – copy the block from the previous version) ----
    st.header("🎯 SDV Missions & Badges")
    st.caption("Hands‑on challenges for learners.")
    # ---- Mission definitions (copy‑paste from the original script) ----
    missions = [
        {
            "id":"m1",
            "title":"Mission 1 – Install & OTA an app",
            "steps":"1) Play Store → install EcoDrive & Battery.\n2) Installed Apps → OTA‑update EcoDrive.\n3) Infotainment → verify version bump.",
            "badge":"ota_expert"
        },
        {
            "id":"m2",
            "title":"Mission 2 – Eco vs Sport battery impact",
            "steps":"1) Driving Dashboard → Eco mode, throttle 40 %, run 40 steps.\n2) Record SOC.\n3) Switch to Sport, same throttle, run 40 steps.\n4) Compare SOC drop.",
            "badge":"eco_champion"
        },
        {
            "id":"m3",
            "title":"Mission 3 – ADAS lane‑departure demo",
            "steps":"1) Drive in mixed mode for ~80 steps.\n2) Open ECU Monitor → ADAS.\n3) Observe lane‑offset & departure warnings.",
            "badge":"adas_specialist"
        },
        {
            "id":"m4",
            "title":"Mission 4 – Predictive battery risk",
            "steps":"1) Drive Eco + Sport (≥60 steps total).\n2) Predictive → use Driving Log.\n3) View risk score & component breakdown.",
            "badge":"battery_guru"
        },
        # Add m5‑m9 if you want – they were in the original script.
    ]

    for m in missions:
        st.markdown("---")
        col_chk, col_body = st.columns([0.07, 0.93])
        with col_chk:
            st.checkbox(" ", value=state["missions"].get(m["id"], False),
                         key=f"chk_{m['id']}", disabled=True)
        with col_body:
            st.subheader(m["title"])
            st.markdown(f"**Steps**:\n{m['steps'].replace('\n','  \n')}")
            if not state["missions"].get(m["id"], False):
                if st.button(f"Mark `{m['title']}` as completed", key=f"b_{m['id']}"):
                    state["missions"][m["id"]] = True
                    state["badges"][m["badge"]] = True
                    save_state(state)
                    st.success("✅ Mission completed – badge unlocked!")
                    st.rerun()
            else:
                st.success("✅ Completed")

    st.markdown("---")
    st.subheader("🛡️ Your Badges")
    badge_names = {
        "eco_champion":"🌱 Eco Champion",
        "ota_expert":"⬆️ OTA Expert",
        "adas_specialist":"🚦 ADAS Specialist",
        "battery_guru":"🔋 Battery Guru",
        "drive_master":"🚗 Drive Master",
        "data_analyst":"📊 Data Analyst",
        "fleet_engineer":"🛠️ Fleet Engineer",
    }
    cols = st.columns(4)
    for i, (bid, unlocked) in enumerate(state["badges"].items()):
        with cols[i%4]:
            if unlocked:
                st.success(badge_names[bid])
            else:
                st.info(badge_names[bid])

elif view == "docs":
    docs_page()
else:
    st.error("Unknown page – something went wrong.")

# ------------------------------------------------------------------
# End of file
# ------------------------------------------------------------------

