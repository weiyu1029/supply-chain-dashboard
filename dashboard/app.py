import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Supply Chain Decision Engine",
    layout="wide"
)

# =========================================================
# Data loading
# =========================================================
@st.cache_data
def load_data():
    shipments = pd.read_csv("outputs/optimal_shipments.csv")
    summary = pd.read_csv("outputs/optimization_summary.csv")
    return shipments, summary


def safe_summary_value(summary_df, metric_name, fallback=None):
    if {"Metric", "Value"}.issubset(summary_df.columns):
        match = summary_df.loc[summary_df["Metric"] == metric_name, "Value"]
        if len(match) > 0:
            return match.values[0]
    return fallback


def build_coords(labels, lat_base, lon_base, lat_step=2.0, lon_step=2.5):
    coords = {}
    for i, label in enumerate(sorted(labels)):
        coords[label] = (
            lat_base + (i % 10) * lat_step,
            lon_base + (i // 10) * lon_step
        )
    return coords


shipments, summary = load_data()

required_cols = {"Plant", "Market", "Shipment"}
missing = required_cols - set(shipments.columns)
if missing:
    st.error(f"Missing required columns in outputs/optimal_shipments.csv: {sorted(missing)}")
    st.stop()

# =========================================================
# Sidebar
# =========================================================
st.sidebar.title("Network Scenario Simulator")

demand_multiplier = st.sidebar.slider(
    "Demand Shock",
    min_value=0.50,
    max_value=1.50,
    value=1.00,
    step=0.05
)

transport_cost_multiplier = st.sidebar.slider(
    "Transport Cost Shock",
    min_value=0.50,
    max_value=1.50,
    value=1.00,
    step=0.05
)

unit_revenue = st.sidebar.number_input(
    "Revenue per Shipment Unit",
    min_value=1.0,
    value=90.0,
    step=5.0
)

base_cost_per_unit = st.sidebar.number_input(
    "Base Transport Cost per Shipment Unit",
    min_value=1.0,
    value=35.0,
    step=1.0
)

st.sidebar.subheader("Filters")

plant_filter = st.sidebar.multiselect(
    "Focus Plants",
    sorted(shipments["Plant"].dropna().unique().tolist())
)

market_filter = st.sidebar.multiselect(
    "Focus Markets",
    sorted(shipments["Market"].dropna().unique().tolist())
)

top_n = st.sidebar.slider(
    "Top Routes to Display",
    min_value=5,
    max_value=100,
    value=20,
    step=5
)

# =========================================================
# Baseline and scenario dataset
# =========================================================
base_df = shipments.copy()

if plant_filter:
    base_df = base_df[base_df["Plant"].isin(plant_filter)]

if market_filter:
    base_df = base_df[base_df["Market"].isin(market_filter)]

if base_df.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

base_df["Route"] = base_df["Plant"].astype(str) + " → " + base_df["Market"].astype(str)
base_df["Base Shipment"] = base_df["Shipment"]
base_df["Base Revenue"] = base_df["Base Shipment"] * unit_revenue
base_df["Base Cost"] = base_df["Base Shipment"] * base_cost_per_unit
base_df["Base Profit"] = base_df["Base Revenue"] - base_df["Base Cost"]

df = base_df.copy()
df["Scenario Shipment"] = df["Base Shipment"] * demand_multiplier
df["Scenario Revenue"] = df["Scenario Shipment"] * unit_revenue
df["Scenario Cost"] = df["Scenario Shipment"] * base_cost_per_unit * transport_cost_multiplier
df["Scenario Profit"] = df["Scenario Revenue"] - df["Scenario Cost"]

# =========================================================
# KPI calculations
# =========================================================
base_total_shipment = df["Base Shipment"].sum()
base_total_revenue = df["Base Revenue"].sum()
base_total_cost = df["Base Cost"].sum()
base_total_profit = df["Base Profit"].sum()

scenario_total_shipment = df["Scenario Shipment"].sum()
scenario_total_revenue = df["Scenario Revenue"].sum()
scenario_total_cost = df["Scenario Cost"].sum()
scenario_total_profit = df["Scenario Profit"].sum()

active_lanes = len(df)

# =========================================================
# Aggregations
# =========================================================
plant_summary = (
    df.groupby("Plant", as_index=False)
    .agg(
        Base_Shipment=("Base Shipment", "sum"),
        Scenario_Shipment=("Scenario Shipment", "sum"),
        Scenario_Cost=("Scenario Cost", "sum"),
        Scenario_Profit=("Scenario Profit", "sum")
    )
    .sort_values("Scenario_Shipment", ascending=False)
)

market_summary = (
    df.groupby("Market", as_index=False)
    .agg(
        Scenario_Shipment=("Scenario Shipment", "sum"),
        Scenario_Cost=("Scenario Cost", "sum"),
        Scenario_Profit=("Scenario Profit", "sum")
    )
    .sort_values("Scenario_Shipment", ascending=False)
)

route_summary = (
    df.groupby(["Plant", "Market", "Route"], as_index=False)
    .agg(
        Base_Shipment=("Base Shipment", "sum"),
        Scenario_Shipment=("Scenario Shipment", "sum"),
        Scenario_Cost=("Scenario Cost", "sum"),
        Scenario_Profit=("Scenario Profit", "sum")
    )
    .sort_values("Scenario_Shipment", ascending=False)
)

plant_summary["Shipment Share %"] = plant_summary["Scenario_Shipment"] / scenario_total_shipment * 100
market_summary["Shipment Share %"] = market_summary["Scenario_Shipment"] / scenario_total_shipment * 100
route_summary["Shipment Share %"] = route_summary["Scenario_Shipment"] / scenario_total_shipment * 100

if scenario_total_cost != 0:
    plant_summary["Cost Share %"] = plant_summary["Scenario_Cost"] / scenario_total_cost * 100
    route_summary["Cost Share %"] = route_summary["Scenario_Cost"] / scenario_total_cost * 100
else:
    plant_summary["Cost Share %"] = 0
    route_summary["Cost Share %"] = 0

plant_summary["Utilization Proxy"] = plant_summary["Scenario_Shipment"] / plant_summary["Scenario_Shipment"].max()
plant_summary["Risk Score"] = plant_summary["Shipment Share %"] * plant_summary["Cost Share %"] / 100

plant_summary["Risk Level"] = pd.cut(
    plant_summary["Utilization Proxy"],
    bins=[0, 0.6, 0.85, 1.0],
    labels=["Low", "Medium", "High"],
    include_lowest=True
)

# =========================================================
# Concentration metrics
# =========================================================
top3_plants_share = plant_summary.head(3)["Scenario_Shipment"].sum() / scenario_total_shipment * 100
top3_markets_share = market_summary.head(3)["Scenario_Shipment"].sum() / scenario_total_shipment * 100
top5_routes_share = route_summary.head(5)["Scenario_Shipment"].sum() / scenario_total_shipment * 100

top_route = route_summary.iloc[0]
top_plant = plant_summary.iloc[0]
top_market = market_summary.iloc[0]

profit_change_pct = ((scenario_total_profit - base_total_profit) / base_total_profit * 100) if base_total_profit != 0 else 0
cost_change_pct = ((scenario_total_cost - base_total_cost) / base_total_cost * 100) if base_total_cost != 0 else 0

# =========================================================
# Title
# =========================================================
st.title("Supply Chain Decision Engine")
st.caption("Interactive supply chain analytics dashboard for scenario simulation, network diagnostics, and operational decision support.")

# =========================================================
# Executive summary
# =========================================================
summary_text = f"""
**Executive Summary**

Under the current scenario, the network delivers **{scenario_total_shipment:,.0f} units**
with an estimated profit of **${scenario_total_profit:,.0f}**.

The network remains most dependent on **plant {top_plant['Plant']}** and **market {top_market['Market']}**,
while **{top_route['Route']}** is the highest-volume route in the system.

Profit changes by **{profit_change_pct:.1f}%** versus baseline, while transport cost changes by **{cost_change_pct:.1f}%**.
Current concentration levels suggest that resilience should be monitored if demand continues to rise.
"""
st.info(summary_text)

# =========================================================
# KPI row
# =========================================================
k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Scenario Shipment Volume",
    f"{scenario_total_shipment:,.0f}",
    delta=f"{scenario_total_shipment - base_total_shipment:,.0f}"
)
k2.metric(
    "Scenario Revenue",
    f"${scenario_total_revenue:,.0f}",
    delta=f"{scenario_total_revenue - base_total_revenue:,.0f}"
)
k3.metric(
    "Scenario Transport Cost",
    f"${scenario_total_cost:,.0f}",
    delta=f"{scenario_total_cost - base_total_cost:,.0f}"
)
k4.metric(
    "Scenario Profit",
    f"${scenario_total_profit:,.0f}",
    delta=f"{scenario_total_profit - base_total_profit:,.0f}"
)

