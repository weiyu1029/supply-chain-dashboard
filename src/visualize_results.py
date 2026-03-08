import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("outputs")
CHART_DIR = OUTPUT_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

def plot_top_shipments():
    shipments = pd.read_csv(OUTPUT_DIR / "optimal_shipments.csv")

    if shipments.empty:
        print("No shipment results found.")
        return

    top_shipments = shipments.sort_values("Shipment", ascending=False).head(15).copy()
    top_shipments["Lane"] = top_shipments["Plant"] + " → " + top_shipments["Market"]

    plt.figure(figsize=(10, 6))
    plt.barh(top_shipments["Lane"], top_shipments["Shipment"])
    plt.xlabel("Shipment Quantity")
    plt.ylabel("Lane")
    plt.title("Top 15 Shipment Lanes")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(CHART_DIR / "top_15_shipment_lanes.png")
    plt.close()

def plot_plant_utilization():
    shipments = pd.read_csv(OUTPUT_DIR / "optimal_shipments.csv")
    plants = pd.read_csv(PROCESSED_DIR / "plants.csv")

    outbound = shipments.groupby("Plant", as_index=False)["Shipment"].sum()
    plant_util = plants.merge(outbound, on="Plant", how="left").fillna(0)
    plant_util["UtilizationRate"] = plant_util["Shipment"] / plant_util["Capacity"]

    top_util = plant_util.sort_values("UtilizationRate", ascending=False).head(15).copy()

    plt.figure(figsize=(10, 6))
    plt.barh(top_util["Plant"], top_util["UtilizationRate"])
    plt.xlabel("Utilization Rate")
    plt.ylabel("Plant")
    plt.title("Top 15 Plant Utilization Rates")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(CHART_DIR / "top_15_plant_utilization.png")
    plt.close()

def plot_scenario_profit():
    scenario = pd.read_csv(OUTPUT_DIR / "scenario_summary.csv")

    plt.figure(figsize=(8, 5))
    plt.bar(scenario["Scenario"], scenario["TotalProfit"])
    plt.xlabel("Scenario")
    plt.ylabel("Total Profit")
    plt.title("Profit by Demand Scenario")
    plt.tight_layout()
    plt.savefig(CHART_DIR / "scenario_profit_comparison.png")
    plt.close()

def plot_scenario_active_lanes():
    scenario = pd.read_csv(OUTPUT_DIR / "scenario_summary.csv")

    plt.figure(figsize=(8, 5))
    plt.bar(scenario["Scenario"], scenario["ActiveLanes"])
    plt.xlabel("Scenario")
    plt.ylabel("Number of Active Lanes")
    plt.title("Active Shipment Lanes by Scenario")
    plt.tight_layout()
    plt.savefig(CHART_DIR / "scenario_active_lanes.png")
    plt.close()


if __name__ == "__main__":
    plot_top_shipments()
    plot_plant_utilization()
    plot_scenario_profit()
    plot_scenario_active_lanes()
    print("Charts created in outputs/charts/")

