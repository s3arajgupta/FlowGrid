"""
FlowGrid - Multi-Scenario Traffic Simulator & Benchmark Suite
Module: src.simulator

Simulates intersection dynamics under varying ASEAN traffic loads.
Generates side-by-side comparison between Fixed-Cycle Baseline and FlowGrid Adaptive.
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from src.pcu import PCUCalculator, ApproachDemand
from src.optimizer import AdaptiveSignalOptimizer, CyclePlan


@dataclass
class SimulationResult:
    scenario_name: str
    description: str
    demands: Dict[str, ApproachDemand]
    fixed_plan: Dict[str, Any]
    adaptive_plan: CyclePlan
    fixed_delay_sec: float
    adaptive_delay_sec: float
    delay_reduction_pct: float
    wasted_green_saved_sec: int


class TrafficSimulator:
    """
    Simulates traffic scenarios to benchmark FlowGrid against fixed-cycle timers.
    """

    def __init__(self):
        self.pcu_calc = PCUCalculator()
        self.optimizer = AdaptiveSignalOptimizer()

    def create_scenario_hcmc_peak(self) -> Dict[str, Dict[str, int]]:
        """
        Scenario 1: HCMC Morning Peak
        Nguyen Hue (Northbound major) has massive motorcycle surge (80 motorcycles, 6 cars).
        Le Loi (Eastbound minor) has light traffic (4 cars, 1 bus).
        """
        return {
            "north": {"motorcycle": 80, "car": 6, "bus": 2, "truck": 0},
            "south": {"motorcycle": 35, "car": 4, "bus": 1, "truck": 0},
            "east":  {"motorcycle": 10, "car": 4, "bus": 1, "truck": 0},
            "west":  {"motorcycle": 8,  "car": 2, "bus": 0, "truck": 0}
        }

    def create_scenario_truck_corridor(self) -> Dict[str, Dict[str, int]]:
        """
        Scenario 2: Arterial Industrial Surge
        Minor street has heavy container trucks and buses.
        Raw counts look low (12 vehicles), but PCU demand is massive (25+ PCU).
        """
        return {
            "north": {"motorcycle": 30, "car": 5, "bus": 0, "truck": 0},   # 20.0 PCU
            "south": {"motorcycle": 20, "car": 3, "bus": 0, "truck": 0},   # 13.0 PCU
            "east":  {"motorcycle": 4,  "car": 3, "bus": 3, "truck": 5},   # 27.5 PCU (Heavy!)
            "west":  {"motorcycle": 6,  "car": 2, "bus": 1, "truck": 2}    # 13.5 PCU
        }

    def create_scenario_night_mode(self) -> Dict[str, Dict[str, int]]:
        """
        Scenario 3: Late Night (Off-Peak)
        Very low demand across all approaches.
        """
        return {
            "north": {"motorcycle": 4, "car": 2, "bus": 0, "truck": 0},
            "south": {"motorcycle": 3, "car": 1, "bus": 0, "truck": 0},
            "east":  {"motorcycle": 1, "car": 1, "bus": 0, "truck": 0},
            "west":  {"motorcycle": 2, "car": 0, "bus": 0, "truck": 0}
        }

    def run_benchmark(self,
                      scenario_name: str,
                      description: str,
                      raw_counts: Dict[str, Dict[str, int]],
                      emergency_approach: str = None,
                      is_night: bool = False) -> SimulationResult:
        """
        Runs side-by-side benchmark for a scenario.
        """
        # 1. Compute PCU Demands
        demands = {}
        for app_id, counts in raw_counts.items():
            density = min(1.0, sum(counts.values()) / 100.0)
            demands[app_id] = self.pcu_calc.compute_demand(
                approach_id=app_id,
                vehicle_counts=counts,
                area_density=density,
                is_night_count_only=is_night
            )

        # 2. Fixed-Cycle Baseline (Typical 30s Major, 30s Minor, 5s Yellow/Red = 70s cycle)
        fixed_g1 = 30
        fixed_g2 = 30
        fixed_cycle = 70

        p1_demand = max(demands["north"].total_pcu, demands["south"].total_pcu)
        p2_demand = max(demands["east"].total_pcu, demands["west"].total_pcu)

        fixed_delay_p1 = (fixed_cycle - fixed_g1) * p1_demand * 0.5
        fixed_delay_p2 = (fixed_cycle - fixed_g2) * p2_demand * 0.5
        fixed_total_delay = fixed_delay_p1 + fixed_delay_p2

        fixed_plan = {
            "p1_green": fixed_g1,
            "p2_green": fixed_g2,
            "total_cycle": fixed_cycle,
            "total_delay_sec": round(fixed_total_delay, 1)
        }

        # 3. FlowGrid Adaptive Optimization
        adaptive_plan = self.optimizer.optimize_2phase(
            demands=demands,
            emergency_approach=emergency_approach
        )

        adaptive_delay = adaptive_plan.estimated_total_delay_sec

        # Delay improvement calculation
        if fixed_total_delay > 0:
            improvement_pct = ((fixed_total_delay - adaptive_delay) / fixed_total_delay) * 100.0
        else:
            improvement_pct = 0.0

        # Wasted green time saved (in seconds)
        wasted_saved = abs(fixed_g2 - adaptive_plan.phases[1].green_seconds) if len(adaptive_plan.phases) > 1 else 0

        return SimulationResult(
            scenario_name=scenario_name,
            description=description,
            demands=demands,
            fixed_plan=fixed_plan,
            adaptive_plan=adaptive_plan,
            fixed_delay_sec=round(fixed_total_delay, 1),
            adaptive_delay_sec=round(adaptive_delay, 1),
            delay_reduction_pct=round(improvement_pct, 1),
            wasted_green_saved_sec=wasted_saved
        )
