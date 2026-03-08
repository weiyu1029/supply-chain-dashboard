import pandas as pd
import pulp
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def solve_model():
    plants = pd.read_csv(PROCESSED_DIR / "plants.csv")
    demand = pd.read_csv(PROCESSED_DIR / "demand.csv")
    transport = pd.read_csv(PROCESSED_DIR / "transport_cost.csv")

    model = pulp.LpProblem("SupplyChainOptimization", pulp.LpMaximize)

    # 建 dictionary 方便查值
    plant_capacity = dict(zip(plants["Plant"], plants["Capacity"]))
    plant_prod_cost = dict(zip(plants["Plant"], plants["ProductionCost"]))
    market_demand = dict(zip(demand["Market"], demand["Demand"]))
    market_price = dict(zip(demand["Market"], demand["Price"]))

    # 只使用存在的運輸路線
    lanes = list(zip(transport["Plant"], transport["Market"]))
    lane_cost = {
        (row["Plant"], row["Market"]): row["Cost"]
        for _, row in transport.iterrows()
    }

    # 只為有效 lane 建立變數
    shipment = {
        (i, j): pulp.LpVariable(f"ship_{i}_{j}", lowBound=0)
        for (i, j) in lanes
    }

    # 目標函數：最大化利潤
    model += pulp.lpSum(
        (market_price[j] - plant_prod_cost[i] - lane_cost[(i, j)]) * shipment[(i, j)]
        for (i, j) in lanes
    )

    # Plant capacity constraints
    for i in plants["Plant"]:
        outgoing_lanes = [(p, m) for (p, m) in lanes if p == i]
        model += pulp.lpSum(shipment[(p, m)] for (p, m) in outgoing_lanes) <= plant_capacity[i], f"Capacity_{i}"

    # Market demand constraints
    for j in demand["Market"]:
        incoming_lanes = [(p, m) for (p, m) in lanes if m == j]

        # 如果某個 market 完全沒有任何可進貨 lane，直接提醒
        if len(incoming_lanes) == 0:
            print(f"Warning: market {j} has no incoming transport lanes.")
            continue

        model += pulp.lpSum(shipment[(p, m)] for (p, m) in incoming_lanes) >= market_demand[j], f"Demand_{j}"

    # 求解
    model.solve()

    print("Status:", pulp.LpStatus[model.status])
    print("Total Profit:", pulp.value(model.objective))

    # 輸出結果
    results = []
    for (i, j) in lanes:
        qty = shipment[(i, j)].varValue
        if qty is not None and qty > 0:
            results.append({
                "Plant": i,
                "Market": j,
                "Shipment": qty
            })

    result_df = pd.DataFrame(results)
    result_df.to_csv(OUTPUT_DIR / "optimal_shipments.csv", index=False)

    summary_df = pd.DataFrame({
        "Metric": ["Status", "Total Profit", "Number of Active Lanes"],
        "Value": [
            pulp.LpStatus[model.status],
            pulp.value(model.objective),
            len(result_df)
        ]
    })
    summary_df.to_csv(OUTPUT_DIR / "optimization_summary.csv", index=False)

    print("Results saved!")
    print(f"Active shipment lanes: {len(result_df)}")

if __name__ == "__main__":
    solve_model()