/**
 * FlowGrid Frontend Interactive Engine
 * Team Jam Breakers | International Hackathon - Vietnam 2026
 */

// PCU Weights
const PCU_WEIGHTS = {
  motorcycle: 0.5,
  car: 1.0,
  bus: 2.5,
  truck: 3.0
};

// State
let trafficState = {
  north: { motorcycle: 80, car: 6, bus: 2, truck: 0 },
  south: { motorcycle: 35, car: 4, bus: 1, truck: 0 },
  east:  { motorcycle: 10, car: 4, bus: 1, truck: 0 },
  west:  { motorcycle: 8,  car: 2, bus: 0, truck: 0 }
};

let currentPhase = "P1"; // "P1" (North/South) or "P2" (East/West) or "EMERGENCY"
let phaseTimeRemaining = 53;
let isEmergency = false;
let isNightMode = false;
let corridorSpeed = 40; // km/h

// Corridor nodes
const corridorNodes = [
  { id: "N1", name: "Nguyen Hue - Le Thanh Ton", dist: 0 },
  { id: "N2", name: "Nguyen Hue - Le Loi", dist: 320 },
  { id: "N3", name: "Nguyen Hue - Ngo Duc Ke", dist: 280 },
  { id: "N4", name: "Nguyen Hue - Ton Duc Thang", dist: 350 }
];

// Presets
const PRESETS = {
  hcmc_peak: {
    north: { motorcycle: 80, car: 6, bus: 2, truck: 0 },
    south: { motorcycle: 35, car: 4, bus: 1, truck: 0 },
    east:  { motorcycle: 10, car: 4, bus: 1, truck: 0 },
    west:  { motorcycle: 8,  car: 2, bus: 0, truck: 0 },
    emergency: false,
    night: false
  },
  truck_influx: {
    north: { motorcycle: 30, car: 5, bus: 0, truck: 0 },
    south: { motorcycle: 20, car: 3, bus: 0, truck: 0 },
    east:  { motorcycle: 4,  car: 3, bus: 3, truck: 5 },
    west:  { motorcycle: 6,  car: 2, bus: 1, truck: 2 },
    emergency: false,
    night: false
  },
  balanced: {
    north: { motorcycle: 30, car: 10, bus: 1, truck: 0 },
    south: { motorcycle: 30, car: 10, bus: 1, truck: 0 },
    east:  { motorcycle: 25, car: 8,  bus: 1, truck: 0 },
    west:  { motorcycle: 25, car: 8,  bus: 1, truck: 0 },
    emergency: false,
    night: false
  },
  night: {
    north: { motorcycle: 4, car: 2, bus: 0, truck: 0 },
    south: { motorcycle: 3, car: 1, bus: 0, truck: 0 },
    east:  { motorcycle: 1, car: 1, bus: 0, truck: 0 },
    west:  { motorcycle: 2, car: 0, bus: 0, truck: 0 },
    emergency: false,
    night: true
  },
  emergency: {
    north: { motorcycle: 80, car: 6, bus: 2, truck: 0 },
    south: { motorcycle: 35, car: 4, bus: 1, truck: 0 },
    east:  { motorcycle: 10, car: 4, bus: 1, truck: 0 },
    west:  { motorcycle: 8,  car: 2, bus: 0, truck: 0 },
    emergency: true,
    night: false
  }
};

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initSliders();
  initPresets();
  initCorridor();
  updateCalculations();
  startSimulationLoop();
});

// Tab Navigation
function initTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = document.getElementById(btn.dataset.tab);
      if (target) target.classList.add("active");
    });
  });
}

// Sliders listener
function initSliders() {
  const approaches = ["north", "south", "east", "west"];
  const types = ["motorcycle", "car", "bus", "truck"];

  approaches.forEach(app => {
    types.forEach(type => {
      const slider = document.getElementById(`slider-${app}-${type}`);
      const valLabel = document.getElementById(`val-${app}-${type}`);
      if (slider && valLabel) {
        slider.addEventListener("input", (e) => {
          const v = parseInt(e.target.value, 10);
          valLabel.textContent = v;
          trafficState[app][type] = v;
          updateCalculations();
        });
      }
    });
  });
}

// Preset Buttons
function initPresets() {
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const presetKey = btn.dataset.preset;
      if (PRESETS[presetKey]) {
        applyPreset(PRESETS[presetKey]);
      }
    });
  });
}

