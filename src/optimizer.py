"""
FlowGrid - Adaptive Signal Optimization Engine
Module: src.optimizer

Optimizes green phase allocation dynamically based on PCU-weighted demand,
minimum/maximum safety bounds, yellow clearance intervals, and fairness constraints.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from src.pcu import ApproachDemand


@dataclass
class PhaseAllocation:
    """Represents the timing plan for a signal cycle."""
    phase_id: str
    phase_name: str
    active_approaches: List[str]
    green_seconds: int
    yellow_seconds: int = 3
    all_red_seconds: int = 2
    allocated_pcu_demand: float = 0.0
    is_preempted_emergency: bool = False


@dataclass
class CyclePlan:
    """Complete cycle plan with multiple phases."""
    cycle_id: int
    phases: List[PhaseAllocation]
    total_cycle_seconds: int
    total_pcu_serviced: float
    estimated_total_delay_sec: float
    is_emergency_override: bool = False


class AdaptiveSignalOptimizer:
    """
    Computes real-time green time allocations for an intersection.
    Enforces NEMA constraints, min/max limits, fairness caps, and emergency interrupts.
    """

    def __init__(self,
                 min_green: int = 10,
                 max_green: int = 70,
                 yellow_clearance: int = 3,
                 all_red_clearance: int = 2,
                 max_wait_fairness: int = 90,
                 delay_weight: float = 1.0,
                 fairness_weight: float = 1.5,
                 queue_overflow_weight: float = 2.0):
        self.min_green = min_green
        self.max_green = max_green
        self.yellow_clearance = yellow_clearance
        self.all_red_clearance = all_red_clearance
        self.max_wait_fairness = max_wait_fairness

        self.delay_weight = delay_weight
        self.fairness_weight = fairness_weight
        self.queue_overflow_weight = queue_overflow_weight

        # Track wait times across cycles for fairness
        self.cumulative_wait_times: Dict[str, float] = {}

    def optimize_2phase(self,
                        demands: Dict[str, ApproachDemand],
                        emergency_approach: Optional[str] = None,
                        corridor_offset_sec: int = 0) -> CyclePlan:
        """
        Optimizes standard 2-Phase intersection:
          - Phase 1 (Major): North & South approaches
          - Phase 2 (Minor): East & West approaches
        """
        # Update cumulative wait counters
        for app_id in ["north", "south", "east", "west"]:
            if app_id not in self.cumulative_wait_times:
                self.cumulative_wait_times[app_id] = 0.0

        # Check Emergency Preemption
        if emergency_approach:
            return self._handle_emergency_preemption(demands, emergency_approach)

        # Aggregate PCU demand per phase
        p1_demand = max(
            demands.get("north", ApproachDemand("north")).total_pcu,
            demands.get("south", ApproachDemand("south")).total_pcu
        )
        p2_demand = max(
            demands.get("east", ApproachDemand("east")).total_pcu,
            demands.get("west", ApproachDemand("west")).total_pcu
        )

        # Density penalty (if an approach is packed with high density)
        p1_max_density = max(
            demands.get("north", ApproachDemand("north")).area_density,
            demands.get("south", ApproachDemand("south")).area_density
        )
        p2_max_density = max(
            demands.get("east", ApproachDemand("east")).area_density,
            demands.get("west", ApproachDemand("west")).area_density
        )

        # Effective demand adjusted with density overflow penalty
        eff_p1 = p1_demand * (1.0 + self.queue_overflow_weight * max(0.0, p1_max_density - 0.5))
        eff_p2 = p2_demand * (1.0 + self.queue_overflow_weight * max(0.0, p2_max_density - 0.5))

        # Check fairness threshold (has any minor approach waited too long?)
        p1_wait = max(self.cumulative_wait_times.get("north", 0), self.cumulative_wait_times.get("south", 0))
        p2_wait = max(self.cumulative_wait_times.get("east", 0), self.cumulative_wait_times.get("west", 0))

        if p2_wait >= self.max_wait_fairness:
            eff_p2 *= self.fairness_weight

        # Proportional green time allocation
        total_effective = eff_p1 + eff_p2
        if total_effective <= 0.01:
            g1 = self.min_green
            g2 = self.min_green
        else:
            # Baseline available green budget (~60s default nominal split)
            green_budget = 60
            raw_g1 = int(round((eff_p1 / total_effective) * green_budget))
            raw_g2 = int(round((eff_p2 / total_effective) * green_budget))

            # Apply hard constraints
            g1 = max(self.min_green, min(self.max_green, raw_g1))
            g2 = max(self.min_green, min(self.max_green, raw_g2))

        # Apply corridor green wave adjustment (if applicable)
        if corridor_offset_sec > 0:
            # Shift green start/extension along arterial major street
            g1 = min(self.max_green, g1 + min(10, corridor_offset_sec // 4))

        # Update wait timers
        self.cumulative_wait_times["north"] = 0.0
        self.cumulative_wait_times["south"] = 0.0
        self.cumulative_wait_times["east"] += (g1 + self.yellow_clearance + self.all_red_clearance)
        self.cumulative_wait_times["west"] += (g1 + self.yellow_clearance + self.all_red_clearance)

        total_cycle = (g1 + self.yellow_clearance + self.all_red_clearance) + \
                      (g2 + self.yellow_clearance + self.all_red_clearance)

        # Estimate delay
        delay_p1 = (total_cycle - g1) * p1_demand * 0.5
        delay_p2 = (total_cycle - g2) * p2_demand * 0.5
        total_delay = delay_p1 + delay_p2

        phases = [
            PhaseAllocation(
                phase_id="Phase_1",
                phase_name="Major Street (Nguyen Hue)",
                active_approaches=["north", "south"],
                green_seconds=g1,
                yellow_seconds=self.yellow_clearance,
                all_red_seconds=self.all_red_clearance,
                allocated_pcu_demand=round(p1_demand, 2)
            ),
            PhaseAllocation(
                phase_id="Phase_2",
                phase_name="Minor Street (Le Loi)",
                active_approaches=["east", "west"],
                green_seconds=g2,
                yellow_seconds=self.yellow_clearance,
                all_red_seconds=self.all_red_clearance,
                allocated_pcu_demand=round(p2_demand, 2)
            )
        ]

        return CyclePlan(
            cycle_id=1,
            phases=phases,
            total_cycle_seconds=total_cycle,
            total_pcu_serviced=round(p1_demand + p2_demand, 2),
            estimated_total_delay_sec=round(total_delay, 1),
            is_emergency_override=False
        )

    def _handle_emergency_preemption(self,
                                     demands: Dict[str, ApproachDemand],
                                     emergency_approach: str) -> CyclePlan:
        """Immediate priority green allocation for first responders."""
        is_major = emergency_approach in ["north", "south"]
        p_name = "EMERGENCY PREEMPTION: " + ("Major Street" if is_major else "Minor Street")
        active = ["north", "south"] if is_major else ["east", "west"]

        phases = [
            PhaseAllocation(
                phase_id="Phase_EMERGENCY",
                phase_name=p_name,
                active_approaches=active,
                green_seconds=self.max_green,
                yellow_seconds=self.yellow_clearance,
                all_red_seconds=self.all_red_clearance,
                allocated_pcu_demand=demands.get(emergency_approach, ApproachDemand(emergency_approach)).total_pcu,
                is_preempted_emergency=True
            )
        ]

        return CyclePlan(
            cycle_id=999,
            phases=phases,
            total_cycle_seconds=self.max_green + self.yellow_clearance + self.all_red_clearance,
            total_pcu_serviced=demands.get(emergency_approach, ApproachDemand(emergency_approach)).total_pcu,
            estimated_total_delay_sec=0.0,
            is_emergency_override=True
        )
