import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Supply Chain Optimization Decision Dashboard")

st.write(
"""
Interactive analytics tool for evaluating supply chain shipment optimization.
"""
)

# -----------------------------
# Load Data
# -----------------------------

shipments = pd.read_csv("outputs/optimal_shipments.csv")
summary = pd.read_csv("outputs/optimization_summary.csv")

profit = summary.loc[summary["Metric"] == "Total Profit", "Value"].values[0]
lanes = summary.loc[summary["Metric"] == "Number of Active Lanes", "Value"].values[0]

# -----------------------------
# KPI
# -----------------------------

c1, c2, c3 = st.columns(3)

c1.metric("Total Profit", f"${float(profit):,.0f}")
c2.metric("Active Shipment Lanes", int(float(lanes)))
c3.metric("Total Shipment Volume", f"{shipments['Shipment'].sum():,.0f}")

st.divider()

# -----------------------------
# Sidebar Filters
# -----------------------------

st.sidebar.header("Filters")

plant_filter = st.sidebar.multiselect(
    "Focus Plants",
    sorted(shipments["Plant"].unique())
)

market_filter = st.sidebar.multiselect(
    "Focus Markets",
    sorted(shipments["Market"].unique())
)

top_n = st.sidebar.slider(
    "Top Routes",
    5,
    100,
    30
)

# -----------------------------
# Scenario Simulator
# -----------------------------

st.sidebar.header("Scenario Simulator")

demand_multiplier = st.sidebar.slider(
    "Demand Shock",
    0.5,
    1.5,
    1.0,
    0.1
)

cost_multiplier = st.sidebar.slider(
    "Transport Cost Shock",
    0.5,
    1.5,
    1.0,
    0.1
)

shipments["Scenario Shipment"] = shipments["Shipment"] * demand_multiplier
shipments["Adjusted Cost"] = shipments["Shipment"] * cost_multiplier

# -----------------------------
# Apply Filters
# -----------------------------

if plant_filter:
    shipments = shipments[shipments["Plant"].isin(plant_filter)]

if market_filter:
    shipments = shipments[shipments["Market"].isin(market_filter)]

shipments["Route"] = shipments["Plant"] + " → " + shipments["Market"]

# -----------------------------
# Top Shipment Routes
# -----------------------------

st.subheader("Top Shipment Routes")

top_routes = shipments.sort_values(
    "Scenario Shipment",
    ascending=False
).head(top_n)

fig_routes = px.bar(
    top_routes,
    x="Scenario Shipment",
    y="Route",
    orientation="h"
)

st.plotly_chart(fig_routes, use_container_width=True)

# -----------------------------
# Plant Distribution
# -----------------------------

st.subheader("Plant Shipment Distribution")

plant_summary = shipments.groupby("Plant")["Scenario Shipment"].sum().reset_index()

fig_plants = px.bar(
    plant_summary,
    x="Plant",
    y="Scenario Shipment"
)

st.plotly_chart(fig_plants, use_container_width=True)

# -----------------------------
# Market Concentration
# -----------------------------

st.subheader("Market Shipment Distribution")

market_summary = shipments.groupby("Market")["Scenario Shipment"].sum().reset_index()

fig_market = px.pie(
    market_summary,
    values="Scenario Shipment",
    names="Market"
)

st.plotly_chart(fig_market, use_container_width=True)

# -----------------------------
# Sankey Flow
# -----------------------------

st.subheader("Supply Chain Flow")

top_flow = shipments.sort_values(
    "Scenario Shipment",
    ascending=False
).head(top_n)

plants = top_flow["Plant"].unique().tolist()
markets = top_flow["Market"].unique().tolist()

labels = plants + markets

source = top_flow["Plant"].apply(lambda x: plants.index(x)).tolist()
target = top_flow["Market"].apply(lambda x: markets.index(x) + len(plants)).tolist()
value = top_flow["Scenario Shipment"].tolist()

fig_sankey = go.Figure(data=[go.Sankey(
    arrangement="snap",
    node=dict(
        pad=40,
        thickness=20,
        label=labels
    ),
    link=dict(
        source=source,
        target=target,
        value=value
    )
)])

fig_sankey.update_layout(height=600)

st.plotly_chart(fig_sankey, use_container_width=True)

# -----------------------------
# Geographic Supply Chain Map
# -----------------------------

st.subheader("Geographic Supply Chain Map")

# demo coordinates
plant_coords = {
"P001": (40,-74),
"P002": (34,-118),
"P003": (41,-87)
}

market_coords = {
"M001": (29,-95),
"M002": (39,-75),
"M003": (33,-84)
}

fig_map = go.Figure()

for _,row in shipments.iterrows():

    if row["Plant"] in plant_coords and row["Market"] in market_coords:

        p_lat,p_lon = plant_coords[row["Plant"]]
        m_lat,m_lon = market_coords[row["Market"]]

        fig_map.add_trace(
            go.Scattergeo(
                lat=[p_lat,m_lat],
                lon=[p_lon,m_lon],
                mode="lines",
                line=dict(width=1),
                opacity=0.6
            )
        )

fig_map.update_layout(
    geo=dict(
        scope="north america",
        showland=True
    )
)

st.plotly_chart(fig_map, use_container_width=True)

# -----------------------------
# Cost Sensitivity
# -----------------------------

st.subheader("Transport Cost Sensitivity")

cost_summary = shipments.groupby("Plant")["Adjusted Cost"].sum().reset_index()

fig_cost = px.bar(
    cost_summary,
    x="Plant",
    y="Adjusted Cost"
)

st.plotly_chart(fig_cost, use_container_width=True)

# -----------------------------
# Route Inspector
# -----------------------------

st.subheader("Route Inspector")

route = st.selectbox(
    "Select Route",
    shipments["Route"]
)

st.dataframe(
    shipments[shipments["Route"] == route]
)

# -----------------------------
# Operational Insights
# -----------------------------

st.subheader("Operational Insights")

largest_routes = shipments.sort_values(
    "Scenario Shipment",
    ascending=False
).head(5)

st.write("Largest Shipment Routes")

st.dataframe(
    largest_routes[["Plant","Market","Scenario Shipment"]]
)

plant_volume = shipments.groupby("Plant")["Scenario Shipment"].sum().sort_values(ascending=False)

st.write("Potential Bottleneck Plants")

st.dataframe(
    plant_volume.head(5)
)