function applyPreset(p) {
  trafficState = JSON.parse(JSON.stringify({
    north: p.north,
    south: p.south,
    east: p.east,
    west: p.west
  }));
  isEmergency = p.emergency;
  isNightMode = p.night;

  // Sync sliders
  const approaches = ["north", "south", "east", "west"];
  const types = ["motorcycle", "car", "bus", "truck"];
  approaches.forEach(app => {
    types.forEach(type => {
      const slider = document.getElementById(`slider-${app}-${type}`);
      const valLabel = document.getElementById(`val-${app}-${type}`);
      if (slider && valLabel) {
        slider.value = trafficState[app][type];
        valLabel.textContent = trafficState[app][type];
      }
    });
  });

  updateCalculations();
}

// Corridor speed slider
function initCorridor() {
  const speedSlider = document.getElementById("corridor-speed-slider");
  const speedLabel = document.getElementById("corridor-speed-val");
  if (speedSlider && speedLabel) {
    speedSlider.addEventListener("input", (e) => {
      corridorSpeed = parseInt(e.target.value, 10);
      speedLabel.textContent = `${corridorSpeed} km/h`;
      renderCorridorOffsets();
    });
  }
  renderCorridorOffsets();
}

function renderCorridorOffsets() {
  const container = document.getElementById("corridor-nodes-container");
  if (!container) return;

  const speedMps = (corridorSpeed * 1000) / 3600;
  let accumulatedDist = 0;
  let html = "";

  corridorNodes.forEach((node, idx) => {
    accumulatedDist += node.dist;
    const offsetSec = Math.round(accumulatedDist / speedMps);

    html += `
      <div class="corridor-node">
        <div class="node-badge">${node.id}</div>
        <div class="node-info">
          <div class="node-name">${node.name}</div>
          <div class="node-sub">${idx === 0 ? 'Anchor Node (t=0)' : `Distance: ${node.dist}m | Cumulative: ${accumulatedDist}m`}</div>
        </div>
        <div class="node-offset">+${offsetSec}s offset</div>
      </div>
    `;
  });

  container.innerHTML = html;
}

