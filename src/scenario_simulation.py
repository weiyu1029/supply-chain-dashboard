import pandas as pd
import pulp
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def solve_scenario(demand_multiplier=1.0, scenario_name="Base"):
    plants = pd.read_csv(PROCESSED_DIR / "plants.csv")
    demand = pd.read_csv(PROCESSED_DIR / "demand.csv")
    transport = pd.read_csv(PROCESSED_DIR / "transport_cost.csv")

    # 調整 demand
    demand = demand.copy()
    demand["Demand"] = demand["Demand"] * demand_multiplier

    model = pulp.LpProblem(f"SupplyChainOptimization_{scenario_name}", pulp.LpMaximize)

    plant_capacity = dict(zip(plants["Plant"], plants["Capacity"]))
    plant_prod_cost = dict(zip(plants["Plant"], plants["ProductionCost"]))
    market_demand = dict(zip(demand["Market"], demand["Demand"]))
    market_price = dict(zip(demand["Market"], demand["Price"]))

    lanes = list(zip(transport["Plant"], transport["Market"]))
    lane_cost = {
        (row["Plant"], row["Market"]): row["Cost"]
        for _, row in transport.iterrows()
    }

    shipment = {
        (i, j): pulp.LpVariable(f"ship_{i}_{j}", lowBound=0)
        for (i, j) in lanes
    }

    model += pulp.lpSum(
        (market_price[j] - plant_prod_cost[i] - lane_cost[(i, j)]) * shipment[(i, j)]
        for (i, j) in lanes
    )

    for i in plants["Plant"]:
        outgoing_lanes = [(p, m) for (p, m) in lanes if p == i]
        model += pulp.lpSum(shipment[(p, m)] for (p, m) in outgoing_lanes) <= plant_capacity[i], f"Capacity_{i}"

    skipped_markets = 0
    for j in demand["Market"]:
        incoming_lanes = [(p, m) for (p, m) in lanes if m == j]
        if len(incoming_lanes) == 0:
            skipped_markets += 1
            continue

        model += pulp.lpSum(shipment[(p, m)] for (p, m) in incoming_lanes) >= market_demand[j], f"Demand_{j}"

    model.solve()

    status = pulp.LpStatus[model.status]
    total_profit = pulp.value(model.objective)

    results = []
    for (i, j) in lanes:
        qty = shipment[(i, j)].varValue
        if qty is not None and qty > 0:
            results.append({
                "Scenario": scenario_name,
                "Plant": i,
                "Market": j,
                "Shipment": qty
            })

    result_df = pd.DataFrame(results)

    summary = {
        "Scenario": scenario_name,
        "DemandMultiplier": demand_multiplier,
        "Status": status,
        "TotalProfit": total_profit,
        "ActiveLanes": len(result_df),
        "SkippedMarketsNoLane": skipped_markets
    }

    return summary, result_df

def run_all_scenarios():
    scenarios = [
        ("Low Demand", 0.70),
        ("Base Demand", 1.00),
        ("High Demand", 1.30),
    ]

    summary_rows = []
    shipment_frames = []

    for scenario_name, multiplier in scenarios:
        print(f"Running {scenario_name}...")
        summary, result_df = solve_scenario(
            demand_multiplier=multiplier,
            scenario_name=scenario_name
        )
        summary_rows.append(summary)
        shipment_frames.append(result_df)

    summary_df = pd.DataFrame(summary_rows)
    shipments_df = pd.concat(shipment_frames, ignore_index=True)

    summary_df.to_csv(OUTPUT_DIR / "scenario_summary.csv", index=False)
    shipments_df.to_csv(OUTPUT_DIR / "scenario_shipments.csv", index=False)

    print("\nScenario simulation completed!")
    print(summary_df)

if __name__ == "__main__":
    run_all_scenarios()