# =========================================================
# Resilience cards
# =========================================================
r1, r2, r3 = st.columns(3)
r1.metric("Top 3 Plant Share", f"{top3_plants_share:.1f}%")
r2.metric("Top 3 Market Share", f"{top3_markets_share:.1f}%")
r3.metric("Top 5 Route Share", f"{top5_routes_share:.1f}%")

# =========================================================
# Scenario comparison
# =========================================================
st.subheader("Scenario Comparison")

comparison_df = pd.DataFrame({
    "Metric": ["Shipment Volume", "Revenue", "Transport Cost", "Profit"],
    "Baseline": [
        base_total_shipment,
        base_total_revenue,
        base_total_cost,
        base_total_profit
    ],
    "Scenario": [
        scenario_total_shipment,
        scenario_total_revenue,
        scenario_total_cost,
        scenario_total_profit
    ]
})

comparison_df["Change"] = comparison_df["Scenario"] - comparison_df["Baseline"]
comparison_df["Change %"] = comparison_df["Change"] / comparison_df["Baseline"].replace(0, 1)

display_comparison = comparison_df.copy()
display_comparison["Baseline"] = display_comparison.apply(
    lambda row: f"${row['Baseline']:,.0f}" if row["Metric"] != "Shipment Volume" else f"{row['Baseline']:,.0f}",
    axis=1
)
display_comparison["Scenario"] = display_comparison.apply(
    lambda row: f"${row['Scenario']:,.0f}" if row["Metric"] != "Shipment Volume" else f"{row['Scenario']:,.0f}",
    axis=1
)
display_comparison["Change"] = display_comparison.apply(
    lambda row: f"${row['Change']:,.0f}" if row["Metric"] != "Shipment Volume" else f"{row['Change']:,.0f}",
    axis=1
)
display_comparison["Change %"] = display_comparison["Change %"].map(lambda x: f"{x:.1%}")

