"""
FlowGrid - Dynamic Full-Stack Web & REST API Server
Team Jam Breakers | International Hackathon - Vietnam 2026

Runs the local HTTP server and provides REST API endpoints for:
  - POST /api/optimize  (Runs Python AdaptiveSignalOptimizer & PCUCalculator)
  - POST /api/corridor  (Runs Python CorridorCoordinator)
  - POST /api/detect    (Runs YOLOv8 Vision Model & returns annotated image + telemetry)
  - GET  /api/status    (Returns backend system status and loaded models)
"""

import os
import sys
import json
import base64
import io
import webbrowser
import http.server
import socketserver
from typing import Dict, Any

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pcu import PCUCalculator, ApproachDemand
from src.optimizer import AdaptiveSignalOptimizer
from src.green_wave import CorridorCoordinator, IntersectionNode
from src.detector import FlowGridDetector, HAS_YOLO, HAS_CV2, HAS_NUMPY

PORT = 8000
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

# Initialize backend singletons
pcu_calc = PCUCalculator()
optimizer = AdaptiveSignalOptimizer()
detector = FlowGridDetector()

corridor_nodes = [
    IntersectionNode("N1", "Nguyen Hue - Le Thanh Ton", 0.0),
    IntersectionNode("N2", "Nguyen Hue - Le Loi", 320.0),
    IntersectionNode("N3", "Nguyen Hue - Ngo Duc Ke", 280.0),
    IntersectionNode("N4", "Nguyen Hue - Ton Duc Thang", 350.0),
]
corridor_coord = CorridorCoordinator("CORRIDOR-01", "Nguyen Hue Blvd", corridor_nodes)


class FlowGridAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self._send_json({
                "status": "ONLINE",
                "backend": "Python FlowGrid Engine",
                "yolo_active": HAS_YOLO and detector.model is not None,
                "opencv_active": HAS_CV2,
                "numpy_active": HAS_NUMPY,
                "port": PORT
            })
            return
        # Serve static frontend files
        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            req_data = json.loads(raw_body)
        except Exception:
            req_data = {}

        if self.path == "/api/optimize":
            self._handle_optimize(req_data)
        elif self.path == "/api/corridor":
            self._handle_corridor(req_data)
        elif self.path == "/api/detect":
            self._handle_detect(req_data)
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def _handle_optimize(self, data: Dict[str, Any]):
        traffic = data.get("traffic", {})
        emergency = data.get("emergency_approach", None)
        is_night = data.get("night_mode", False)

        demands = {}
        total_vehicles = 0

        for app_id in ["north", "south", "east", "west"]:
            counts = traffic.get(app_id, {"motorcycle": 0, "car": 0, "bus": 0, "truck": 0})
            total_vehicles += sum(counts.values())
            density = min(1.0, sum(counts.values()) / (100.0 if app_id in ["north", "south"] else 60.0))

            demands[app_id] = pcu_calc.compute_demand(
                approach_id=app_id,
                vehicle_counts=counts,
                area_density=density,
                is_night_count_only=is_night
            )

        # Run Python optimizer
        plan = optimizer.optimize_2phase(demands=demands, emergency_approach=emergency)

        # Baseline calculation (30s/30s)
        p1_d = max(demands["north"].total_pcu, demands["south"].total_pcu)
        p2_d = max(demands["east"].total_pcu, demands["west"].total_pcu)
        fixed_delay = (70 - 30) * p1_d * 0.5 + (70 - 30) * p2_d * 0.5
        adaptive_delay = plan.estimated_total_delay_sec
        delay_saved_pct = ((fixed_delay - adaptive_delay) / fixed_delay * 100.0) if fixed_delay > 0 else 0.0

        res = {
            "total_vehicles": total_vehicles,
            "total_pcu": round(p1_d + p2_d, 2),
            "delay_reduction_pct": round(delay_saved_pct, 1),
            "fixed_delay_sec": round(fixed_delay, 1),
            "adaptive_delay_sec": round(adaptive_delay, 1),
            "phases": [
                {
                    "phase_id": p.phase_id,
                    "phase_name": p.phase_name,
                    "green_seconds": p.green_seconds,
                    "allocated_pcu": p.allocated_pcu_demand
                }
                for p in plan.phases
            ],
            "demands": {
                k: {
                    "pcu": v.total_pcu,
                    "density": v.area_density,
                    "clearance_sec": v.estimated_clearance_time_sec,
                    "sat_flow": v.adjusted_saturation_flow
                }
                for k, v in demands.items()
            }
        }
        self._send_json(res)

    def _handle_corridor(self, data: Dict[str, Any]):
        speed = float(data.get("speed_kmh", 40.0))
        plan = corridor_coord.compute_offsets(real_time_speed_kmh=speed)
        self._send_json({
            "corridor_name": plan.corridor_name,
            "real_time_speed_kmh": plan.real_time_speed_kmh,
            "active_direction": plan.active_direction,
            "offsets": plan.node_offsets_sec
        })

    def _handle_detect(self, data: Dict[str, Any]):
        img_b64 = data.get("image_base64", "")
        if not img_b64:
            self._send_json({"error": "No image provided"}, status=400)
            return

        # Strip data URL prefix if present
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]

        try:
            img_bytes = base64.b64decode(img_b64)
        except Exception as e:
            self._send_json({"error": f"Base64 decode failed: {e}"}, status=400)
            return

        if HAS_CV2 and HAS_NUMPY:
            import cv2
            import numpy as np

            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                self._send_json({"error": "Could not decode image format"}, status=400)
                return

            # Run YOLO Detection
            detection = detector.detect_frame(img)
            pcu_res = pcu_calc.compute_demand("Uploaded_Camera_Feed", detection["vehicle_counts"], detection["area_density"])

            # Overlay annotations
            annotated = detector.draw_overlay(img, detection, pcu_res)
            _, buffer = cv2.imencode(".jpg", annotated)
            out_b64 = base64.b64encode(buffer).decode("utf-8")

            self._send_json({
                "success": True,
                "counts": detection["vehicle_counts"],
                "area_density": detection["area_density"],
                "lighting_mode": detection["lighting_mode"],
                "total_pcu": pcu_res.total_pcu,
                "clearance_sec": pcu_res.estimated_clearance_time_sec,
                "annotated_image_b64": f"data:image/jpeg;base64,{out_b64}"
            })
        else:
            # Fallback mock detector if OpenCV not installed
            mock_counts = {"motorcycle": 24, "car": 5, "bus": 1, "truck": 0}
            pcu_res = pcu_calc.compute_demand("Mock_Feed", mock_counts, 0.45)
            self._send_json({
                "success": True,
                "mock": True,
                "counts": mock_counts,
                "area_density": 0.45,
                "lighting_mode": "DAYLIGHT",
                "total_pcu": pcu_res.total_pcu,
                "clearance_sec": pcu_res.estimated_clearance_time_sec,
                "annotated_image_b64": f"data:image/jpeg;base64,{img_b64}"
            })


def main():
    print("=" * 70)
    print("      FLOWGRID DYNAMIC FULL-STACK SERVER (REST API + DASHBOARD)")
    print("=" * 70)
    print(f"[*] Dashboard & Static Files : {FRONTEND_DIR}")
    print(f"[*] Local Web Endpoint       : http://localhost:{PORT}")
    print(f"[*] REST APIs Available      : /api/optimize, /api/corridor, /api/detect, /api/status")
    print(f"[*] YOLOv8 Model Status      : {'ACTIVE (TensorRT/PyTorch)' if HAS_YOLO else 'STANDBY (Mock/Sim)'}")
    print("=" * 70)
    print("[*] Launching browser automatically... Press Ctrl+C to stop.\n")

    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), FlowGridAPIHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] FlowGrid server stopped by user.")


if __name__ == "__main__":
    main()
