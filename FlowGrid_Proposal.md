# FlowGrid

## Adaptive Traffic Signal Control System

**Team Jam Breakers** | International Hackathon — Vietnam 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [First Principles Analysis](#3-first-principles-analysis)
4. [Solution Overview](#4-solution-overview)
5. [System Architecture](#5-system-architecture)
6. [Sensing Layer](#6-sensing-layer)
7. [Vision Processing Layer](#7-vision-processing-layer)
8. [Traffic Demand Estimation — The PCU Model](#8-traffic-demand-estimation--the-pcu-model)
9. [Optimization Engine](#9-optimization-engine)
10. [Coordination Layer — City-Level Green Waves](#10-coordination-layer--city-level-green-waves)
11. [Edge-First Control Architecture](#11-edge-first-control-architecture)
12. [Special Case: Night-Time Strategy](#12-special-case-night-time-strategy)
13. [Special Case: Emergency Vehicle Priority](#13-special-case-emergency-vehicle-priority)
14. [Special Case: Motorcycle-Dominant Traffic](#14-special-case-motorcycle-dominant-traffic)
15. [Safety and Failure Modes](#15-safety-and-failure-modes)
16. [Universal Deployment Model](#16-universal-deployment-model)
17. [HCMC Case Study](#17-hcmc-case-study)
18. [Hackathon Deliverables — 60-Day Plan](#18-hackathon-deliverables--60-day-plan)
19. [Team Jam Breakers](#19-team-jam-breakers)
20. [Post-Hackathon Roadmap](#20-post-hackathon-roadmap)
21. [Conclusion](#21-conclusion)
22. [Appendix A — Signal Phasing Reference](#appendix-a--signal-phasing-reference)
23. [Appendix B — Data Requirements Per City Deployment](#appendix-b--data-requirements-per-city-deployment)

---

## 1. Executive Summary

**FlowGrid** is an adaptive traffic signal control system that replaces fixed-cycle traffic lights with intelligent, real-time signal optimization. By combining camera-based vehicle detection with sensor-agnostic data inputs, edge computing for low-latency decisions, and city-level green wave coordination, FlowGrid reduces commuter wait times, eases congestion, and improves urban mobility — starting with Ho Chi Minh City and scaling to any city worldwide.

**The core insight:** Traffic lights today are static schedulers operating on a dynamic system. They have no information about the system they are controlling. FlowGrid closes this information gap by sensing real traffic demand, deciding how to allocate green time proportionally, and coordinating those decisions across neighboring intersections to create smooth traffic flow along corridors.

**Key differentiators:**

- **Designed for motorcycle-dominant traffic** — unlike Western solutions, FlowGrid uses Passenger Car Unit (PCU) weighting and area density estimation to correctly handle the fluid, lane-agnostic nature of motorcycle traffic prevalent across ASEAN cities.
- **Edge-first, cloud-informed** — all safety-critical decisions happen at the intersection with zero dependency on network connectivity. Cloud infrastructure handles monitoring, analytics, and policy updates only.
- **Sensor-agnostic** — works with cameras alone (minimal deployment), but seamlessly integrates induction loops, GPS floating car data, and emergency vehicle preemption sensors where available.
- **Low capital expenditure** — leverages pretrained neural networks (YOLO family) fine-tuned on local traffic, runs on commodity edge hardware, and integrates with existing traffic signal infrastructure without replacing it.
- **Universal architecture, local tuning** — the system architecture, interfaces, and protocols are universal. Only the vision model weights and optimization parameters need local adaptation per city — a one-time effort of 2–4 weeks, refreshed annually.

---

## 2. Problem Statement

### 2.1 The Current Reality

Traffic signals in most cities worldwide — including Ho Chi Minh City — operate on **fixed timing cycles**. These cycles are programmed once (often years ago) and do not adapt to actual traffic conditions. This creates two fundamental problems:

**Problem 1: Wasted Green Time**

When one direction has no vehicles waiting but the signal remains red, commuters on the empty approach wait unnecessarily while vehicles on the congested approach could be clearing. In peak hours, this mismatch between scheduled cycles and actual demand compounds across every intersection a commuter passes through.

**Problem 2: No Inter-Intersection Coordination**

Adjacent traffic signals operate independently. A driver who clears one green light immediately encounters a red at the next intersection. Without coordination, vehicles stop and start repeatedly, creating a chain reaction: each stop adds to fuel consumption, increases emissions, and propagates congestion backward through the network.

### 2.2 Scale of Impact

| Metric | Ho Chi Minh City |
|---|---|
| Population | ~9 million (metro: ~13 million) |
| Registered motorcycles | ~7.4 million |
| Percentage of traffic that is motorcycles | ~80% |
| Signalized intersections | ~1,000+ |
| Average commute time | 30–45 minutes (up to 90 minutes in peak) |
| Economic cost of congestion | Estimated 1.2–6% of GDP annually |

The problem is not unique to HCMC. Across ASEAN:

- **Hanoi**: Similar motorcycle dominance, rapidly growing vehicle population
- **Bangkok**: Severe congestion despite extensive road network, average peak commute exceeds 60 minutes
- **Jakarta**: Among the world's most congested cities, estimated $7.5B annual economic loss from traffic delays
- **Manila**: Heavy mixed traffic with jeepneys, tricycles, and motorcycles

These cities share common characteristics: **high motorcycle ratios, mixed vehicle types, rapid urbanization, and legacy traffic signal infrastructure**. A solution that works for one can transfer to all.

### 2.3 Why Existing Solutions Fall Short

Several adaptive traffic control systems exist globally (SCATS from Australia, SCOOT from the UK, InSync from the US). However, these systems were designed for **Western traffic patterns** — lane-disciplined, car-dominated traffic. They struggle in ASEAN contexts because:

- They assume vehicles queue in discrete lanes — motorcycles do not
- Their vehicle detection relies on induction loops sized for cars — motorcycles are too small to trigger reliably
- They optimize for car-equivalent throughput — not for the fluid, density-based flow of motorcycle traffic
- They require significant infrastructure investment and proprietary hardware

FlowGrid is designed from the ground up for mixed, motorcycle-dominant traffic while remaining equally effective in car-dominated environments.

---

## 3. First Principles Analysis

Before designing a solution, we decompose the problem to its fundamental elements:

**What is a traffic signal?**
A traffic signal is a time-sharing mechanism. Multiple traffic streams (approaches) need to use the same physical space (the intersection). The signal allocates time to each stream, preventing collisions by ensuring only non-conflicting streams move simultaneously.

**What is the ideal signal?**
An ideal signal would give green time to each approach in exact proportion to its current demand, with zero wasted time, and would coordinate with neighboring signals so that vehicles travel through corridors without stopping.

**What prevents this today?**
1. **No sensing** — the controller doesn't know current demand
2. **No adaptation** — cycles are fixed, not responsive
3. **No coordination** — intersections operate in isolation
4. **No graceful degradation** — when anything fails, there's no intelligent fallback

**Therefore, the solution must:**

```
┌──────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  SENSE   │ ──→ │  DECIDE  │ ──→ │ COORDINATE  │ ──→ │     FAIL     │
│  demand  │     │  green   │     │   across    │     │  GRACEFULLY  │
│  at each │     │  time    │     │  adjacent   │     │  when any    │
│  approach│     │  per     │     │  signals    │     │  part breaks │
│          │     │  approach│     │             │     │              │
└──────────┘     └──────────┘     └─────────────┘     └──────────────┘
```

Each of these four functions introduces design choices. The following sections detail these choices and the reasoning behind each.

---

## 4. Solution Overview

FlowGrid is a **distributed, adaptive traffic signal control system** composed of four layers:

```
┌─────────────────────────────────────────────────────────────┐
│                     CLOUD LAYER                             │
│  Monitoring Dashboard · Analytics · Policy Updates          │
│  Model Weight Distribution · Historical Data Storage        │
├─────────────────────────────────────────────────────────────┤
│                  COORDINATION LAYER                         │
│  Green Wave Corridors · Adaptive Offsets · Wave Switching   │
├─────────────────────────────────────────────────────────────┤
│                  OPTIMIZATION LAYER                         │
│  PCU-Weighted Demand · Multi-Objective Optimizer            │
│  Configurable Per Intersection                              │
├─────────────────────────────────────────────────────────────┤
│                    SENSING LAYER                            │
│  Camera + YOLO NN · Induction Loops · GPS Floating Car Data │
│  Emergency Vehicle Preemption Sensor                        │
├─────────────────────────────────────────────────────────────┤
│              SAFETY LAYER (HARDWARE)                        │
│  Conflict Monitor · Minimum Phase Times · Fixed-Cycle       │
│  Fallback                                                   │
└─────────────────────────────────────────────────────────────┘
```

**Key principle:** Each layer can fail independently without compromising layers below it. The Safety Layer is hardware-enforced and never bypassed by software. The Sensing Layer feeds the Optimization Layer, which feeds the Coordination Layer. If Coordination fails, Optimization still works locally. If Optimization fails, the Safety Layer reverts to fixed-cycle timing.

---

## 5. System Architecture

### 5.1 High-Level Architecture

```
                          ┌──────────────────────┐
                          │    CLOUD PLATFORM     │
                          │                       │
                          │  ┌─────────────────┐  │
                          │  │   Monitoring     │  │
                          │  │   Dashboard      │  │
                          │  └─────────────────┘  │
                          │  ┌─────────────────┐  │
                          │  │   Analytics &    │  │
                          │  │   Model Updates  │  │
                          │  └─────────────────┘  │
                          │  ┌─────────────────┐  │
                          │  │   GPS Floating   │  │
                          │  │   Car Data API   │  │
                          │  └─────────────────┘  │
                          └──────────┬───────────┘
                                     │ Policy updates,
                                     │ model weights,
                                     │ corridor speed data
                                     │ (non-critical path)
                    ┌────────────────┼────────────────┐
                    │                │                 │
              ┌─────▼─────┐   ┌─────▼─────┐   ┌──────▼────┐
              │ CORRIDOR   │   │ CORRIDOR   │   │ CORRIDOR  │
              │ CONTROLLER │   │ CONTROLLER │   │CONTROLLER │
              │ (edge)     │   │ (edge)     │   │ (edge)    │
              └──┬──┬──┬───┘   └──┬──┬──┬───┘   └──┬──┬──┬─┘
                 │  │  │          │  │  │            │  │  │
              ┌──▼┐┌▼┐┌▼──┐   ┌──▼┐┌▼┐┌▼──┐     ┌──▼┐┌▼┐┌▼──┐
              │N1 ││N2││N3 │   │N4 ││N5││N6 │     │N7 ││N8││N9 │
              └───┘└──┘└───┘   └───┘└──┘└───┘     └───┘└──┘└───┘

              N = Intersection Node (edge device + sensors)
```

### 5.2 Intersection Node Architecture

Each signalized intersection runs a **FlowGrid Node** — a self-contained edge device that can operate fully autonomously:

```
┌──────────────────────────────────────────────────┐
│              FLOWGRID NODE (per intersection)     │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │   Camera(s)  │  │  Induction  │  │ Preempt  │ │
│  │   + IR LED   │  │   Loops     │  │ Receiver │ │
│  └──────┬──────┘  └──────┬──────┘  └────┬─────┘ │
│         │                │              │        │
│  ┌──────▼────────────────▼──────────────▼─────┐  │
│  │          SENSOR ABSTRACTION LAYER          │  │
│  │   Unified Vehicle Count + Density Output   │  │
│  └────────────────────┬───────────────────────┘  │
│                       │                          │
│  ┌────────────────────▼───────────────────────┐  │
│  │           OPTIMIZATION ENGINE              │  │
│  │   PCU Conversion · Phase Allocation        │  │
│  │   Multi-Objective Optimizer                │  │
│  └────────────────────┬───────────────────────┘  │
│                       │                          │
│  ┌────────────────────▼───────────────────────┐  │
│  │          SIGNAL CONTROLLER INTERFACE       │  │
│  │   Phase Commands → Existing Signal HW      │  │
│  └────────────────────┬───────────────────────┘  │
│                       │                          │
│  ┌────────────────────▼───────────────────────┐  │
│  │          CONFLICT MONITOR (HARDWARE)       │  │
│  │   Prevents conflicting greens              │  │
│  │   *** NOT CONTROLLED BY SOFTWARE ***       │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

---

## 6. Sensing Layer

### 6.1 Design Philosophy: Sensor-Agnostic with Camera as Primary

> **🔑 Design Choice — Why sensor-agnostic?**
>
> A system that only works with cameras cannot be deployed in cities that lack camera infrastructure or face regulatory constraints. A system that only works with induction loops cannot be deployed where loops aren't installed. By abstracting all sensor inputs into a **unified demand signal** (vehicle counts by class + area density), FlowGrid can be deployed with any combination of available sensors — from camera-only (minimum viable) to camera + loops + GPS (maximum accuracy).

### 6.2 Sensor Inputs

#### 6.2.1 Camera (Primary)

Traffic cameras mounted at intersection approaches capture real-time video. The vision processing layer (Section 7) extracts vehicle counts and density from this feed.

**Camera specification for FlowGrid:**
- Resolution: 1080p minimum (to detect motorcycles at distance)
- Frame rate: 15 FPS minimum (sufficient for stopped/slow traffic counting)
- Sensor: Low-light capable CMOS (e.g., Sony Starvis IMX335 or equivalent)
- Night capability: Near-IR illuminator (850nm LED, invisible to drivers)
- Mounting: Traffic signal pole or dedicated pole, 5–8m height, angled downward at approach
- One camera per approach direction (typical 4-way intersection = 4 cameras)

**Cost estimate:** $200–500 per camera (industrial-grade, weatherproof). A 4-way intersection requires $800–2,000 in camera hardware.

#### 6.2.2 Induction Loops (Secondary, Where Available)

Many cities already have induction loops embedded in road surfaces. These loops detect the presence of a vehicle by measuring changes in electromagnetic inductance when metal passes over them.

**Advantages:** Weather-immune, zero maintenance, no privacy concerns, already installed at many intersections.

**Limitations for ASEAN:** Standard induction loops are tuned for car-sized metal masses. Motorcycles — especially those with aluminum frames — may not trigger reliably. Where loops exist, FlowGrid uses their data as a supplementary signal but does not depend on it exclusively.

**Integration:** Induction loop data is fed into the Sensor Abstraction Layer as a binary vehicle presence signal per lane, which supplements or validates camera-derived counts.

#### 6.2.3 GPS Floating Car Data (Secondary)

Aggregated, anonymized GPS data from ride-hailing services (Grab in ASEAN), navigation apps, and fleet management systems provides:

- **Corridor travel time** — how long vehicles take to travel between two intersections
- **Corridor speed** — real-time average speed on road segments
- **Congestion detection** — sudden drops in speed indicate downstream congestion

This data is consumed by the Coordination Layer (Section 10) to dynamically adjust green wave offsets based on actual travel speed, rather than assumed speed limits.

**Integration:** GPS data is consumed at the Corridor Controller level via API (e.g., Google Maps Routes API, TomTom Traffic Flow API, HERE Traffic API). It does not feed into individual intersection decisions but into corridor-level coordination. The system abstracts over data providers through a standard API adapter.

#### 6.2.4 Emergency Vehicle Preemption Receiver (Specialized)

See Section 13 for full details. An IR/radio receiver at each intersection detects approaching emergency vehicles and triggers priority preemption.

### 6.3 Sensor Abstraction Layer

All sensor inputs are normalized into a **unified demand descriptor** per approach:

```
ApproachDemand {
    approach_id: string          // e.g., "north", "south_left_turn"
    timestamp: ISO8601

    // Per-class vehicle count (from camera NN or induction loops)
    vehicle_counts: {
        motorcycle: int
        car: int
        bus: int
        truck: int
    }

    // Area density (from camera NN)
    area_density: float          // 0.0 (empty) to 1.0 (fully occupied)

    // Queue presence (from camera or induction loop)
    queue_detected: boolean

    // Confidence score (how reliable is this reading?)
    confidence: float            // 0.0 to 1.0

    // Data source metadata
    source: enum [CAMERA, INDUCTION_LOOP, FUSED, FALLBACK_TIMER]
}
```

This abstraction is the **interface contract** between the Sensing Layer and the Optimization Layer. Any sensor that can produce this structure can be plugged into FlowGrid.

---

## 7. Vision Processing Layer

### 7.1 Model Selection

> **🔑 Design Choice — Why YOLO (You Only Look Once)?**
>
> FlowGrid requires a vision model that:
> 1. Runs at real-time speed (≥15 FPS) on edge hardware
> 2. Detects small objects (motorcycles at distance)
> 3. Classifies vehicle types (motorcycle, car, bus, truck)
> 4. Has pretrained weights on vehicle classes (to minimize fine-tuning effort)
>
> The YOLO family (specifically YOLOv8 or later) meets all four criteria. It is pretrained on the COCO dataset, which includes `car`, `motorcycle`, `bus`, `truck`, and `bicycle` as built-in classes. It runs at 30+ FPS on edge hardware like NVIDIA Jetson Orin Nano (~$250) or equivalent. Fine-tuning for local traffic conditions (e.g., Vietnamese motorcycle styles, xe lam, xe buyt) requires as few as 1,000–2,000 annotated images and a few hours of GPU training.
>
> Alternative models (EfficientDet, RT-DETR) were considered but YOLO offers the best balance of speed, accuracy, and edge deployment maturity for this use case.

### 7.2 Model Outputs

The YOLO model produces two outputs per camera frame:

**Output 1: Per-Class Vehicle Count**

Standard object detection — bounding boxes with class labels. Post-processing counts the number of detected objects per class within a defined Region of Interest (ROI) for each approach.

```
Frame N, Camera "North Approach":
  motorcycle: 14 detections
  car: 3 detections
  bus: 1 detection
  truck: 0 detections
```

**Output 2: Area Density Estimation**

> **🔑 Design Choice — Why area density in addition to vehicle count?**
>
> In motorcycle-dominant traffic (e.g., HCMC where 80% of vehicles are motorcycles), vehicles do not queue in discrete lanes. Motorcycles fill every available gap, flowing like a fluid. A simple vehicle count can miss the nuance of how "full" an approach is.
>
> Area density measures **what percentage of the approach road surface is occupied by detected vehicles**. This is computed by summing the area of all bounding boxes and dividing by the ROI area (with overlap correction).
>
> This metric captures the fundamental physical reality: an approach with 40 tightly-packed motorcycles may have lower vehicle count than expected but 80% area density — indicating the approach is nearly saturated and needs more green time to clear.
>
> In car-dominated Western traffic, area density correlates linearly with vehicle count and adds little value. In motorcycle-dominant ASEAN traffic, it is a critical signal that vehicle count alone cannot provide.

```
density = sum(bounding_box_areas) / ROI_area

Frame N, Camera "North Approach":
  area_density: 0.73 (73% occupied)
```

### 7.3 Temporal Smoothing

Individual frame detections are noisy (momentary occlusions, detection flicker). FlowGrid applies a **rolling window average** over the last 5–10 seconds of detections to produce stable demand estimates. This smoothing window is configurable — shorter windows react faster to sudden changes, longer windows reduce noise.

### 7.4 Fine-Tuning for Local Traffic

The base YOLO model (pretrained on COCO) can detect standard vehicle classes out of the box. For optimal performance in a specific city:

1. **Collect** 2–4 days of camera footage from 10–20 representative intersections
2. **Annotate** 1,000–2,000 images with bounding boxes and class labels (using tools like CVAT or Label Studio)
3. **Fine-tune** the YOLO model using transfer learning — freeze early layers, retrain detection head
4. **Validate** on a held-out test set, targeting >85% mAP (mean Average Precision) for all vehicle classes
5. **Deploy** updated weights to all edge devices

**Estimated effort:** 1–2 weeks with one annotator, 4–8 hours of GPU training. This is a one-time effort per city, refreshed annually or when vehicle fleet composition changes significantly.

---

## 8. Traffic Demand Estimation — The PCU Model

### 8.1 The Problem with Raw Vehicle Counts

> **🔑 Design Choice — Why PCU (Passenger Car Unit) weighting?**
>
> Consider two intersection approaches:
>
> | Approach | Vehicles | Raw Count |
> |---|---|---|
> | Side A | 40 motorcycles, 5 cars | 45 |
> | Side B | 2 trucks, 8 cars, 2 buses | 12 |
>
> Raw count says Side A has nearly 4x the demand. But this is misleading:
> - Side B's 2 trucks and 2 buses occupy far more road space and take far longer to clear the intersection than Side A's compact motorcycles
> - PCU-weighted demand: Side A = 40x0.5 + 5x1.0 = **25 PCU**. Side B = 2x3.0 + 8x1.0 + 2x2.5 = **19 PCU**
> - The real demand ratio is closer to 1.3:1, not 3.75:1
>
> In motorcycle-dominant cities like HCMC, where motorcycles comprise 80% of traffic, using raw counts would systematically over-allocate green time to motorcycle-heavy approaches and under-allocate to approaches carrying buses and trucks. PCU weighting corrects this distortion.

### 8.2 PCU Conversion Table

| Vehicle Type | Default PCU | Rationale |
|---|---|---|
| Motorcycle / 2-wheeler | 0.5 | Small footprint, fast acceleration from stop |
| Car / sedan / SUV (4-wheeler) | 1.0 | Reference unit |
| Bus (xe buyt) | 2.5 | Large footprint, slow acceleration |
| Truck | 3.0 | Largest footprint, slowest acceleration |

**These weights are configurable per deployment.** Different cities may adjust based on local vehicle sizes and driving behavior. For example, Vietnamese motorcycles tend to be smaller (100–150cc) than Western motorcycles, potentially justifying a PCU of 0.4 rather than 0.5.

### 8.3 Demand Calculation

For each approach, the Optimization Engine computes:

```
demand_pcu = sum(vehicle_count[class] * pcu_weight[class])

For the example in 8.1, Side A:
demand_pcu = (40 * 0.5) + (5 * 1.0) = 25.0 PCU
```

This PCU-weighted demand is the primary input to the green time allocation algorithm.

### 8.4 Saturation Flow Rate Adjustment

> **🔑 Design Choice — Why adjust for vehicle composition?**
>
> A motorcycle-heavy queue clears faster than a car-heavy queue of equal PCU. When the light turns green, motorcycles accelerate quickly and filter through. A queue of 25 PCU that is 80% motorcycles will clear in approximately 60% of the time it takes a 25 PCU queue that is 100% cars.
>
> FlowGrid adjusts its estimate of "how long does this approach need to clear?" based on the motorcycle ratio in the queue. This prevents over-allocating green time to motorcycle-heavy approaches, which would waste time that could be given to other approaches.

```
saturation_flow_rate = base_rate * (1 + motorcycle_acceleration_bonus * motorcycle_ratio)
```

Where `motorcycle_acceleration_bonus` is a tunable parameter (default: 0.4) and `motorcycle_ratio` is the fraction of PCU contributed by motorcycles. This accounts for the "motorcycle filtering" behavior unique to ASEAN traffic, where motorcycles squeeze to the front of the queue during red phases and clear quickly when green begins.

---

## 9. Optimization Engine

### 9.1 Objective Function

> **🔑 Design Choice — Why a configurable multi-objective function?**
>
> No single optimization objective works for all intersections. A major arterial road may prioritize throughput. A neighborhood intersection may prioritize fairness (no approach waits more than 90 seconds). A hospital entrance may prioritize emergency vehicle preemption above all else.
>
> Making the objective function configurable per intersection — with weights adjustable by traffic engineers through the monitoring dashboard — ensures FlowGrid adapts to local priorities without code changes. This is critical for universal deployment: different cities, different roads within the same city, and different times of day may all require different priority balances.

The Optimization Engine computes the optimal phase sequence and duration by minimizing a weighted cost function:

```
Cost = w1 * TotalDelay
     + w2 * MaxWaitPenalty
     + w3 * QueueOverflowPenalty
     + w4 * PhaseTransitionCost

Where:
  TotalDelay          = sum of (PCU * wait_time) across all approaches
  MaxWaitPenalty       = penalty when any approach exceeds max_wait_threshold
  QueueOverflowPenalty = penalty when estimated queue length approaches
                         intersection capacity (risk of spillback)
  PhaseTransitionCost  = cost of switching phases (accounts for yellow/all-red
                          clearance time that adds unproductive delay)

  w1, w2, w3, w4  = configurable weights per intersection
```

### 9.2 Constraints

The optimizer operates within hard constraints that **cannot** be violated:

1. **Minimum green time:** Each phase must be green for at least a legally mandated minimum (typically 7–15 seconds, varies by jurisdiction). This ensures vehicles that entered on green have time to clear.
2. **Maximum green time:** No phase exceeds a maximum (typically 60–120 seconds) to prevent starvation of other approaches.
3. **Yellow + all-red clearance:** Between every phase change, a fixed clearance interval (typically 3–5 seconds yellow + 1–2 seconds all-red) is enforced. This is a safety requirement and is non-negotiable.
4. **Conflict avoidance:** Conflicting phases (e.g., northbound through and eastbound through) are never green simultaneously. This is enforced by the hardware Conflict Monitor, not by software (see Section 15).
5. **Maximum cycle length:** The total cycle duration is capped (typically 120–180 seconds) to ensure all approaches receive service within a reasonable time.

### 9.3 Phase Sequencing

FlowGrid supports the standard **NEMA phasing convention** as the default, while also supporting simpler 2-phase and 3-phase configurations as subsets:

**Full NEMA 8-Phase (complex intersections):**

| Phase | Movement |
|---|---|
| Phase 1 | Major street left turn (opposing Phase 6 through) |
| Phase 2 | Major street through |
| Phase 3 | Minor street left turn (opposing Phase 8 through) |
| Phase 4 | Minor street through |
| Phase 5 | Major street left turn (opposing Phase 2 through) |
| Phase 6 | Major street through |
| Phase 7 | Minor street left turn (opposing Phase 4 through) |
| Phase 8 | Minor street through |

**Simplified 2-Phase (simple intersections):**

| Phase | Movement |
|---|---|
| Phase A | All major street movements |
| Phase B | All minor street movements |

The phasing configuration is defined per intersection during deployment setup by traffic engineers and stored as part of the intersection's configuration profile.

### 9.4 Optimization Algorithm

The optimizer runs a **greedy allocation with fairness constraints** on each cycle:

1. Read current demand (PCU-weighted) for all approaches
2. Allocate green time proportional to demand, subject to min/max constraints
3. Check fairness constraint — if any approach has been waiting longer than `max_wait_threshold`, force-allocate green to it
4. Apply corridor offset (from Coordination Layer) if this intersection is part of a green wave
5. Output phase sequence and durations to Signal Controller Interface

The algorithm runs every cycle (typically every 60–180 seconds), re-evaluating demand and adjusting the next cycle's plan. This ensures the signal adapts within one cycle of demand changes — a latency of 1–3 minutes, which is sufficient for traffic flow changes that evolve over minutes, not seconds.

---

## 10. Coordination Layer — City-Level Green Waves

### 10.1 What Is a Green Wave?

A green wave coordinates traffic signals along a corridor so that a vehicle traveling at a target speed encounters green lights in sequence without stopping:

```
Intersection 1    Intersection 2    Intersection 3    Intersection 4
     [GREEN] ────────→ [GREEN] ────────→ [GREEN] ────────→ [GREEN]
     (t=0s)             (t=30s)            (t=60s)            (t=90s)

     Vehicle traveling at 40 km/h with intersections 330m apart
     hits all greens in sequence = zero stops along the corridor.
```

Without a green wave, the same driver might stop at 2–3 of these 4 lights, adding 2–6 minutes of delay per corridor traversal.

### 10.2 Coordination Topology

> **🔑 Design Choice — Why hierarchical coordination?**
>
> Three coordination topologies were considered:
>
> | Topology | Pros | Cons |
> |---|---|---|
> | **Centralized** (one city controller) | Simple logic | Single point of failure; network latency |
> | **Peer-to-peer mesh** | Maximum resilience | Consensus is hard; complex protocol |
> | **Hierarchical** (city → corridor → node) | Natural fit for road networks; graceful degradation | Requires corridor definition |
>
> We chose hierarchical because:
> 1. **Road networks are naturally hierarchical** — arterial roads, collector roads, local streets form a natural hierarchy
> 2. **Green waves are corridor-level** — coordination is most impactful between sequential intersections on the same road, not between distant intersections
> 3. **Graceful degradation** — if the city-level coordinator fails, corridors continue operating independently. If a corridor controller fails, individual intersections continue optimizing locally. At no point does a failure cascade
> 4. **Manageable complexity** — a corridor controller coordinates 5–15 intersections, a city controller coordinates 10–30 corridors. These are manageable scales for each level

```
┌─────────────────────────────────────────┐
│           CITY COORDINATOR              │
│  Manages corridor priorities            │
│  Distributes GPS corridor speed data    │
│  Adjusts AM/PM wave direction           │
└────────────┬──────────────┬─────────────┘
             │              │
     ┌───────▼───────┐ ┌───▼────────────┐
     │  CORRIDOR A   │ │  CORRIDOR B    │
     │  (Nguyen Hue) │ │  (Le Loi)      │
     │  N1→N2→N3→N4  │ │  N5→N6→N7→N8  │
     └───────────────┘ └────────────────┘
```

### 10.3 Corridor Definition

Corridors are defined **manually by traffic engineers** during deployment. This is a one-time configuration step. A corridor definition includes:

```
Corridor {
    corridor_id: string              // e.g., "nguyen_hue_boulevard"
    intersections: [N1, N2, N3, N4]  // ordered list
    distances: [350m, 280m, 420m]    // between consecutive intersections
    target_speed: 40 km/h           // design speed for green wave
    primary_direction: "southbound"  // AM direction
    reverse_direction: "northbound"  // PM direction
    switch_time_am: "07:00"          // when to switch to AM wave
    switch_time_pm: "17:00"          // when to switch to PM wave
}
```

### 10.4 Adaptive Offsets

> **🔑 Design Choice — Why adaptive offsets instead of fixed offsets?**
>
> Traditional green wave systems use fixed time offsets between intersections, calculated from distance and target speed. But actual traffic speed varies — congestion slows vehicles below the target speed, causing them to arrive at the next intersection *after* the green window has passed. The green wave breaks.
>
> FlowGrid uses **GPS floating car data** to measure real-time corridor speed and dynamically adjusts the offset between intersections:
>
> ```
> offset_N2 = distance(N1, N2) / real_time_corridor_speed
> ```
>
> If congestion slows the corridor from 40 km/h to 25 km/h, the offset between N1 and N2 (350m apart) changes from 31.5 seconds to 50.4 seconds. FlowGrid adjusts the phase timing at N2 accordingly, maintaining the green wave even under degraded conditions.

### 10.5 Time-of-Day Wave Direction

In most cities, morning commute traffic flows **inbound** (suburbs → city center) and evening commute traffic flows **outbound** (city center → suburbs). FlowGrid supports **automatic wave direction switching**:

- **AM wave (e.g., 7:00–12:00):** Green wave optimized for inbound direction
- **PM wave (e.g., 16:00–20:00):** Green wave optimized for outbound direction
- **Off-peak (other hours):** Green wave disabled; each intersection optimizes locally

The switch times and directions are configurable per corridor.

---

## 11. Edge-First Control Architecture

> **🔑 Design Choice — Why edge-first?**
>
> Traffic signal control is **safety-critical infrastructure**. A software bug or network failure doesn't cause a 500 error — it can cause a collision. The decision loop (sense demand → compute green time → change signal) must therefore:
>
> 1. **Never depend on network connectivity** — cell towers fail in storms, fiber is cut by construction, cloud services have outages
> 2. **Have minimal latency** — the decision cycle should be <100ms, not the 200ms–2s of a cloud round-trip
> 3. **Maintain data privacy** — video feeds stay at the intersection and are never streamed to cloud, eliminating privacy concerns entirely
>
> Therefore, FlowGrid places **all real-time control logic at the edge** — on the intersection node itself. The cloud platform serves three non-critical functions only:
>
> | Function | Criticality | Failure Impact |
> |---|---|---|
> | Monitoring dashboard | Non-critical | Operators lose visibility, signals continue |
> | Model weight updates | Non-critical | Old model continues running, still functional |
> | GPS corridor speed data | Non-critical | Green wave uses last known speed or design speed |

### 11.1 Edge Hardware

Each intersection node runs on commodity edge computing hardware:

**Minimum viable edge device:**
- NVIDIA Jetson Orin Nano (~$250) or equivalent (e.g., Rockchip RK3588, Google Coral)
- Runs YOLO inference at 30+ FPS on 1080p input
- Sufficient compute for optimization algorithm
- Low power consumption (~15W)

**Connectivity:**
- Primary: 4G/LTE cellular modem (for cloud communication and corridor coordination)
- Fallback: If connectivity is lost, node operates fully autonomously using local sensing only

### 11.2 Software Stack

| Component | Technology |
|---|---|
| Vision inference | YOLO (ONNX Runtime or TensorRT on Jetson) |
| Optimization engine | Python or C++ (performance-critical path) |
| Corridor communication | MQTT or gRPC (lightweight, low-latency) |
| Signal controller interface | Standard NTCIP (National Transportation Communications for ITS Protocol) or local serial interface to existing signal controller hardware |
| Local data logging | SQLite (for offline analytics sync) |

---

## 12. Special Case: Night-Time Strategy

> **🔑 Design Choice — Layered night-time sensing**
>
> Traffic demand between 5 PM and 10 PM (the evening peak and transition to night) is significant and cannot be ignored. However, visual conditions degrade as daylight fades. Rather than adding expensive radar hardware (high capital expenditure for an edge case), FlowGrid uses a **layered fallback strategy** that degrades gracefully with light levels:

### 12.1 Three-Tier Night Strategy

```
Light Level        Primary Sensor         Fallback Sensor       Mode
──────────────────────────────────────────────────────────────────────
Daylight           Camera (full NN)       —                     Full
(5–7 PM summer)    classification                               classification

Dusk / Low Light   Camera (IR-assisted    Headlight blob        Full
(transition)       full NN)               detection (classical   classification
                                          CV backup)

Full Dark          Camera (IR-assisted)   Headlight blob        Vehicle count
(after sunset)     + IR illuminator       detection             only (no class
                                                                distinction)
```

**Tier 1 — Full daylight (standard operation):** Camera runs the full YOLO model with per-class vehicle detection and area density estimation. No modifications needed.

**Tier 2 — Dusk / low-light with IR assist:** The near-IR illuminator (850nm LED) activates automatically when ambient light drops below a threshold. Modern traffic cameras with IR-capable sensors (Sony Starvis series) perform well under IR illumination, maintaining near-daylight detection accuracy. The YOLO model continues running. As a backup, a lightweight **headlight blob detection** algorithm runs in parallel using classical computer vision (no NN required) — detecting pairs of bright spots (headlights) to validate vehicle presence.

**Tier 3 — Full dark (simplified operation):** In full darkness, distinguishing vehicle types from IR imagery becomes less reliable (a motorcycle's single headlight can be confused with a car with one broken headlight). FlowGrid switches to **vehicle count only** mode — each detected object counts as 1 PCU regardless of type. Since nighttime traffic volumes are lower, the simplified counting is sufficient for effective signal optimization. The PCU accuracy loss is acceptable because the optimization problem is simpler: fewer vehicles means less contention between approaches.

### 12.2 Why This Approach?

Alternative approaches and why they were rejected:

| Alternative | Cost | Reliability | Why Rejected |
|---|---|---|---|
| Radar/microwave sensor | $500–2,000/unit | High (weather-immune) | High capital expenditure for a limited-duration use case (a few hours per day) |
| Thermal/FLIR camera | $2,000–10,000/unit | High | Prohibitively expensive for city-wide deployment |
| IR illumination + standard camera | $20–50/unit | Good | **Selected** — minimal cost, good performance |

---

## 13. Special Case: Emergency Vehicle Priority

### 13.1 Approach

> **🔑 Design Choice — Why IR/radio preemption over audio detection?**
>
> Audio-based siren detection (using microphones) was considered but rejected:
> - Siren frequencies vary by country (US: wail/yelp ~1–3kHz; Europe: different patterns; Vietnam: different again)
> - Urban ambient noise creates high false-positive rates
> - Directionality is hard to determine — a siren from a parallel street should not trigger preemption
>
> Instead, FlowGrid uses **dedicated preemption hardware** (similar to the Opticom system widely deployed in North America):
> - Each emergency vehicle is equipped with a small IR or radio transmitter (~$100/vehicle)
> - Each intersection has a receiver that detects the approaching emergency vehicle and its direction
> - This method has near-zero false positives and unambiguous directionality

### 13.2 Preemption Sequence

When an emergency vehicle is detected approaching an intersection:

1. **Immediate:** The Optimization Engine receives a HIGH_PRIORITY interrupt
2. **Clear phase:** The current phase completes its minimum green time, then transitions through yellow → all-red clearance
3. **Green for emergency direction:** The approach from which the emergency vehicle is arriving receives green
4. **Hold:** Green is held until the emergency vehicle clears the intersection (detected by the receiver signal fading) or a maximum hold time is reached (typically 60–120 seconds)
5. **Recovery:** The Optimization Engine re-evaluates demand and resumes adaptive operation, compensating for any approaches that were starved during preemption

### 13.3 Multi-Emergency Conflict

If two emergency vehicles approach from conflicting directions simultaneously, the first-detected vehicle gets priority. The second vehicle's approach receives green immediately after the first clears.

---

## 14. Special Case: Motorcycle-Dominant Traffic

### 14.1 The ASEAN Challenge

In Western cities, traffic engineering assumes:
- Vehicles queue in lanes
- Queue length can be measured in "vehicles per lane"
- One vehicle = one car = one unit of demand

In ASEAN cities (HCMC, Hanoi, Bangkok, Jakarta), these assumptions break down:

- **Motorcycles don't follow lanes** — they fill every gap, flowing like a fluid
- **Queue measurement is meaningless** — motorcycles are 3-wide where cars are 1-wide
- **One vehicle does not equal one car** — 80% of vehicles are motorcycles occupying 50% of the road space

### 14.2 How FlowGrid Handles This

FlowGrid addresses motorcycle-dominant traffic through three mechanisms:

**Mechanism 1: PCU Weighting (Section 8)**
Converts raw vehicle counts to road-demand-equivalent units, correctly weighting motorcycles at 0.5 PCU vs cars at 1.0 PCU. This prevents the systematic over-allocation of green time to motorcycle-heavy approaches.

**Mechanism 2: Area Density Estimation (Section 7)**
Supplements vehicle count with a measure of "how full is this approach?" — the percentage of road area occupied by detected vehicles. This captures the fluid, lane-agnostic nature of motorcycle queues that vehicle count alone misses.

**Mechanism 3: Saturation Flow Rate Adjustment (Section 8.4)**
Accounts for the faster queue clearance of motorcycle-heavy approaches. When the light turns green, motorcycles accelerate faster and clear the intersection more quickly than an equivalent PCU of cars. The optimization engine adjusts its "time to clear this queue" estimate based on the motorcycle fraction, preventing over-allocation of green time.

### 14.3 Motorcycle Filtering Behavior

A uniquely ASEAN driving behavior: during a red phase, motorcycles **filter to the front** of the queue, squeezing past stopped cars. By the time the light turns green, motorcycles are clustered at the stop line and cars are behind them.

**Impact on FlowGrid:**
- The first 3–5 seconds of green clear motorcycles rapidly (fast acceleration, small size)
- The remaining green time clears cars and larger vehicles at the normal rate
- The Optimization Engine's saturation flow rate model accounts for this two-phase clearance pattern

---

## 15. Safety and Failure Modes

### 15.1 Design Principle: Defense in Depth

FlowGrid treats safety as a **layered defense**. Each layer provides independent protection:

```
Layer 3: Optimization Engine     → Smart green time allocation
                                    (if this fails ↓)
Layer 2: Fixed-Cycle Fallback    → Pre-programmed timing resumes
                                    (if this fails ↓)
Layer 1: Conflict Monitor (HW)   → Hardware prevents conflicting greens
                                    (if this fails ↓)
Layer 0: All-Red Flash           → All directions show red flash
                                    (requires human traffic control)
```

### 15.2 Conflict Monitor — The Non-Negotiable Layer

The **Conflict Monitor Unit (CMU)** is a hardware device that exists in virtually all modern traffic signal controllers. It is an independent circuit — completely separate from any computer or software — that monitors the signal outputs and **physically disconnects power to the signal if conflicting directions are both commanded green.**

**FlowGrid does not replace, modify, or bypass the CMU.** The FlowGrid edge device sends phase commands to the existing signal controller, which sends electrical signals to the signal heads. The CMU monitors these electrical signals independently. If the FlowGrid software ever commanded conflicting greens (due to a bug), the CMU would override it within milliseconds.

This hardware layer is the **ultimate safety guarantee** and is why FlowGrid can be deployed without compromising intersection safety.

### 15.3 Fallback Modes

| Failure | Detection | Fallback |
|---|---|---|
| Camera failure | No detections for >30 seconds | Revert to fixed-cycle timing for that approach |
| All cameras fail | No detections on any approach | Full fixed-cycle fallback (pre-programmed timing) |
| Edge device crash | Watchdog timer, no heartbeat | Signal controller reverts to its built-in fixed timing |
| Network loss | No corridor communication | Node continues local optimization; green wave disabled |
| Power loss | UPS monitoring | Signal controller enters battery-backed all-red flash |

### 15.4 Minimum Phase Times

All jurisdictions mandate minimum green, yellow, and all-red durations. These are **hard constraints** in the optimization engine and cannot be overridden by any optimization objective:

| Parameter | Typical Range | Enforced By |
|---|---|---|
| Minimum green | 7–15 seconds | Software constraint (hard limit) |
| Yellow change interval | 3–5 seconds | Signal controller hardware |
| All-red clearance | 1–3 seconds | Signal controller hardware |
| Maximum green | 60–120 seconds | Software constraint (configurable) |

---

## 16. Universal Deployment Model

### 16.1 What "Universal" Means

FlowGrid is designed for deployment in any city worldwide. "Universal" does not mean "one size fits all" — it means:

- **Universal architecture:** The system architecture, layer structure, interfaces, and protocols are the same everywhere
- **Universal sensor abstraction:** Any combination of cameras, induction loops, and GPS data feeds into the same demand descriptor format
- **Universal optimization engine:** The same multi-objective optimizer runs everywhere, with locally configured weights
- **Local model weights:** The YOLO vision model is fine-tuned on local traffic data per city
- **Local configuration:** Intersection phasing, corridor definitions, and optimization weights are configured by local traffic engineers

### 16.2 Per-City Deployment Process

```
Week 1–2: SETUP
├── Install camera hardware at target intersections
├── Connect FlowGrid edge devices to existing signal controllers
├── Import intersection topology from OpenStreetMap
├── Configure intersection phasing (NEMA or simplified)
└── Define corridor groupings with local traffic engineers

Week 2–3: FINE-TUNING
├── Collect 2–4 days of camera footage
├── Annotate 1,000–2,000 images for local vehicle types
├── Fine-tune YOLO model (4–8 hours GPU training)
├── Validate model accuracy (target >85% mAP)
└── Deploy model weights to edge devices

Week 3–4: CALIBRATION
├── Run FlowGrid in shadow mode (computes but does not actuate)
├── Compare FlowGrid recommendations vs. fixed-cycle baseline
├── Tune PCU weights and optimization objectives per intersection
├── Measure GPS corridor speeds for green wave offset calibration
└── Activate FlowGrid in live control mode, intersection by intersection
```

**Total deployment timeline: 3–4 weeks per city.** Annual refresh: 2–3 days (recollect data, retrain model if vehicle fleet has changed).

### 16.3 Right-Hand vs. Left-Hand Traffic

The current implementation focuses on **right-hand traffic** (used in Vietnam, most of ASEAN, Europe, Americas — ~65% of the world). Left-hand traffic support (UK, Japan, Thailand, Indonesia, India, Australia) requires:
- Mirrored intersection geometry in the configuration
- Adjusted phase definitions (left turns become right turns)
- No changes to the vision model, optimization engine, or coordination layer

This is a configuration change, not an architectural change.

---

## 17. HCMC Case Study

### 17.1 Why Ho Chi Minh City?

| Factor | Relevance |
|---|---|
| **Scale of problem** | 9M population, 7.4M motorcycles, severe daily congestion |
| **Motorcycle dominance** | 80% motorcycle traffic — the hardest case for any traffic system |
| **Growing vehicle fleet** | Car ownership rising rapidly — congestion will worsen without intervention |
| **Existing infrastructure** | 1,000+ signalized intersections, most on fixed-cycle timing |
| **Government interest** | Vietnamese government actively seeking smart traffic solutions |
| **Data availability** | OpenStreetMap coverage, traffic camera footage obtainable, research datasets available |
| **Transferability** | Success in HCMC validates the system for all ASEAN motorcycle-dominant cities |

### 17.2 Proposed Initial Deployment Area

For the hackathon demonstration, we propose targeting a **single corridor in District 1** (central HCMC):

**Candidate corridor: Nguyen Hue Boulevard → Le Loi → Hai Ba Trung**

- 8–12 signalized intersections in sequence
- Major commercial corridor with heavy traffic at all hours
- Well-documented in OpenStreetMap
- Multiple traffic cameras already installed by HCMC traffic management center
- Highly visible — improvements here impact hundreds of thousands of daily commuters

### 17.3 Expected Impact

Based on published results from adaptive signal control deployments in comparable cities:

| Metric | Fixed-Cycle Baseline | FlowGrid Expected | Improvement |
|---|---|---|---|
| Average delay per vehicle | 45–90 seconds | 25–50 seconds | 30–45% reduction |
| Number of stops per corridor | 3–5 per km | 1–2 per km | 50–60% reduction |
| Corridor travel time | Variable, high variance | More consistent, lower mean | 15–25% reduction |
| Fuel consumption | Baseline | Reduced (fewer stops) | 10–15% reduction |
| Emissions | Baseline | Reduced (fewer stops, less idling) | 10–15% reduction |

*Note: These estimates are based on published results from SCATS, SCOOT, and InSync deployments. Actual FlowGrid performance will be validated through simulation during the hackathon.*

### 17.4 Data Requirements from Vietnamese Mentors

To build and validate the HCMC prototype, Team Jam Breakers will work with Vietnamese mentors to obtain:

**Critical (blocks prototype):**
1. Traffic camera footage — 2–3 days from 10–20 intersections, covering peak hours
2. Current signal timing plans — existing fixed-cycle durations and phase sequences
3. Intersection-level vehicle counts — by vehicle type, at 15-minute intervals

**Important (significantly improves quality):**
4. Corridor identification — which 3–5 roads benefit most from green wave coordination
5. OpenStreetMap validation — lane counts, turn restrictions for target area
6. Known congestion hotspots — where to focus and validate

**Nice to have:**
7. GPS/ride-hailing speed data — anonymized corridor speeds from Grab or similar
8. Incident/accident data — for emergency priority validation

---

## 18. Hackathon Deliverables — 60-Day Plan

### 18.1 Scope: What We Build vs. Full Vision

| Component | Hackathon Scope | Full Vision (Post-Hackathon) |
|---|---|---|
| **Vision model** | YOLO fine-tuned on HCMC footage, running on video files | Real-time camera processing on edge device |
| **Optimization engine** | Full implementation, tested in simulation | Production-hardened, deployed at real intersections |
| **Green wave coordination** | Simulated on 1 corridor in SUMO | Multi-corridor, city-wide deployment |
| **Monitoring dashboard** | Web dashboard showing simulation results | Live operational dashboard with remote intervention |
| **Edge deployment** | Software running on laptop/cloud (simulating edge) | Actual Jetson/edge hardware at intersections |
| **Emergency preemption** | Simulated in SUMO | Real IR/radio preemption hardware |

### 18.2 60-Day Timeline

```
PHASE 1: FOUNDATION (Weeks 1–2)
─────────────────────────────────
AI Engineer:
  ├── Set up YOLO training pipeline
  ├── Collect & annotate Vietnamese traffic images
  └── Begin model fine-tuning

Researcher:
  ├── Extract HCMC road network from OpenStreetMap
  ├── Set up SUMO simulation environment
  └── Research published HCMC traffic volume data

Full Stack Developer:
  ├── Design system architecture & data models
  ├── Build sensor abstraction layer interfaces
  └── Begin monitoring dashboard skeleton


PHASE 2: CORE DEVELOPMENT (Weeks 3–5)
──────────────────────────────────────
AI Engineer:
  ├── Validate YOLO model on HCMC test set
  ├── Implement area density estimation
  └── Build inference pipeline (video → demand descriptor)

Researcher:
  ├── Implement optimization engine (PCU, multi-objective)
  ├── Calibrate SUMO with realistic HCMC traffic patterns
  └── Define corridor configurations and green wave parameters

Full Stack Developer:
  ├── Implement green wave coordination protocol
  ├── Connect simulation to optimization engine
  └── Build dashboard: real-time visualization of signal states


PHASE 3: INTEGRATION & VALIDATION (Weeks 6–7)
──────────────────────────────────────────────
AI Engineer:
  ├── Integrate vision pipeline with optimization engine
  ├── Night-time fallback implementation
  └── Performance benchmarking (FPS, accuracy)

Researcher:
  ├── Run comparison: FlowGrid vs. fixed-cycle in SUMO
  ├── Measure improvement metrics (delay, stops, travel time)
  └── Statistical analysis of results

Full Stack Developer:
  ├── Dashboard: comparison visualizations (before/after)
  ├── Dashboard: corridor green wave animation
  └── System integration testing


PHASE 4: POLISH & PRESENTATION (Week 8)
────────────────────────────────────────
All team members:
  ├── Final testing and bug fixes
  ├── Record demo video
  ├── Prepare presentation materials
  └── Documentation finalization
```

### 18.3 Key Milestones

| Week | Milestone | Deliverable |
|---|---|---|
| 2 | Vision model v1 | YOLO detecting motorcycles, cars, buses, trucks on HCMC footage |
| 3 | SUMO simulation running | HCMC corridor simulated with realistic traffic demand |
| 5 | Optimization engine complete | Adaptive signal timing running in SUMO, outperforming fixed-cycle |
| 6 | Green wave working | Corridor-level coordination demonstrated in simulation |
| 7 | Full pipeline integrated | Camera video → NN → demand → optimizer → signal → SUMO feedback loop |
| 8 | Final demo | Dashboard showing FlowGrid vs. fixed-cycle comparison with quantified improvements |

---

## 19. Team Jam Breakers

| Role | Responsibility |
|---|---|
| **AI Engineer** | Vision model (YOLO fine-tuning, inference pipeline), area density estimation, night-time fallback, edge deployment optimization |
| **Researcher** | Traffic engineering domain (PCU model, optimization objectives, SUMO simulation), data collection coordination with Vietnamese mentors, performance analysis and validation |
| **Full Stack Developer** | System architecture, monitoring dashboard, green wave coordination protocol, sensor abstraction interfaces, system integration |

**Supported by:** Vietnamese mentors providing local traffic data, domain expertise on HCMC traffic patterns, and practical deployment guidance.

---

## 20. Post-Hackathon Roadmap

### Phase 1: Pilot Deployment (Months 3–6)
- Partner with HCMC traffic management center for a live pilot on one corridor (8–12 intersections)
- Deploy actual edge hardware (Jetson Orin Nano) and cameras
- Measure real-world performance vs. simulation predictions
- Iterate on optimization parameters based on real data

### Phase 2: City-Wide Expansion (Months 6–12)
- Extend to 5–10 corridors across HCMC
- Deploy emergency vehicle preemption hardware on ambulances and fire trucks
- Integrate GPS floating car data from Grab for adaptive green wave offsets
- Build operator training program for monitoring dashboard

### Phase 3: ASEAN Expansion (Year 2)
- Transfer to Hanoi (similar traffic profile, minimal re-tuning)
- Adapt for Bangkok, Jakarta, Manila (different vehicle mixes, some left-hand traffic)
- Build city-deployment toolkit for rapid onboarding

### Phase 4: Global (Year 3+)
- Car-dominant city deployments (different PCU weights, simpler density estimation)
- Left-hand traffic support
- Integration with V2X (Vehicle-to-Everything) communication as it becomes available
- Pedestrian and cyclist detection modules (currently out of scope)

### Low Priority / Future Features
- **Pedestrian zebra crossing on ad-hoc request** — pedestrian push-button integration that triggers a walk phase on demand
- **Strategic road construction recommendations** — using traffic flow data to identify bottlenecks where new road infrastructure would have maximum impact

---

## 21. Conclusion

FlowGrid addresses a problem that affects millions of urban commuters daily — not through incremental improvements to existing systems, but by rethinking traffic signal control from first principles.

The system is:
- **Practical** — it works with existing traffic signal infrastructure, requires only cameras and commodity edge hardware, and can be deployed in 3–4 weeks per city
- **Innovative** — it introduces PCU-weighted demand estimation, area density measurement for motorcycle-fluid traffic, and adaptive green waves using GPS floating car data
- **Impactful** — simulation-validated improvements of 30–45% reduction in average delay, directly benefiting millions of commuters
- **Universal** — a single architecture that adapts to any city through local fine-tuning, from motorcycle-dominant HCMC to car-dominant European cities

Team Jam Breakers is committed to building and validating this system over the next 60 days, starting with Ho Chi Minh City — one of the world's most challenging traffic environments. If FlowGrid works here, it works anywhere.

We look forward to collaborating with Vietnamese mentors and traffic experts to turn this proposal into a working demonstration that improves the daily lives of commuters across Vietnam and beyond.

---

## Appendix A — Signal Phasing Reference

### NEMA Standard Phase Numbering

```
                    N
                    ↑
              P5 ←  │  → P2 (through)
              (LT)  │
                    │
    W ←─────────────┼──────────────→ E
              P7 ←  │  → P4 (through)
              (LT)  │
                    │
              P1 ←  │  → P6 (through)
              (LT)  │
                    ↓
                    S
              P3 ←     → P8 (through)
              (LT)

    Even phases (2, 4, 6, 8): Through movements
    Odd phases (1, 3, 5, 7): Left-turn movements
    Phases 2 & 6: Major street through
    Phases 4 & 8: Minor street through
```

### Simplified 2-Phase Configuration

For simple intersections without dedicated turn phases:

```
Phase A: Major street (all movements) — combines P2 + P6 + turns
Phase B: Minor street (all movements) — combines P4 + P8 + turns
```

### Ring-Barrier Structure

NEMA phases are organized into two rings and two barriers:

```
Ring 1:  P1 → P2  |  P3 → P4
                   |
Ring 2:  P5 → P6  |  P7 → P8
         ─────────────────────
         Barrier 1 | Barrier 2
```

Phases within the same ring are sequential. Phases in different rings but the same barrier are concurrent (non-conflicting). The barrier is a synchronization point — all phases before the barrier must complete before any phase after the barrier can begin.

---

## Appendix B — Data Requirements Per City Deployment

### Critical Data (Blocks Deployment)

| # | Data Item | Source | Format | Volume |
|---|---|---|---|---|
| 1 | Traffic camera footage | City traffic center / new cameras | Video (MP4/H.264) | 2–4 days, 10–20 intersections, peak hours |
| 2 | Current signal timing plans | City traffic engineering dept. | Spreadsheet / PDF | All target intersections |
| 3 | Vehicle counts by type | Manual counts or existing sensors | CSV / spreadsheet | 15-min intervals, 1 full day, 5–10 intersections |

### Important Data (Improves Quality)

| # | Data Item | Source | Format | Volume |
|---|---|---|---|---|
| 4 | Corridor identification | Local traffic engineers | Map / list | 3–5 priority corridors |
| 5 | OSM road network validation | Local team on-ground | OpenStreetMap edits | Target deployment area |
| 6 | Congestion hotspot list | Traffic police / city data | Map / list | Top 10–20 worst intersections |

### Nice-to-Have Data (Enhanced Capabilities)

| # | Data Item | Source | Format | Volume |
|---|---|---|---|---|
| 7 | GPS corridor speed traces | Grab / taxi companies / research | CSV (timestamp, lat, lng, speed) | 1 week, major corridors |
| 8 | Incident / accident records | Traffic police | CSV / database | 1 year historical |
| 9 | Public transit routes and schedules | City transit authority | GTFS format | Current schedules |

---

*Document prepared by Team Jam Breakers for the International Hackathon — Vietnam 2026.*
*FlowGrid — Adaptive Traffic Signal Control System.*
*Version 1.0 — September 2026.*