st.dataframe(display_comparison, use_container_width=True)

# =========================================================
# Baseline vs Scenario chart
# =========================================================
comparison_chart_df = comparison_df.copy()

fig_compare = px.bar(
    comparison_chart_df.melt(
        id_vars="Metric",
        value_vars=["Baseline", "Scenario"],
        var_name="Version",
        value_name="Value"
    ),
    x="Metric",
    y="Value",
    color="Version",
    barmode="group",
    title="Baseline vs Scenario Comparison"
)

st.plotly_chart(fig_compare, use_container_width=True)

# =========================================================
# Waterfall chart
# =========================================================
waterfall_labels = ["Baseline Profit", "Revenue Change", "Cost Change", "Scenario Profit"]
revenue_delta = scenario_total_revenue - base_total_revenue
cost_delta = scenario_total_cost - base_total_cost

fig_waterfall = go.Figure(go.Waterfall(
    name="Profit Bridge",
    orientation="v",
    measure=["absolute", "relative", "relative", "total"],
    x=waterfall_labels,
    y=[base_total_profit, revenue_delta, -cost_delta, scenario_total_profit],
    connector={"line": {"color": "rgb(63, 63, 63)"}}
))

fig_waterfall.update_layout(
    title="Scenario Profit Bridge",
    showlegend=False
)

st.plotly_chart(fig_waterfall, use_container_width=True)

st.divider()

