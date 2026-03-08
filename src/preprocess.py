import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def build_scenario():
    plants = pd.read_csv(RAW_DIR / "plants_100k.csv")
    demand = pd.read_csv(RAW_DIR / "demand_100k.csv")
    transport = pd.read_csv(RAW_DIR / "transport_cost_100k.csv")

    week = "2025-01-06"
    product = "SKU_A"

    plants_s = plants[
        (plants["WeekStart"] == week) &
        (plants["Product"] == product)
    ]

    plants_s = plants_s.groupby("PlantID", as_index=False).agg({
        "CapacityUnits": "mean",
        "ProductionCostPerUnit": "mean"
    })

    plants_s = plants_s.rename(columns={
        "PlantID": "Plant",
        "CapacityUnits": "Capacity",
        "ProductionCostPerUnit": "ProductionCost"
    })

    demand_s = demand[
        (demand["WeekStart"] == week) &
        (demand["Product"] == product)
    ]

    demand_s = demand_s.groupby("MarketID", as_index=False).agg({
        "DemandUnits": "mean",
        "SellingPricePerUnit": "mean"
    })

    demand_s = demand_s.rename(columns={
        "MarketID": "Market",
        "DemandUnits": "Demand",
        "SellingPricePerUnit": "Price"
    })

    transport_s = transport[transport["Product"] == product]

    transport_s = transport_s.groupby(
        ["PlantID", "MarketID"], as_index=False
    ).agg({
        "TransportCostPerUnit": "mean"
    })

    transport_s = transport_s.rename(columns={
        "PlantID": "Plant",
        "MarketID": "Market",
        "TransportCostPerUnit": "Cost"
    })

    plants_s.to_csv(PROCESSED_DIR / "plants.csv", index=False)
    demand_s.to_csv(PROCESSED_DIR / "demand.csv", index=False)
    transport_s.to_csv(PROCESSED_DIR / "transport_cost.csv", index=False)

    print("Scenario created!")
    print(f"Plants rows: {len(plants_s)}")
    print(f"Demand rows: {len(demand_s)}")
    print(f"Transport rows: {len(transport_s)}")


if __name__ == "__main__":
    build_scenario()
