import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path

OUTPUT_DIR = Path("outputs")
CHART_DIR = OUTPUT_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

def plot_supply_chain_network(top_n=40):
    shipments = pd.read_csv(OUTPUT_DIR / "optimal_shipments.csv")

    if shipments.empty:
        print("No shipment results found.")
        return

    # 只畫 shipment 最大的前幾條，避免圖太亂
    top_shipments = shipments.sort_values("Shipment", ascending=False).head(top_n).copy()

    plants = sorted(top_shipments["Plant"].unique())
    markets = sorted(top_shipments["Market"].unique())

    G = nx.DiGraph()

    for p in plants:
        G.add_node(p, node_type="plant")
    for m in markets:
        G.add_node(m, node_type="market")

    for _, row in top_shipments.iterrows():
        G.add_edge(row["Plant"], row["Market"], weight=row["Shipment"])

    pos = {}

    # Plant 放左邊
    for i, p in enumerate(plants):
        pos[p] = (0, -i)

    # Market 放右邊
    for i, m in enumerate(markets):
        pos[m] = (1, -i)

    plt.figure(figsize=(14, 10))

    plant_nodes = [n for n, d in G.nodes(data=True) if d["node_type"] == "plant"]
    market_nodes = [n for n, d in G.nodes(data=True) if d["node_type"] == "market"]

    nx.draw_networkx_nodes(G, pos, nodelist=plant_nodes, node_size=1200)
    nx.draw_networkx_nodes(G, pos, nodelist=market_nodes, node_size=1200)

    edges = G.edges(data=True)
    widths = [max(1, e[2]["weight"] / 500) for e in edges]

    nx.draw_networkx_edges(G, pos, width=widths, arrows=True, arrowstyle="->")
    nx.draw_networkx_labels(G, pos, font_size=8)

    plt.title("Supply Chain Network Graph (Top Shipment Lanes)")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(CHART_DIR / "supply_chain_network_graph.png")
    plt.close()

    print("Network graph saved to outputs/charts/")

if __name__ == "__main__":
    plot_supply_chain_network()

 