# =========================================================
# Network diagnostics
# =========================================================
st.subheader("Network Diagnostics")

diag1, diag2 = st.columns(2)

with diag1:
    st.markdown("**Capacity Risk**")
    st.write(
        f"- Plant **{top_plant['Plant']}** carries **{top_plant['Shipment Share %']:.1f}%** of scenario shipment volume, the highest in the network."
    )
    st.write(
        f"- Top 3 plants account for **{top3_plants_share:.1f}%** of total shipment volume."
    )

    high_risk_plants = plant_summary.loc[plant_summary["Risk Level"] == "High", "Plant"].head(5).tolist()
    if high_risk_plants:
        st.write(
            "- Plants classified as **High** risk under current utilization proxy: "
            + ", ".join(high_risk_plants)
        )
    else:
        st.write("- No plants are currently classified as **High** risk.")

    st.markdown("**Concentration Risk**")
    st.write(
        f"- Top 3 markets account for **{top3_markets_share:.1f}%** of scenario shipment volume."
    )
    st.write(
        f"- The largest market is **{top_market['Market']}**, representing **{top_market['Shipment Share %']:.1f}%** of network volume."
    )

with diag2:
    st.markdown("**Cost Exposure**")
    st.write(
        f"- Route **{top_route['Route']}** is the highest-volume lane, carrying **{top_route['Scenario_Shipment']:,.0f} units**."
    )
    st.write(
        f"- This route also contributes **{top_route['Cost Share %']:.1f}%** of total scenario transport cost."
    )
    st.write(
        f"- Top 5 routes account for **{top5_routes_share:.1f}%** of network shipment volume."
    )

    st.markdown("**Scenario Interpretation**")
    if comparison_df.loc[comparison_df["Metric"] == "Profit", "Change"].iloc[0] > 0:
        st.write("- Network profitability improves under the current scenario.")
    else:
        st.write("- Network profitability weakens under the current scenario.")

    if comparison_df.loc[comparison_df["Metric"] == "Transport Cost", "Change %"].iloc[0] > comparison_df.loc[comparison_df["Metric"] == "Revenue", "Change %"].iloc[0]:
        st.write("- Cost pressure is rising faster than revenue growth.")
    else:
        st.write("- Revenue growth remains ahead of cost inflation.")

st.divider()

# =========================================================
# Top risks / opportunities
# =========================================================
st.subheader("Top Risks and Opportunities")

risk_col, opp_col = st.columns(2)

with risk_col:
    st.markdown("**Top Risks**")
    top_risks = plant_summary.sort_values("Risk Score", ascending=False).head(5)[
        ["Plant", "Scenario_Shipment", "Scenario_Cost", "Risk Score", "Risk Level"]
    ]
    st.dataframe(top_risks, use_container_width=True)

with opp_col:
    st.markdown("**Top Opportunities**")
    top_opportunities = route_summary.sort_values("Scenario_Profit", ascending=False).head(5)[
        ["Route", "Scenario_Shipment", "Scenario_Cost", "Scenario_Profit"]
    ]
    st.dataframe(top_opportunities, use_container_width=True)

st.divider()

# =========================================================
# Tabs
# =========================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Executive Overview",
    "Critical Routes",
    "Route Explorer",
    "Flow & Network",
    "Geographic Map",
    "Data Drilldown"
])

# =========================================================
# Executive Overview
# =========================================================
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        fig_plant_ship = px.bar(
            plant_summary.sort_values("Scenario_Shipment", ascending=False),
            x="Plant",
            y="Scenario_Shipment",
            color="Risk Level",
            title="Plant Shipment Distribution and Risk Level"
        )
        st.plotly_chart(fig_plant_ship, use_container_width=True)

    with c2:
        fig_market_share = px.pie(
            market_summary,
            values="Scenario_Shipment",
            names="Market",
            title="Market Shipment Distribution"
        )
        st.plotly_chart(fig_market_share, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        fig_cost = px.bar(
            plant_summary.sort_values("Scenario_Cost", ascending=False),
            x="Plant",
            y="Scenario_Cost",
            title="Transport Cost Sensitivity by Plant"
        )
        st.plotly_chart(fig_cost, use_container_width=True)

    with c4:
        fig_profit = px.bar(
            route_summary.sort_values("Scenario_Profit", ascending=False).head(15),
            x="Scenario_Profit",
            y="Route",
            orientation="h",
            title="Highest Profit Routes"
        )
        fig_profit.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_profit, use_container_width=True)

    concentration_df = pd.DataFrame({
        "Metric": ["Top 3 Plant Share", "Top 3 Market Share", "Top 5 Route Share"],
        "Value": [top3_plants_share, top3_markets_share, top5_routes_share]
    })

    fig_concentration = px.bar(
        concentration_df,
        x="Metric",
        y="Value",
        title="Network Concentration Indicators",
        text="Value"
    )
    fig_concentration.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig_concentration, use_container_width=True)

