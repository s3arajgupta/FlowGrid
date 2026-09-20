"""
FlowGrid - Vision Processing & YOLO Detection Layer
Module: src.detector

Extracts vehicle counts and computes road area density from camera frames.
Supports YOLOv8 inference, 4 vehicle classes (motorcycle, car, bus, truck),
area-density estimation, and night-time lighting tier classification.
"""

import os
from typing import Dict, List, Tuple, Any, Optional


# Try importing ultralytics and cv2, provide robust fallback for pure-python environments
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


# COCO standard class mappings for vehicles
COCO_VEHICLE_MAP = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}


class FlowGridDetector:
    """
    Edge Vision Detector running YOLOv8 for vehicle classification,
    bounding box area density calculation, and ambient lighting check.
    """

    def __init__(self,
                 model_path: str = "yolov8n.pt",
                 conf_threshold: float = 0.35,
                 iou_threshold: float = 0.45,
                 night_dusk_threshold: float = 50.0,
                 night_dark_threshold: float = 22.0):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.night_dusk_threshold = night_dusk_threshold
        self.night_dark_threshold = night_dark_threshold

        self.model = None
        if HAS_YOLO:
            try:
                # Load pretrained YOLOv8 model (auto downloads yolov8n.pt if not present)
                self.model = YOLO(model_path)
            except Exception as e:
                print(f"[FlowGridDetector] Warning: Could not initialize YOLO model: {e}")

    def check_ambient_lighting(self, image: Any) -> Tuple[float, str]:
        """
        Determines lighting tier: 'DAYLIGHT', 'DUSK_IR_ASSIST', or 'DARK_COUNT_ONLY'.
        """
        if not HAS_CV2 or image is None:
            return 100.0, "DAYLIGHT"

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        mean_brightness = float(np.mean(gray))

        if mean_brightness < self.night_dark_threshold:
            mode = "DARK_COUNT_ONLY"
        elif mean_brightness < self.night_dusk_threshold:
            mode = "DUSK_IR_ASSIST"
        else:
            mode = "DAYLIGHT"

        return mean_brightness, mode

    def calculate_area_density(self,
                              boxes_xyxy: List[List[float]],
                              roi_width: int,
                              roi_height: int) -> float:
        """
        Computes the ratio of road ROI area occupied by detected vehicle bounding boxes.
        In motorcycle-fluid ASEAN traffic, this captures congestion density independent of lane discipline.
        """
        if roi_width <= 0 or roi_height <= 0 or not boxes_xyxy:
            return 0.0

        total_roi_area = float(roi_width * roi_height)
        total_box_area = 0.0

        for box in boxes_xyxy:
            x1, y1, x2, y2 = box[:4]
            # Clip box to ROI
            x1 = max(0, min(roi_width, x1))
            x2 = max(0, min(roi_width, x2))
            y1 = max(0, min(roi_height, y1))
            y2 = max(0, min(roi_height, y2))

            box_w = max(0.0, x2 - x1)
            box_h = max(0.0, y2 - y1)
            total_box_area += (box_w * box_h)

        # Simplified occupancy with overlap mitigation cap
        density = min(1.0, total_box_area / total_roi_area)
        return float(density)

    def detect_frame(self,
                     image: Any,
                     roi_polygon: Optional[List[Tuple[int, int]]] = None) -> Dict[str, Any]:
        """
        Runs object detection on a single frame or image.
        Returns:
          - vehicle_counts: dict of count per class
          - area_density: float [0.0 - 1.0]
          - lighting_mode: str
          - raw_detections: list of boxes
        """
        if image is None:
            return {
                "vehicle_counts": {"motorcycle": 0, "car": 0, "bus": 0, "truck": 0},
                "area_density": 0.0,
                "lighting_mode": "DAYLIGHT",
                "raw_detections": []
            }

        height, width = image.shape[:2]
        brightness, lighting_mode = self.check_ambient_lighting(image)

        counts = {"motorcycle": 0, "car": 0, "bus": 0, "truck": 0}
        boxes_xyxy = []
        raw_detections = []

        if self.model is not None and HAS_YOLO:
            results = self.model.predict(
                source=image,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False
            )

            if len(results) > 0:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    xyxy = box.xyxy[0].tolist()

                    if cls_id in COCO_VEHICLE_MAP:
                        v_class = COCO_VEHICLE_MAP[cls_id]
                        counts[v_class] += 1
                        boxes_xyxy.append(xyxy)
                        raw_detections.append({
                            "class": v_class,
                            "confidence": round(conf, 3),
                            "box": [round(x, 1) for x in xyxy]
                        })

        area_density = self.calculate_area_density(boxes_xyxy, width, height)

        return {
            "vehicle_counts": counts,
            "area_density": round(area_density, 3),
            "ambient_brightness": round(brightness, 1),
            "lighting_mode": lighting_mode,
            "total_detected": sum(counts.values()),
            "raw_detections": raw_detections
        }

    def draw_overlay(self,
                     image: Any,
                     detection_result: Dict[str, Any],
                     pcu_demand: Optional[Any] = None) -> np.ndarray:
        """
        Draws visual annotations, bounding boxes, PCU badge, and area density meter onto the image.
        """
        if not HAS_CV2 or image is None:
            return image

        annotated = image.copy()
        h, w = annotated.shape[:2]

        color_map = {
            "motorcycle": (0, 255, 255),  # Yellow
            "car": (255, 128, 0),         # Blue/Orange
            "bus": (0, 200, 0),           # Green
            "truck": (0, 0, 255)          # Red
        }

        # Draw bounding boxes
        for det in detection_result.get("raw_detections", []):
            x1, y1, x2, y2 = [int(v) for v in det["box"]]
            v_cls = det["class"]
            conf = det["confidence"]
            color = color_map.get(v_cls, (255, 255, 255))

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{v_cls.upper()} {conf:.2f}"
            cv2.putText(annotated, label, (x1, max(15, y1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Draw HUD Panel (top-left)
        hud_bg = np.zeros((140, 360, 3), dtype=np.uint8)
        alpha = 0.7
        roi_hud = annotated[10:150, 10:370]
        if roi_hud.shape[0] == 140 and roi_hud.shape[1] == 360:
            annotated[10:150, 10:370] = cv2.addWeighted(roi_hud, 1 - alpha, hud_bg, alpha, 0)

        # HUD Text
        counts = detection_result["vehicle_counts"]
        density = detection_result["area_density"]
        mode = detection_result["lighting_mode"]

        cv2.putText(annotated, "FLOWGRID VISION TELEMETRY", (20, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        cv2.putText(annotated, f"Motorcycles: {counts['motorcycle']} | Cars: {counts['car']}", (20, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        cv2.putText(annotated, f"Buses: {counts['bus']} | Trucks: {counts['truck']}", (20, 78),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        cv2.putText(annotated, f"Area Density: {density*100:.1f}% | Mode: {mode}", (20, 98),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0) if density < 0.6 else (0, 0, 255), 1)

        if pcu_demand is not None:
            pcu_val = getattr(pcu_demand, 'total_pcu', 0.0)
            clearance = getattr(pcu_demand, 'estimated_clearance_time_sec', 0.0)
            cv2.putText(annotated, f"DEMAND: {pcu_val:.1f} PCU | Est Clear: {clearance}s", (20, 128),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 255), 2)

        return annotated
