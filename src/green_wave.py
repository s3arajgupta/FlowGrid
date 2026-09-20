"""
FlowGrid - Green Wave Corridor Coordination
Module: src.green_wave

Coordinates green waves across a sequence of intersections.
Dynamically adjusts offsets based on real-time speed from GPS floating car data.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class IntersectionNode:
    node_id: str
    name: str
    distance_from_prev_m: float  # distance in meters from previous intersection


@dataclass
class CorridorPlan:
    corridor_id: str
    corridor_name: str
    target_speed_kmh: float
    real_time_speed_kmh: float
    active_direction: str  # "INBOUND_AM" or "OUTBOUND_PM"
    node_offsets_sec: Dict[str, int] = field(default_factory=dict)


class CorridorCoordinator:
    """
    Computes dynamic offsets between consecutive intersections
    to maintain a smooth green wave.
    """

    def __init__(self,
                 corridor_id: str,
                 corridor_name: str,
                 intersections: List[IntersectionNode],
                 default_design_speed_kmh: float = 40.0):
        self.corridor_id = corridor_id
        self.corridor_name = corridor_name
        self.intersections = intersections
        self.design_speed_kmh = default_design_speed_kmh

    def compute_offsets(self,
                        real_time_speed_kmh: float = None,
                        time_of_day: str = "08:30") -> CorridorPlan:
        """
        Calculates time offset for each intersection along the corridor.
        Offset(N_i) = Distance(N_0 -> N_i) / Real_Time_Speed
        """
        speed = real_time_speed_kmh if (real_time_speed_kmh and real_time_speed_kmh > 5.0) else self.design_speed_kmh
        speed_mps = (speed * 1000.0) / 3600.0  # Convert km/h to m/s

        # Determine wave direction based on time of day
        hour = int(time_of_day.split(":")[0]) if ":" in time_of_day else 8
        if 6 <= hour < 12:
            direction = "INBOUND_AM"
            ordered_nodes = self.intersections
        elif 16 <= hour < 21:
            direction = "OUTBOUND_PM"
            ordered_nodes = list(reversed(self.intersections))
        else:
            direction = "OFF_PEAK_BALANCED"
            ordered_nodes = self.intersections

        offsets = {}
        accumulated_dist = 0.0

        for i, node in enumerate(ordered_nodes):
            if i == 0:
                offsets[node.node_id] = 0
            else:
                accumulated_dist += node.distance_from_prev_m
                # Offset in seconds = distance / speed
                offset_s = int(round(accumulated_dist / speed_mps))
                offsets[node.node_id] = offset_s

        return CorridorPlan(
            corridor_id=self.corridor_id,
            corridor_name=self.corridor_name,
            target_speed_kmh=self.design_speed_kmh,
            real_time_speed_kmh=speed,
            active_direction=direction,
            node_offsets_sec=offsets
        )