# =========================================================
# Critical Routes
# =========================================================
with tab2:
    st.subheader("Critical Routes")

    critical_routes = route_summary.copy()
    critical_routes["Profit Margin %"] = critical_routes["Scenario_Profit"] / critical_routes["Scenario_Shipment"].replace(0, 1)
    critical_routes["Shipment Change %"] = (
        (critical_routes["Scenario_Shipment"] - critical_routes["Base_Shipment"])
        / critical_routes["Base_Shipment"].replace(0, 1)
    )

    display_routes = critical_routes.head(top_n)[[
        "Route",
        "Base_Shipment",
        "Scenario_Shipment",
        "Shipment Change %",
        "Scenario_Cost",
        "Scenario_Profit",
        "Profit Margin %",
        "Shipment Share %",
        "Cost Share %"
    ]].copy()

    display_routes["Shipment Change %"] = display_routes["Shipment Change %"].map(lambda x: f"{x:.1%}")
    display_routes["Profit Margin %"] = display_routes["Profit Margin %"].map(lambda x: f"{x:.2f}")
    display_routes["Shipment Share %"] = display_routes["Shipment Share %"].map(lambda x: f"{x:.1f}%")
    display_routes["Cost Share %"] = display_routes["Cost Share %"].map(lambda x: f"{x:.1f}%")

    st.dataframe(display_routes, use_container_width=True)

# =========================================================
# Route Explorer
# =========================================================
with tab3:
    st.subheader("Route Explorer")

    route_options = df["Route"].drop_duplicates().sort_values().tolist()
    selected_route = st.selectbox("Select a Route", route_options)

    route_df = df[df["Route"] == selected_route].copy()

    route_k1, route_k2, route_k3, route_k4 = st.columns(4)
    route_k1.metric("Base Shipment", f"{route_df['Base Shipment'].sum():,.0f}")
    route_k2.metric("Scenario Shipment", f"{route_df['Scenario Shipment'].sum():,.0f}")
    route_k3.metric("Scenario Cost", f"${route_df['Scenario Cost'].sum():,.0f}")
    route_k4.metric("Scenario Profit", f"${route_df['Scenario Profit'].sum():,.0f}")

    route_detail = (
        route_df.groupby(["Plant", "Market", "Route"], as_index=False)
        .agg(
            Base_Shipment=("Base Shipment", "sum"),
            Scenario_Shipment=("Scenario Shipment", "sum"),
            Scenario_Cost=("Scenario Cost", "sum"),
            Scenario_Profit=("Scenario Profit", "sum")
        )
    )

    route_detail["Profit Margin %"] = route_detail["Scenario_Profit"] / route_detail["Scenario_Shipment"].replace(0, 1)
    route_detail["Shipment Share %"] = route_detail["Scenario_Shipment"] / scenario_total_shipment * 100

    st.dataframe(route_detail, use_container_width=True)

