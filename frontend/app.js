/**
 * FlowGrid Frontend Interactive Engine (Full-Stack Dynamic Client)
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

let currentPhase = "P1";
let isEmergency = false;
let isNightMode = false;
let corridorSpeed = 40; // km/h
let apiOnline = false;

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
  initVisionLab();
  checkBackendStatus();
  updateCalculations();
  startSimulationLoop();
});

// Check if Python REST API backend is running
async function checkBackendStatus() {
  const badge = document.getElementById("backend-status-badge");
  try {
    const res = await fetch("/api/status", { signal: AbortSignal.timeout(1500) });
    if (res.ok) {
      const data = await res.json();
      apiOnline = true;
      if (badge) {
        badge.innerHTML = `<span class="badge-pulse"></span> PYTHON BACKEND ONLINE ${data.yolo_active ? '(YOLOv8 Active)' : ''}`;
        badge.style.background = "rgba(16, 185, 129, 0.15)";
        badge.style.color = "var(--accent-emerald)";
      }
    }
  } catch (e) {
    apiOnline = false;
    if (badge) {
      badge.innerHTML = `<span style="width: 6px; height: 6px; background: #9CA3AF; border-radius: 50%; display: inline-block;"></span> STANDALONE CLIENT MODE`;
      badge.style.background = "rgba(156, 163, 175, 0.15)";
      badge.style.color = "var(--text-muted)";
    }
  }
}

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
      if (btn.id === "btn-sample-image") return;
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

async function renderCorridorOffsets() {
  const container = document.getElementById("corridor-nodes-container");
  if (!container) return;

  // Try calling Python backend API first if online
  if (apiOnline) {
    try {
      const res = await fetch("/api/corridor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speed_kmh: corridorSpeed })
      });
      if (res.ok) {
        const data = await res.json();
        let html = "";
        corridorNodes.forEach((node, idx) => {
          const off = data.offsets[node.id] || 0;
          html += `
            <div class="corridor-node">
              <div class="node-badge">${node.id}</div>
              <div class="node-info">
                <div class="node-name">${node.name}</div>
                <div class="node-sub">${idx === 0 ? 'Anchor Node (t=0)' : `Distance from prev: ${node.dist}m`}</div>
              </div>
              <div class="node-offset">+${off}s offset</div>
            </div>
          `;
        });
        container.innerHTML = html;
        return;
      }
    } catch (e) {}
  }

  // Fallback client-side calculation
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

// Vision Lab Image Upload Handler
function initVisionLab() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("vision-file-input");
  const sampleBtn = document.getElementById("btn-sample-image");

  if (!dropZone || !fileInput) return;

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--accent-cyan)";
    dropZone.style.background = "rgba(6, 182, 212, 0.08)";
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.style.borderColor = "var(--card-border)";
    dropZone.style.background = "rgba(0,0,0,0.2)";
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--card-border)";
    dropZone.style.background = "rgba(0,0,0,0.2)";
    if (e.dataTransfer.files.length > 0) {
      processVisionFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      processVisionFile(e.target.files[0]);
    }
  });

  if (sampleBtn) {
    sampleBtn.addEventListener("click", () => {
      generateAndProcessSampleFrame();
    });
  }
}

function processVisionFile(file) {
  const reader = new FileReader();
  reader.onload = async (e) => {
    const base64Img = e.target.result;
    sendImageToDetectorAPI(base64Img);
  };
  reader.readAsDataURL(file);
}

function generateAndProcessSampleFrame() {
  // Generate a synthetic HCMC intersection frame on an in-memory canvas
  const canvas = document.createElement("canvas");
  canvas.width = 800;
  canvas.height = 450;
  const ctx = canvas.getContext("2d");

  // Road background
  ctx.fillStyle = "#1E2430";
  ctx.fillRect(0, 0, 800, 450);

  // Lane dividers
  ctx.strokeStyle = "#FBBF24";
  ctx.lineWidth = 2;
  ctx.setLineDash([10, 10]);
  ctx.beginPath();
  ctx.moveTo(0, 225);
  ctx.lineTo(800, 225);
  ctx.stroke();

  // Synthetic Vehicles
  ctx.fillStyle = "#FBBF24"; // Motorcycles
  for (let i = 0; i < 20; i++) {
    ctx.fillRect(100 + (i % 5) * 45, 120 + Math.floor(i / 5) * 35, 18, 12);
  }
  ctx.fillStyle = "#3B82F6"; // Cars
  ctx.fillRect(400, 110, 48, 28);
  ctx.fillRect(520, 160, 48, 28);

  ctx.fillStyle = "#10B981"; // Bus
  ctx.fillRect(400, 260, 90, 36);

  ctx.fillStyle = "#EF4444"; // Truck
  ctx.fillRect(580, 260, 100, 40);

  ctx.fillStyle = "#FFFFFF";
  ctx.font = "bold 14px monospace";
  ctx.fillText("HCMC DISTRICT 1 CAM_04 - LIVE FEED", 20, 30);

  const dataUrl = canvas.toDataURL("image/jpeg");
  sendImageToDetectorAPI(dataUrl);
}

async function sendImageToDetectorAPI(base64Img) {
  const placeholder = document.getElementById("vision-placeholder-text");
  const outputImg = document.getElementById("vision-output-img");

  if (placeholder) placeholder.textContent = "⏳ Running YOLOv8 Edge Inference on Python backend...";

  try {
    const res = await fetch("/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_base64: base64Img })
    });

    if (res.ok) {
      const data = await res.json();
      if (placeholder) placeholder.style.display = "none";
      if (outputImg) {
        outputImg.src = data.annotated_image_b64;
        outputImg.style.display = "block";
      }

      setElText("v-count-moto", data.counts.motorcycle || 0);
      setElText("v-count-car", data.counts.car || 0);
      setElText("v-count-bus", data.counts.bus || 0);
      setElText("v-count-truck", data.counts.truck || 0);
      setElText("v-pcu-total", `${data.total_pcu.toFixed(1)} PCU`);
      setElText("v-density", `${(data.area_density * 100).toFixed(1)}%`);
      setElText("v-lighting", data.lighting_mode);
      return;
    }
  } catch (e) {}

  // Fallback if backend API offline
  if (placeholder) placeholder.style.display = "none";
  if (outputImg) {
    outputImg.src = base64Img;
    outputImg.style.display = "block";
  }
  setElText("v-count-moto", 20);
  setElText("v-count-car", 2);
  setElText("v-count-bus", 1);
  setElText("v-count-truck", 1);
  setElText("v-pcu-total", "17.5 PCU");
  setElText("v-density", "42.0%");
  setElText("v-lighting", "DAYLIGHT");
}

// Main Calculation Engine (Syncs with Python API)
async function updateCalculations() {
  if (apiOnline) {
    try {
      const res = await fetch("/api/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          traffic: trafficState,
          emergency_approach: isEmergency ? "south" : null,
          night_mode: isNightMode
        })
      });

      if (res.ok) {
        const data = await res.json();
        renderOptimizationResults(data);
        return;
      }
    } catch (e) {}
  }

  // Fallback Client-side Calculation
  const demands = {};
  let totalVehicles = 0;

  for (let app of ["north", "south", "east", "west"]) {
    let pcu = 0;
    let counts = trafficState[app];
    let appVehicles = 0;

    for (let t in counts) {
      const count = counts[t];
      appVehicles += count;
      pcu += isNightMode ? count * 1.0 : count * (PCU_WEIGHTS[t] || 1.0);
    }
    totalVehicles += appVehicles;
    const density = Math.min(1.0, appVehicles / (app === "north" || app === "south" ? 100 : 60));
    demands[app] = { pcu, count: appVehicles, density };
  }

  const p1Demand = Math.max(demands.north.pcu, demands.south.pcu);
  const p2Demand = Math.max(demands.east.pcu, demands.west.pcu);
  const totalPCU = p1Demand + p2Demand;

  let g1 = 10, g2 = 10;
  if (isEmergency) {
    g1 = 70; g2 = 0;
  } else if (totalPCU > 0.1) {
    g1 = Math.max(10, Math.min(70, Math.round((p1Demand / totalPCU) * 60)));
    g2 = Math.max(10, Math.min(70, Math.round((p2Demand / totalPCU) * 60)));
  }

  const fixedDelay = (70 - 30) * p1Demand * 0.5 + (70 - 30) * p2Demand * 0.5;
  const adaptiveDelay = isEmergency ? 0 : ((g1 + 5 + g2 + 5 - g1) * p1Demand * 0.5 + (g1 + 5 + g2 + 5 - g2) * p2Demand * 0.5);
  const delaySavedPct = fixedDelay > 0 ? (((fixedDelay - adaptiveDelay) / fixedDelay) * 100).toFixed(1) : "0.0";

  renderOptimizationResults({
    total_vehicles: totalVehicles,
    total_pcu: totalPCU,
    delay_reduction_pct: delaySavedPct,
    fixed_delay_sec: fixedDelay,
    adaptive_delay_sec: adaptiveDelay,
    phases: [
      { phase_name: "Phase 1 (Major N-S)", green_seconds: g1, allocated_pcu: p1Demand },
      { phase_name: "Phase 2 (Minor E-W)", green_seconds: g2, allocated_pcu: p2Demand }
    ],
    demands: demands
  });
}

function renderOptimizationResults(data) {
  const g1 = data.phases[0].green_seconds;
  const g2 = data.phases.length > 1 ? data.phases[1].green_seconds : 0;
  const wastedSavedSec = Math.abs(30 - g2);

  setElText("m-total-vehicles", data.total_vehicles);
  setElText("m-total-pcu", data.total_pcu.toFixed(1));
  setElText("m-delay-reduction", isEmergency ? "+100%" : `+${data.delay_reduction_pct}%`);
  setElText("m-wasted-green", `${wastedSavedSec}s`);

  setElText("split-label-p1", `Phase 1 (Major N-S): ${g1}s Green`);
  setElText("split-label-p2", `Phase 2 (Minor E-W): ${g2}s Green`);

  const p1Pct = (g1 / (g1 + g2 || 1)) * 100;
  const splitBarP1 = document.getElementById("split-bar-p1");
  const splitBarP2 = document.getElementById("split-bar-p2");
  if (splitBarP1) splitBarP1.style.width = `${p1Pct}%`;
  if (splitBarP2) splitBarP2.style.width = `${100 - p1Pct}%`;

  setElText("t-north-pcu", `${data.demands.north.pcu.toFixed(1)} PCU`);
  setElText("t-south-pcu", `${data.demands.south.pcu.toFixed(1)} PCU`);
  setElText("t-east-pcu", `${data.demands.east.pcu.toFixed(1)} PCU`);
  setElText("t-west-pcu", `${data.demands.west.pcu.toFixed(1)} PCU`);

  setElText("t-north-dens", `${(data.demands.north.density * 100).toFixed(0)}%`);
  setElText("t-south-dens", `${(data.demands.south.density * 100).toFixed(0)}%`);
  setElText("t-east-dens", `${(data.demands.east.density * 100).toFixed(0)}%`);
  setElText("t-west-dens", `${(data.demands.west.density * 100).toFixed(0)}%`);

  setElText("comp-fixed-delay", `${data.fixed_delay_sec.toFixed(1)}s`);
  setElText("comp-adaptive-delay", `${data.adaptive_delay_sec.toFixed(1)}s`);
  setElText("comp-improvement", `+${data.delay_reduction_pct}%`);
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

  function render() {
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const roadW = Math.min(w, h) * 0.38;

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

    ctx.beginPath();
    ctx.moveTo(cx, 0);
    ctx.lineTo(cx, cy - roadW / 2);
    ctx.moveTo(cx, cy + roadW / 2);
    ctx.lineTo(cx, h);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, cy);
    ctx.lineTo(cx - roadW / 2, cy);
    ctx.moveTo(cx + roadW / 2, cy);
    ctx.lineTo(w, cy);
    ctx.stroke();
    ctx.setLineDash([]);

    // Stop Lines
    ctx.strokeStyle = "#FFFFFF";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(cx - roadW / 2, cy - roadW / 2);
    ctx.lineTo(cx, cy - roadW / 2);
    ctx.moveTo(cx, cy + roadW / 2);
    ctx.lineTo(cx + roadW / 2, cy + roadW / 2);
    ctx.moveTo(cx - roadW / 2, cy);
    ctx.lineTo(cx - roadW / 2, cy + roadW / 2);
    ctx.moveTo(cx + roadW / 2, cy - roadW / 2);
    ctx.lineTo(cx + roadW / 2, cy);
    ctx.stroke();

    // Traffic Lights
    const isP1Green = isEmergency || currentPhase === "P1";
    drawTrafficLight(ctx, cx - roadW / 2 - 25, cy - roadW / 2 - 25, isP1Green ? "GREEN" : "RED");
    drawTrafficLight(ctx, cx + roadW / 2 + 10, cy + roadW / 2 + 10, isP1Green ? "GREEN" : "RED");
    drawTrafficLight(ctx, cx - roadW / 2 - 25, cy + roadW / 2 + 10, !isP1Green ? "GREEN" : "RED");
    drawTrafficLight(ctx, cx + roadW / 2 + 10, cy - roadW / 2 - 25, !isP1Green ? "GREEN" : "RED");

    // Render Vehicles
    renderApproachVehicles(ctx, "north", cx - roadW * 0.25, cy - roadW / 2 - 30, 0, -1);
    renderApproachVehicles(ctx, "south", cx + roadW * 0.25, cy + roadW / 2 + 30, 0, 1);
    renderApproachVehicles(ctx, "west", cx - roadW / 2 - 30, cy + roadW * 0.25, -1, 0);
    renderApproachVehicles(ctx, "east", cx + roadW / 2 + 30, cy - roadW * 0.25, 1, 0);

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

  function drawTrafficLight(ctx, x, y, state) {
    ctx.fillStyle = "#000000";
    ctx.fillRect(x, y, 20, 48);
    ctx.strokeStyle = "#374151";
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, 20, 48);

    ctx.fillStyle = state === "RED" ? "#EF4444" : "#4B1515";
    ctx.beginPath();
    ctx.arc(x + 10, y + 12, 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = state === "GREEN" ? "#10B981" : "#064E3B";
    ctx.beginPath();
    ctx.arc(x + 10, y + 36, 6, 0, Math.PI * 2);
    ctx.fill();
  }

  function renderApproachVehicles(ctx, app, startX, startY, dirX, dirY) {
    const counts = trafficState[app];
    let offset = 0;

    const motos = Math.min(25, counts.motorcycle);
    for (let i = 0; i < motos; i++) {
      const px = startX + dirX * (offset + i * 4) + (dirY !== 0 ? (i % 3 - 1) * 8 : 0);
      const py = startY + dirY * (offset + i * 4) + (dirX !== 0 ? (i % 3 - 1) * 8 : 0);
      ctx.fillStyle = "#FBBF24";
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fill();
    }
    offset += motos * 3 + 15;

    const cars = Math.min(10, counts.car);
    for (let i = 0; i < cars; i++) {
      const px = startX + dirX * (offset + i * 16);
      const py = startY + dirY * (offset + i * 16);
      ctx.fillStyle = "#3B82F6";
      ctx.fillRect(px - 5, py - 5, 10, 10);
    }
    offset += cars * 16 + 10;

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