// Main Calculation Engine
function updateCalculations() {
  // Compute PCU per approach
  const demands = {};
  let totalVehicles = 0;

  for (let app of ["north", "south", "east", "west"]) {
    let pcu = 0;
    let counts = trafficState[app];
    let appVehicles = 0;

    for (let t in counts) {
      const count = counts[t];
      appVehicles += count;
      if (isNightMode) {
        pcu += count * 1.0; // 1 object = 1 PCU in dark night mode
      } else {
        pcu += count * (PCU_WEIGHTS[t] || 1.0);
      }
    }
    totalVehicles += appVehicles;

    // Area density estimate (% occupied)
    const density = Math.min(1.0, appVehicles / (app === "north" || app === "south" ? 100 : 60));
    demands[app] = { pcu, count: appVehicles, density };
  }

  // Phase Demands
  const p1Demand = Math.max(demands.north.pcu, demands.south.pcu);
  const p2Demand = Math.max(demands.east.pcu, demands.west.pcu);
  const totalPCU = p1Demand + p2Demand;

  // Adaptive Split Allocation
  let g1 = 10, g2 = 10;
  if (isEmergency) {
    g1 = 70;
    g2 = 0;
  } else if (totalPCU > 0.1) {
    const budget = 60;
    const p1Raw = Math.round((p1Demand / totalPCU) * budget);
    const p2Raw = Math.round((p2Demand / totalPCU) * budget);
    g1 = Math.max(10, Math.min(70, p1Raw));
    g2 = Math.max(10, Math.min(70, p2Raw));
  }

  // Fixed baseline
  const fixedG1 = 30;
  const fixedG2 = 30;
  const fixedCycle = 70;
  const fixedDelay = (fixedCycle - fixedG1) * p1Demand * 0.5 + (fixedCycle - fixedG2) * p2Demand * 0.5;

  const adaptiveCycle = (g1 + 5) + (g2 + 5);
  const adaptiveDelay = isEmergency ? 0 : ((adaptiveCycle - g1) * p1Demand * 0.5 + (adaptiveCycle - g2) * p2Demand * 0.5);

  const delaySavedPct = fixedDelay > 0 ? (((fixedDelay - adaptiveDelay) / fixedDelay) * 100).toFixed(1) : "0.0";
  const wastedSavedSec = Math.abs(fixedG2 - g2);

  // Update UI Elements
  setElText("m-total-vehicles", totalVehicles);
  setElText("m-total-pcu", totalPCU.toFixed(1));
  setElText("m-delay-reduction", isEmergency ? "+100%" : `+${delaySavedPct}%`);
  setElText("m-wasted-green", `${wastedSavedSec}s`);
  setElText("split-label-p1", `Phase 1 (Major North-South): ${g1}s Green (${p1Demand.toFixed(1)} PCU)`);
  setElText("split-label-p2", `Phase 2 (Minor East-West): ${g2}s Green (${p2Demand.toFixed(1)} PCU)`);

  const p1Pct = (g1 / (g1 + g2)) * 100;
  const splitBarP1 = document.getElementById("split-bar-p1");
  const splitBarP2 = document.getElementById("split-bar-p2");
  if (splitBarP1) splitBarP1.style.width = `${p1Pct}%`;
  if (splitBarP2) splitBarP2.style.width = `${100 - p1Pct}%`;

  // Update Telemetry table
  setElText("t-north-pcu", `${demands.north.pcu.toFixed(1)} PCU`);
  setElText("t-south-pcu", `${demands.south.pcu.toFixed(1)} PCU`);
  setElText("t-east-pcu", `${demands.east.pcu.toFixed(1)} PCU`);
  setElText("t-west-pcu", `${demands.west.pcu.toFixed(1)} PCU`);

  setElText("t-north-dens", `${(demands.north.density * 100).toFixed(0)}%`);
  setElText("t-south-dens", `${(demands.south.density * 100).toFixed(0)}%`);
  setElText("t-east-dens", `${(demands.east.density * 100).toFixed(0)}%`);
  setElText("t-west-dens", `${(demands.west.density * 100).toFixed(0)}%`);

  setElText("comp-fixed-delay", `${fixedDelay.toFixed(1)}s`);
  setElText("comp-adaptive-delay", `${adaptiveDelay.toFixed(1)}s`);
  setElText("comp-improvement", `+${delaySavedPct}%`);
  setElText("comp-split", `${g1}s / ${g2}s`);
}