# =========================================================
# Flow & Network
# =========================================================
with tab4:
    st.subheader("Supply Chain Flow")

    top_flow = route_summary.head(top_n).copy()

    plants = top_flow["Plant"].unique().tolist()
    markets = top_flow["Market"].unique().tolist()
    labels = plants + markets

    source = top_flow["Plant"].apply(lambda x: plants.index(x)).tolist()
    target = top_flow["Market"].apply(lambda x: markets.index(x) + len(plants)).tolist()
    values = top_flow["Scenario_Shipment"].tolist()

    hover_text = [
        f"Route: {r}<br>Shipment: {s:,.0f}<br>Cost: ${c:,.0f}<br>Profit: ${p:,.0f}"
        for r, s, c, p in zip(
            top_flow["Route"],
            top_flow["Scenario_Shipment"],
            top_flow["Scenario_Cost"],
            top_flow["Scenario_Profit"]
        )
    ]

    fig_sankey = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=40,
            thickness=18,
            label=labels
        ),
        link=dict(
            source=source,
            target=target,
            value=values,
            customdata=hover_text,
            hovertemplate="%{customdata}<extra></extra>"
        )
    )])

    fig_sankey.update_layout(height=650, title="Plant-to-Market Flow")
    st.plotly_chart(fig_sankey, use_container_width=True)

    st.subheader("Network Optimization Simulator")
    simulator_table = plant_summary[[
        "Plant",
        "Scenario_Shipment",
        "Scenario_Cost",
        "Scenario_Profit",
        "Risk Score",
        "Risk Level"
    ]].copy()
    st.dataframe(simulator_table, use_container_width=True)

# =========================================================
# Geographic Map
# =========================================================
with tab5:
    st.subheader("Geographic Supply Chain Map")

    plant_coords = build_coords(df["Plant"].unique(), lat_base=30, lon_base=-125)
    market_coords = build_coords(df["Market"].unique(), lat_base=28, lon_base=-95)

    fig_map = go.Figure()

    top_map_routes = route_summary.head(top_n).copy()

    for _, row in top_map_routes.iterrows():
        p_lat, p_lon = plant_coords[row["Plant"]]
        m_lat, m_lon = market_coords[row["Market"]]

        fig_map.add_trace(
            go.Scattergeo(
                lat=[p_lat, m_lat],
                lon=[p_lon, m_lon],
                mode="lines",
                line=dict(
                    width=1 + row["Scenario_Shipment"] / top_map_routes["Scenario_Shipment"].max() * 4
                ),
                opacity=0.55,
                hovertemplate=(
                    f"Route: {row['Route']}<br>"
                    f"Shipment: {row['Scenario_Shipment']:,.0f}<br>"
                    f"Cost: ${row['Scenario_Cost']:,.0f}<br>"
                    f"Profit: ${row['Scenario_Profit']:,.0f}<extra></extra>"
                )
            )
        )

    fig_map.add_trace(
        go.Scattergeo(
            lat=[v[0] for v in plant_coords.values()],
            lon=[v[1] for v in plant_coords.values()],
            text=list(plant_coords.keys()),
            mode="markers+text",
            textposition="top center",
            marker=dict(size=8, symbol="square"),
            name="Plants"
        )
    )

    fig_map.add_trace(
        go.Scattergeo(
            lat=[v[0] for v in market_coords.values()],
            lon=[v[1] for v in market_coords.values()],
            text=list(market_coords.keys()),
            mode="markers+text",
            textposition="top center",
            marker=dict(size=8, symbol="circle"),
            name="Markets"
        )
    )

    fig_map.update_layout(
        geo=dict(
            scope="north america",
            showland=True,
            landcolor="rgb(243,243,243)",
            countrycolor="rgb(204,204,204)"
        ),
        height=700
    )
    st.plotly_chart(fig_map, use_container_width=True)

# =========================================================
# Data Drilldown
# =========================================================
with tab6:
    st.subheader("Capacity Stress")

    bottleneck_df = plant_summary[[
        "Plant",
        "Scenario_Shipment",
        "Shipment Share %",
        "Scenario_Cost",
        "Risk Score",
        "Risk Level"
    ]].copy()
    st.dataframe(bottleneck_df, use_container_width=True)

    st.subheader("Detailed Scenario Data")
    st.dataframe(df, use_container_width=True)

# =========================================================
# Download
# =========================================================
st.download_button(
    "Download Scenario Results",
    df.to_csv(index=False),
    file_name="scenario_results.csv",
    mime="text/csv"
)
