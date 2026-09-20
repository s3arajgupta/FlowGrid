"""
FlowGrid - Passenger Car Unit (PCU) Calculation Engine
Module: src.pcu

Converts heterogeneous raw vehicle counts into standardized Passenger Car Units (PCU)
and calculates saturation flow rates adjusted for ASEAN motorcycle filtering behavior.
"""

from typing import Dict, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class ApproachDemand:
    """Standardized descriptor of traffic demand on a single approach."""
    approach_id: str
    vehicle_counts: Dict[str, int] = field(default_factory=lambda: {"motorcycle": 0, "car": 0, "bus": 0, "truck": 0})
    area_density: float = 0.0  # 0.0 to 1.0 (% of ROI road area occupied)
    total_pcu: float = 0.0
    motorcycle_ratio: float = 0.0
    adjusted_saturation_flow: float = 0.55  # PCU / sec
    estimated_clearance_time_sec: float = 0.0
    night_mode_active: bool = False
    source: str = "VISION_YOLO"


class PCUCalculator:
    """
    Calculates standardized traffic demand using Passenger Car Units (PCU).
    Default PCU Weights:
      - Motorcycle / 2-wheeler: 0.5
      - Car / 4-wheeler:        1.0 (Reference Unit)
      - Bus (Xe buýt):          2.5
      - Truck (Xe tải):         3.0
    """

    DEFAULT_WEIGHTS = {
        "motorcycle": 0.5,
        "car": 1.0,
        "bus": 2.5,
        "truck": 3.0,
    }

    def __init__(self,
                 custom_weights: Dict[str, float] = None,
                 base_sat_flow: float = 0.55,
                 motorcycle_accel_bonus: float = 0.40):
        self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        self.base_sat_flow = base_sat_flow
        self.motorcycle_accel_bonus = motorcycle_accel_bonus

    def compute_demand(self,
                       approach_id: str,
                       vehicle_counts: Dict[str, int],
                       area_density: float = 0.0,
                       is_night_count_only: bool = False,
                       source: str = "VISION_YOLO") -> ApproachDemand:
        """
        Converts raw vehicle counts into PCU and computes saturation clearance dynamics.
        """
        counts = {k: max(0, int(v)) for k, v in vehicle_counts.items()}

        if is_night_count_only:
            # In full dark night mode: 1 object = 1 PCU
            total_vehicles = sum(counts.values())
            total_pcu = float(total_vehicles)
            moto_ratio = 0.0
            adjusted_sat_flow = self.base_sat_flow
            clearance_time = total_pcu / adjusted_sat_flow if adjusted_sat_flow > 0 else 0.0

            return ApproachDemand(
                approach_id=approach_id,
                vehicle_counts=counts,
                area_density=area_density,
                total_pcu=round(total_pcu, 2),
                motorcycle_ratio=0.0,
                adjusted_saturation_flow=round(adjusted_sat_flow, 2),
                estimated_clearance_time_sec=round(clearance_time, 1),
                night_mode_active=True,
                source=source
            )

        # Standard PCU Calculation
        total_pcu = 0.0
        for v_type, count in counts.items():
            weight = self.weights.get(v_type, 1.0)
            total_pcu += count * weight

        total_vehicles = sum(counts.values())
        motorcycle_count = counts.get("motorcycle", 0)
        moto_ratio = (motorcycle_count / total_vehicles) if total_vehicles > 0 else 0.0

        # Saturation flow rate adjustment:
        # Motorcycle-dense queues accelerate faster off the line (filtering effect)
        # S = S_base * (1 + bonus * motorcycle_ratio)
        adjusted_sat_flow = self.base_sat_flow * (1.0 + self.motorcycle_accel_bonus * moto_ratio)
        clearance_time = (total_pcu / adjusted_sat_flow) if adjusted_sat_flow > 0 else 0.0

        return ApproachDemand(
            approach_id=approach_id,
            vehicle_counts=counts,
            area_density=round(area_density, 3),
            total_pcu=round(total_pcu, 2),
            motorcycle_ratio=round(moto_ratio, 3),
            adjusted_saturation_flow=round(adjusted_sat_flow, 3),
            estimated_clearance_time_sec=round(clearance_time, 1),
            night_mode_active=False,
            source=source
        )

    def explain_pcu_vs_raw(self, approach_a: Dict[str, int], approach_b: Dict[str, int],
                           name_a: str = "Approach A", name_b: str = "Approach B") -> str:
        """
        Generates an educational comparison illustrating why raw counts fail in ASEAN traffic.
        """
        raw_a = sum(approach_a.values())
        raw_b = sum(approach_b.values())

        pcu_a = sum(approach_a.get(k, 0) * self.weights.get(k, 1.0) for k in self.weights)
        pcu_b = sum(approach_b.get(k, 0) * self.weights.get(k, 1.0) for k in self.weights)

        raw_ratio = (raw_a / raw_b) if raw_b > 0 else float('inf')
        pcu_ratio = (pcu_a / pcu_b) if pcu_b > 0 else float('inf')

        output = [
            f"\n{'='*70}",
            f"FLOWGRID PCU DEMAND ANALYSIS: {name_a} vs {name_b}",
            f"{'='*70}",
            f"1. Raw Vehicle Count Comparison:",
            f"   - {name_a}: {raw_a} vehicles {approach_a}",
            f"   - {name_b}: {raw_b} vehicles {approach_b}",
            f"   -> Raw Demand Ratio ({name_a} : {name_b}) = {raw_ratio:.2f} : 1.00",
            f"\n2. FlowGrid PCU-Weighted Demand Comparison:",
            f"   - {name_a}: {pcu_a:.1f} PCU (Motorcycles: {approach_a.get('motorcycle', 0)}*0.5, Cars: {approach_a.get('car',0)}*1.0)",
            f"   - {name_b}: {pcu_b:.1f} PCU (Trucks: {approach_b.get('truck',0)}*3.0, Buses: {approach_b.get('bus',0)}*2.5, Cars: {approach_b.get('car',0)}*1.0)",
            f"   -> Real Road Capacity Demand Ratio = {pcu_ratio:.2f} : 1.00",
            f"\n3. First-Principles Verdict:",
            f"   Naive systems allocating green time purely on vehicle counts would give",
            f"   {name_a} {raw_ratio:.1f}x green time, severely starving {name_b}'s buses and trucks.",
            f"   FlowGrid correctly evaluates true demand ({pcu_a:.1f} PCU vs {pcu_b:.1f} PCU).",
            f"{'='*70}\n"
        ]
        return "\n".join(output)