function setElText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// Canvas Intersection Rendering
function startSimulationLoop() {
  const canvas = document.getElementById("intersectionCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
  }
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  let frameCount = 0;

  function render() {
    frameCount++;
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const roadW = Math.min(w, h) * 0.38;

    // Background
    ctx.fillStyle = "#0A0E17";
    ctx.fillRect(0, 0, w, h);

    // Roads
    ctx.fillStyle = "#1E2430";
    ctx.fillRect(cx - roadW / 2, 0, roadW, h); // North-South
    ctx.fillRect(0, cy - roadW / 2, w, roadW); // East-West

    // Road Markings (Yellow center line)
    ctx.strokeStyle = "#FBBF24";
    ctx.lineWidth = 2;
    ctx.setLineDash([12, 10]);

    // North-South center line
    ctx.beginPath();
    ctx.moveTo(cx, 0);
    ctx.lineTo(cx, cy - roadW / 2);
    ctx.moveTo(cx, cy + roadW / 2);
    ctx.lineTo(cx, h);
    ctx.stroke();

    // East-West center line
    ctx.beginPath();
    ctx.moveTo(0, cy);
    ctx.lineTo(cx - roadW / 2, cy);
    ctx.moveTo(cx + roadW / 2, cy);
    ctx.lineTo(w, cy);
    ctx.stroke();
    ctx.setLineDash([]);

    // Stop Lines (White)
    ctx.strokeStyle = "#FFFFFF";
    ctx.lineWidth = 4;
    ctx.beginPath();
    // North stop line
    ctx.moveTo(cx - roadW / 2, cy - roadW / 2);
    ctx.lineTo(cx, cy - roadW / 2);
    // South stop line
    ctx.moveTo(cx, cy + roadW / 2);
    ctx.lineTo(cx + roadW / 2, cy + roadW / 2);
    // West stop line
    ctx.moveTo(cx - roadW / 2, cy);
    ctx.lineTo(cx - roadW / 2, cy + roadW / 2);
    // East stop line
    ctx.moveTo(cx + roadW / 2, cy - roadW / 2);
    ctx.lineTo(cx + roadW / 2, cy);
    ctx.stroke();

    // Render Traffic Lights
    const isP1Green = isEmergency || currentPhase === "P1";
    drawTrafficLight(ctx, cx - roadW / 2 - 25, cy - roadW / 2 - 25, isP1Green ? "GREEN" : "RED", "N-S (P1)");
    drawTrafficLight(ctx, cx + roadW / 2 + 10, cy + roadW / 2 + 10, isP1Green ? "GREEN" : "RED", "N-S (P1)");
    drawTrafficLight(ctx, cx - roadW / 2 - 25, cy + roadW / 2 + 10, !isP1Green ? "GREEN" : "RED", "E-W (P2)");
    drawTrafficLight(ctx, cx + roadW / 2 + 10, cy - roadW / 2 - 25, !isP1Green ? "GREEN" : "RED", "E-W (P2)");

    // Render Vehicles as dots/shapes
    renderApproachVehicles(ctx, "north", cx - roadW * 0.25, cy - roadW / 2 - 30, 0, -1);
    renderApproachVehicles(ctx, "south", cx + roadW * 0.25, cy + roadW / 2 + 30, 0, 1);
    renderApproachVehicles(ctx, "west", cx - roadW / 2 - 30, cy + roadW * 0.25, -1, 0);
    renderApproachVehicles(ctx, "east", cx + roadW / 2 + 30, cy - roadW * 0.25, 1, 0);

    // Emergency Vehicle Banner
    if (isEmergency) {
      ctx.fillStyle = "rgba(244, 63, 94, 0.9)";
      ctx.fillRect(cx - 160, 20, 320, 36);
      ctx.fillStyle = "#FFFFFF";
      ctx.font = "bold 14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("🚨 EMERGENCY PREEMPTION ACTIVE", cx, 43);
    }

    requestAnimationFrame(render);
  }

  function drawTrafficLight(ctx, x, y, state, label) {
    ctx.fillStyle = "#000000";
    ctx.fillRect(x, y, 20, 48);
    ctx.strokeStyle = "#374151";
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, 20, 48);

    // Red light
    ctx.fillStyle = state === "RED" ? "#EF4444" : "#4B1515";
    ctx.beginPath();
    ctx.arc(x + 10, y + 12, 6, 0, Math.PI * 2);
    ctx.fill();

    // Green light
    ctx.fillStyle = state === "GREEN" ? "#10B981" : "#064E3B";
    ctx.beginPath();
    ctx.arc(x + 10, y + 36, 6, 0, Math.PI * 2);
    ctx.fill();
  }

  function renderApproachVehicles(ctx, app, startX, startY, dirX, dirY) {
    const counts = trafficState[app];
    let offset = 0;

    // Draw motorcycles (yellow dots)
    const motos = Math.min(25, counts.motorcycle);
    for (let i = 0; i < motos; i++) {
      const spreadX = (Math.random() - 0.5) * 20;
      const spreadY = (Math.random() - 0.5) * 20;
      const px = startX + dirX * (offset + i * 4) + (dirY !== 0 ? (i % 3 - 1) * 8 : 0);
      const py = startY + dirY * (offset + i * 4) + (dirX !== 0 ? (i % 3 - 1) * 8 : 0);

      ctx.fillStyle = "#FBBF24";
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fill();
    }
    offset += motos * 3 + 15;

    // Draw Cars (Blue rectangles)
    const cars = Math.min(10, counts.car);
    for (let i = 0; i < cars; i++) {
      const px = startX + dirX * (offset + i * 16);
      const py = startY + dirY * (offset + i * 16);
      ctx.fillStyle = "#3B82F6";
      ctx.fillRect(px - 5, py - 5, 10, 10);
    }
    offset += cars * 16 + 10;

    // Draw Trucks / Buses (Red / Green large rectangles)
    const heavy = Math.min(4, counts.truck + counts.bus);
    for (let i = 0; i < heavy; i++) {
      const px = startX + dirX * (offset + i * 26);
      const py = startY + dirY * (offset + i * 26);
      ctx.fillStyle = i < counts.truck ? "#EF4444" : "#10B981";
      ctx.fillRect(px - 8, py - 8, 16, 16);
    }
  }

  render();
}
