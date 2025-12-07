# sdv_demo
Short demo on SDV Playground Demo

SDV Interactive Demo – Student Walkthrough

Welcome to the Software–Defined Vehicle (SDV) Hands-on Demo.
This exercise teaches you how modern automotive software, OTA, ADAS, prediction models and zonal architecture work — through a browser.

You will complete either Easy or Advanced Scenarios, generate reports, and submit them.

🟩 Step 1 — Open the SDV Demo

Your instructor will share a link such as:

https://your-sdv-demo.streamlit.app


Open it on your laptop.

🟩 Step 2 — Explore the Left Sidebar

The navigation menu contains:

👨‍💻 Developer Playground

🧭 ADAS Dashboard

📱 Infotainment & OTA

🔮 Predictive Maintenance

🕹️ Driving Dashboard

🧠 ECU Monitor

🎯 Missions

🧩 Scenarios & Report ← Your main work area

🟩 Step 3 — Go to “🧩 Scenarios & Report”

You will see:

Difficulty Selector

Easy (Beginner)

Advanced (Tier-1)

Example walkthrough

Expandable scenario boxes

Form fields for entering metrics

Button to generate your report

🟦 EASY MODE (recommended for first timers)

The system will show 5 simple scenarios like:

Basic Drive & SOC Drop

Eco vs Sport Drive Comparison

ADAS Alert Detection

Install + OTA Update Flow

Simple Predictive Risk Score

Each scenario explains:

What to do

Step-by-step actions

What numbers to collect

🟩 Step 4 — Read the Scenario Instructions

Inside each scenario:

Read the objective

Follow the steps using other pages of the app

Return to the scenario form and fill:

Peak speed

SOC drop

Warning flags

OTA time

Risk score

(depending on scenario)

🟩 Step 5 — Fill the Form

For each metric:

Peak Speed (km/h): 57
SOC Before (%): 94.3
SOC After (%): 93.8


Then write short answers in:

Observations

Interpretation

Recommendations

No long paragraphs needed — 2–3 sentences each.

🟩 Step 6 — Click “📝 Generate report”

The system creates a Markdown (.md) file instantly.

Download the file:

scenario_E1_report.md


Rename it if required:

TeamA_Scenario1.md


This is your submission.

🟩 Step 7 — Submit your report

Based on how your instructor collects files:

Upload to LMS

Email

WhatsApp

or upload directly inside the SDV app (if enabled)

⭐ Sample Completed Report (What your output should look like)
# Scenario E1: Basic Drive & SOC Drop

## Objective
Understand how speed and battery SOC change during a simple 10-step drive.

## Steps (as performed)
1. Set Normal mode, throttle 40%.
2. Ran 10 steps.
3. Recorded speed and SOC.

## Collected Metrics
- Peak Speed: 57 km/h
- SOC Before: 94.3 %
- SOC After: 93.8 %

## Observations
Smooth acceleration. SOC drop is minimal.

## Interpretation
Normal mode uses less power; good for commuting.  
Higher drive modes will increase SOC loss.

## Recommendations
Repeat in Sport mode and compare.
