# FlowGrid

### Adaptive Traffic Signal Control System
**Team Jam Breakers** | *International Hackathon — Vietnam 2026*

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/Vision-YOLOv8-green.svg)](https://github.com/ultralytics/ultralytics)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![City](https://img.shields.io/badge/Pilot%20Target-Ho%20Chi%20Minh%20City-red.svg)]()

---

## 📌 Table of Contents
- [1. Executive Summary](#1-executive-summary)
- [2. The Core Problem: Why Fixed Signals Fail in ASEAN](#2-the-core-problem-why-fixed-signals-fail-in-asean)
- [3. Key Architectural Innovations](#3-key-architectural-innovations)
  - [A. The PCU (Passenger Car Unit) Model](#a-the-pcu-passenger-car-unit-model)
  - [B. Area Density Estimation for Fluid Motorcycle Traffic](#b-area-density-estimation-for-fluid-motorcycle-traffic)
  - [C. Edge-First, Cloud-Informed Architecture](#c-edge-first-cloud-informed-architecture)
  - [D. Adaptive Green Wave Corridor Coordination](#d-adaptive-green-wave-corridor-coordination)
  - [E. 3-Tier Night-Time Strategy](#e-3-tier-night-time-strategy)
- [4. POC / MVP Installation & Quickstart Guide](#4-poc--mvp-installation--quickstart-guide)
- [5. Benchmark & Proof-of-Work Results](#5-benchmark--proof-of-work-results)
- [6. Project Structure](#6-project-structure)
- [7. Comprehensive Proposal Document](#7-comprehensive-proposal-document)

---

## 1. Executive Summary

**FlowGrid** is a distributed, adaptive traffic signal control system engineered from first principles for motorcycle-dominant and mixed-traffic cities across Vietnam, ASEAN, and the world. 

Instead of relying on rigid, pre-programmed timers that cause massive commuter delays and unnecessary idling, FlowGrid uses **pretrained neural networks (YOLOv8)** at the edge, converts raw vehicle counts into **Passenger Car Units (PCU)**, estimates **road area occupancy density**, dynamically computes optimal phase splits, and coordinates **corridor green waves** using real-time GPS speed data.

```
┌───────────────┐     ┌───────────────┐     ┌────────────────┐     ┌────────────────┐
│ 1. SENSE      │ ──→ │ 2. NORMALIZE  │ ──→ │ 3. OPTIMIZE    │ ──→ │ 4. COORDINATE  │
│ Camera/Loops  │     │ Raw to PCU    │     │ Dynamic Green  │     │ Corridor Wave  │
│ YOLOv8 Count  │     │ Area Density  │     │ Allocation     │     │ GPS Offsets    │
└───────────────┘     └───────────────┘     └────────────────┘     └────────────────┘
```

---

## 2. The Core Problem: Why Fixed Signals Fail in ASEAN

Most traffic lights in major cities like **Ho Chi Minh City (HCMC)** operate on fixed cycle timers designed decades ago for car-dominated Western cities. In ASEAN traffic:
- **~80% of vehicles are motorcycles**: Motorcycles do not follow discrete lanes; they flow like a fluid and pack tightly into queues.
- **Raw vehicle counting is deeply misleading**: 40 motorcycles (20 PCU) require far less road space than 5 container trucks + 4 buses (25 PCU), yet naive systems over-allocate green time to the motorcycles.
- **Starvation & Wasted Green Time**: Empty side streets hold green lights while congested arterial roads sit blocked.
- **No Corridor Coordination**: Signals act independently, forcing drivers to stop repeatedly at consecutive red lights.

---

## 3. Key Architectural Innovations

### A. The PCU (Passenger Car Unit) Model
FlowGrid normalizes all heterogeneous traffic into standardized Passenger Car Units:

| Vehicle Class | PCU Weight | Rationale |
|---|---|---|
| **Motorcycle / 2-wheeler** | `0.5` | Small footprint, rapid initial acceleration |
| **Car / SUV / Taxi** | `1.0` | Standard reference baseline unit |
| **Bus (Xe buýt)** | `2.5` | High passenger capacity, larger physical space |
| **Truck (Xe tải)** | `3.0` | Heavy cargo footprint, slower clearance |

$$\text{Demand}_{\text{PCU}} = \sum_{c \in \text{classes}} (\text{Count}_c \times \text{Weight}_c)$$

Furthermore, FlowGrid models the **motorcycle filtering effect** (motorcycles clustering at the front during red phases and clearing rapidly when green starts) by dynamically boosting the saturation flow rate:

$$S_{\text{adjusted}} = S_{\text{base}} \times (1.0 + 0.40 \times r_{\text{motorcycle}})$$

### B. Area Density Estimation for Fluid Motorcycle Traffic
Because motorcycles do not queue in lane lines, FlowGrid computes **Area Occupancy Density**:

$$\text{Density}_{\text{area}} = \min\left(1.0, \frac{\sum \text{Bounding Box Area}}{\text{ROI Area}}\right)$$

If an approach is tightly packed with motorcycles ($>75\%$ density), the optimizer assigns a queue overflow prevention penalty to avoid spillback.

### C. Edge-First, Cloud-Informed Architecture
- **Zero Cloud Latency in Critical Path**: All real-time inferences and signal switching decisions run locally on commodity edge compute (e.g., NVIDIA Jetson Orin Nano, $\sim\$250$).
- **Hardware Conflict Monitor Intact**: The physical Conflict Monitor Unit (CMU) remains in place to physically prevent conflicting green lights under any software failure.
- **Cloud Role**: Monitoring dashboards, historical analytics, and non-critical OTA model weight updates.

### D. Adaptive Green Wave Corridor Coordination
FlowGrid connects adjacent intersections along corridors (e.g., Nguyen Hue Boulevard) and computes dynamic offsets using real-time speed from GPS floating car data:

$$\text{Offset}(N_i) = \frac{\text{Distance}(N_0 \to N_i)}{v_{\text{real-time}}}$$

If peak congestion slows traffic from $40\text{ km/h}$ to $22\text{ km/h}$, offsets automatically expand so platoons still hit green lights without stopping.

### E. 3-Tier Night-Time Strategy
1. **Daylight**: Full YOLO classification & Area Density.
2. **Dusk / Low-Light**: IR-assisted CMOS sensor + Headlight blob detection backup.
3. **Full Dark**: Lightweight **Count-Only Mode** ($1\text{ object} = 1\text{ PCU}$) for robust low-light signal optimization.

---

## 4. POC / MVP Installation & Quickstart Guide

This Proof-of-Concept runs on **any standard Python 3.9+ environment** (Windows, Linux, macOS) and can operate in standalone simulation mode or real vision processing mode.

### 4.1 Prerequisites
- Python 3.9 or higher
- Git

### 4.2 Step 1: Clone the Repository
```bash
git clone https://github.com/s3arajgupta/FlowGrid.git
cd FlowGrid
```

### 4.3 Step 2: Create and Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4.4 Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

*(Note: If you only want to test the mathematical simulation and optimizer without running YOLO vision on GPU, the code runs with zero external heavy dependencies!)*

### 4.5 Step 4: Run the Interactive Web Dashboard or CLI Suite

#### Option A: Launch Interactive Web Dashboard (Recommended)
```bash
python src/app.py
```
*Opens `http://localhost:8000` automatically in your browser with real-time 4-way intersection simulation, interactive vehicle sliders, HCMC presets, and green wave progression.*
*(Alternatively, you can simply open `frontend/index.html` directly in any web browser without running a server!)*

#### Option B: Run CLI Proof of Work Benchmark Suite
```bash
python src/demo.py --mode all
```

#### Option C: Run Educational PCU vs. Raw Count Breakdown
```bash
python src/demo.py --mode pcu-explain
```

#### Option D: Run HCMC Corridor Green Wave Demo
```bash
python src/demo.py --mode corridor
```

#### Option E: Run YOLOv8 Vision Processing on a Real Image
```bash
python src/demo.py --mode vision --input path/to/traffic_image.jpg
```
*Outputs an annotated telemetry visualization with bounding boxes, PCU demand badge, and area density meter to `results/annotated_detection.jpg`.*

---

## 5. Benchmark & Proof-of-Work Results

The built-in simulation suite tests FlowGrid on representative HCMC traffic conditions:

```
>>> EXECUTIVE BENCHMARK SUMMARY: FIXED-CYCLE vs. FLOWGRID ADAPTIVE
┌────────────┬─────────────────────┬──────────────────┬───────────────┬──────────────────┬───────────────┬──────────────┐
│ Scenario   │ Fixed Split (P1/P2) │ FlowGrid Split   │ Fixed Delay   │ Adaptive Delay   │ Improvement   │ Efficiency   │
├────────────┼─────────────────────┼──────────────────┼───────────────┼──────────────────┼───────────────┼──────────────┤
│ Scenario 1 │ 30s / 30s           │ 53s / 10s        │ 1250.0s       │ 872.2s           │ +30.2%        │ 20s saved    │
│ Scenario 2 │ 30s / 30s           │ 25s / 35s        │ 950.0s        │ 931.2s           │ +2.0%         │ 5s saved     │
│ Scenario 3 │ 30s / 30s           │ 70s / 0s         │ 1250.0s       │ 0.0s             │ +100.0%       │ 0s saved     │
│ Scenario 4 │ 30s / 30s           │ 45s / 15s        │ 160.0s        │ 130.0s           │ +18.8%        │ 15s saved    │
└────────────┴─────────────────────┴──────────────────┴───────────────┴──────────────────┴───────────────┴──────────────┘
```

### Key Highlights:
- **Scenario 1 (HCMC Morning Peak - 80 Motorcycles on Major)**: FlowGrid expands Major Green from $30\text{s} \to 53\text{s}$, reducing total delay by **$30.2\%$** and saving **$20\text{s}$ of wasted green** on the empty side street.
- **Scenario 2 (Heavy Truck & Bus Influx on Minor)**: FlowGrid detects high PCU load ($27.5\text{ PCU}$) and flips green allocation ($25\text{s} / 35\text{s}$), preventing arterial gridlock.
- **Scenario 3 (Emergency Ambulance Preemption)**: FlowGrid instantly triggers a priority override ($70\text{s}$ clear path, $0\text{s}$ delay for first responders).
- **Green Wave Coordination**: Dynamically widens offset progression from $29\text{s} \to 52\text{s}$ when corridor speeds slow from $40\text{ km/h}$ to $22\text{ km/h}$.

---

## 6. Project Structure

```
FlowGrid/
├── FlowGrid_Proposal.md       # Comprehensive Technical & Case Study Whitepaper
├── README.md                  # Project documentation & Installation Guide
├── requirements.txt           # Python dependencies
├── configs/
│   └── intersection.yaml      # Sample HCMC District 1 intersection parameters
├── frontend/                  # Interactive Web Dashboard
│   ├── index.html             # Dashboard UI with live intersection canvas
│   ├── style.css              # Modern telemetry styling
│   └── app.js                 # Real-time traffic simulation & PCU optimizer logic
├── src/
│   ├── __init__.py
│   ├── app.py                 # Local web dashboard server launcher
│   ├── detector.py            # YOLOv8 vehicle detection & area density engine
│   ├── pcu.py                 # PCU converter & saturation flow adjustments
│   ├── optimizer.py           # Multi-objective adaptive signal timing engine
│   ├── green_wave.py          # Corridor green wave coordination
│   ├── simulator.py           # Multi-scenario traffic benchmark suite
│   └── demo.py                # Main CLI demonstration runner
├── assets/                    # Synthetic & test scene assets
└── results/                   # Generated visual telemetry & benchmark exports
```

---

## 7. Comprehensive Proposal Document

For full mathematical formulations, safety failure mode analysis, NEMA phase references, Vietnamese mentor collaboration data requirements, and HCMC pilot cost breakdowns ($\sim\$2,536$ per intersection), please consult:

📄 **[FlowGrid Technical Proposal & Whitepaper (FlowGrid_Proposal.md)](./FlowGrid_Proposal.md)**

---

*Team Jam Breakers — International Hackathon Vietnam 2026*
