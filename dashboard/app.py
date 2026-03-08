import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Supply Chain Decision Engine",
    layout="wide"
)

# =========================================================
# Helpers
# =========================================================
@st.cache_data
def load_data():
    shipments = pd.read_csv("outputs/optimal_shipments.csv")
    summary = pd.read_csv("outputs/optimization_summary.csv")
    return shipments, summary


def safe_summary_value(summary_df, metric_name, fallback=None):
    if "Metric" in summary_df.columns and "Value" in summary_df.columns:
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


def generate_ai_insights(df, top_n=3):
    insights = []

    if df.empty:
        return ["No data available under the selected scenario and filters."]

    total_shipment = df["Scenario Shipment"].sum()

    plant_summary = (
        df.groupby("Plant", as_index=False)["Scenario Shipment"]
        .sum()
        .sort_values("Scenario Shipment", ascending=False)
    )

    market_summary = (
        df.groupby("Market", as_index=False)["Scenario Shipment"]
        .sum()
        .sort_values("Scenario Shipment", ascending=False)
    )

    route_summary = (
        df.groupby(["Plant", "Market"], as_index=False)["Scenario Shipment"]
        .sum()
        .sort_values("Scenario Shipment", ascending=False)
    )

    top_plants = plant_summary.head(top_n)
    top_plant_share = top_plants["Scenario Shipment"].sum() / total_shipment * 100
    insights.append(
        f"Top {top_n} plants contribute {top_plant_share:.1f}% of total shipment volume."
    )

    bottleneck_threshold = plant_summary["Scenario Shipment"].quantile(0.9)
    bottlenecks = plant_summary[plant_summary["Scenario Shipment"] >= bottleneck_threshold]
    if not bottlenecks.empty:
        bottleneck_names = ", ".join(bottlenecks["Plant"].astype(str).tolist()[:3])
        insights.append(
            f"Potential bottleneck risk is concentrated in {bottleneck_names}, based on scenario shipment concentration."
        )

    top_route = route_summary.iloc[0]
    insights.append(
        f"The highest-volume route is {top_route['Plant']} → {top_route['Market']}, carrying {top_route['Scenario Shipment']:,.0f} units."
    )

    top_market_share = market_summary.iloc[0]["Scenario Shipment"] / total_shipment * 100
    if top_market_share >= 20:
        concentration_text = "high"
    elif top_market_share >= 10:
        concentration_text = "moderate"
    else:
        concentration_text = "low"

    insights.append(
        f"Market concentration is {concentration_text}; the largest market accounts for {top_market_share:.1f}% of scenario shipment volume."
    )

    cost_by_plant = (
        df.groupby("Plant", as_index=False)["Scenario Transport Cost"]
        .sum()
        .sort_values("Scenario Transport Cost", ascending=False)
    )
    if not cost_by_plant.empty:
        expensive_plant = cost_by_plant.iloc[0]["Plant"]
        insights.append(
            f"{expensive_plant} has the highest scenario transport cost burden and should be monitored under cost inflation scenarios."
        )

    return insights


# =========================================================
# Load
# =========================================================
shipments, summary = load_data()

# Expecting columns like: Plant, Market, Shipment
required_cols = {"Plant", "Market", "Shipment"}
missing = required_cols - set(shipments.columns)
if missing:
    st.error(f"Missing required columns in outputs/optimal_shipments.csv: {sorted(missing)}")
    st.stop()

# =========================================================
# Header
# =========================================================
st.title("Supply Chain Decision Engine")
st.caption("Interactive supply chain analytics dashboard with scenario simulation and AI-style business insights.")

# =========================================================
# Sidebar controls
# =========================================================
st.sidebar.header("Scenario Controls")

demand_multiplier = st.sidebar.slider(
    "Demand Shock",
    min_value=0.50,
    max_value=1.50,
    value=1.00,
    step=0.05,
    help="Simulates higher or lower demand across routes."
)

transport_cost_multiplier = st.sidebar.slider(
    "Transport Cost Shock",
    min_value=0.50,
    max_value=1.50,
    value=1.00,
    step=0.05,
    help="Simulates changes in transport cost intensity."
)

unit_revenue = st.sidebar.number_input(
    "Revenue per Shipment Unit",
    min_value=1.0,
    value=120.0,
    step=5.0
)

unit_transport_cost = st.sidebar.number_input(
    "Base Transport Cost per Shipment Unit",
    min_value=1.0,
    value=35.0,
    step=1.0
)

st.sidebar.header("Filters")

plant_filter = st.sidebar.multiselect(
    "Focus Plants",
    options=sorted(shipments["Plant"].dropna().unique().tolist())
)

market_filter = st.sidebar.multiselect(
    "Focus Markets",
    options=sorted(shipments["Market"].dropna().unique().tolist())
)

top_n = st.sidebar.slider(
    "Top Routes to Display",
    min_value=5,
    max_value=100,
    value=20,
    step=5
)

# =========================================================
# Scenario transformation
# =========================================================
df = shipments.copy()

if plant_filter:
    df = df[df["Plant"].isin(plant_filter)]

if market_filter:
    df = df[df["Market"].isin(market_filter)]

df["Route"] = df["Plant"].astype(str) + " → " + df["Market"].astype(str)
df["Scenario Shipment"] = df["Shipment"] * demand_multiplier
df["Scenario Revenue"] = df["Scenario Shipment"] * unit_revenue
df["Scenario Transport Cost"] = df["Scenario Shipment"] * unit_transport_cost * transport_cost_multiplier
df["Scenario Profit Proxy"] = df["Scenario Revenue"] - df["Scenario Transport Cost"]

if df.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

# =========================================================
# KPI block
# =========================================================
original_profit = safe_summary_value(summary, "Total Profit", fallback=None)
active_lanes = safe_summary_value(summary, "Number of Active Lanes", fallback=len(df))

scenario_total_shipment = df["Scenario Shipment"].sum()
scenario_total_revenue = df["Scenario Revenue"].sum()
scenario_total_cost = df["Scenario Transport Cost"].sum()
scenario_profit_proxy = df["Scenario Profit Proxy"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Scenario Shipment Volume", f"{scenario_total_shipment:,.0f}")
k2.metric("Scenario Revenue", f"${scenario_total_revenue:,.0f}")
k3.metric("Scenario Transport Cost", f"${scenario_total_cost:,.0f}")
k4.metric("Scenario Profit Proxy", f"${scenario_profit_proxy:,.0f}")

k5, k6 = st.columns(2)
k5.metric("Active Shipment Lanes", f"{int(active_lanes):,}")
if original_profit is not None:
    try:
        original_profit_num = float(original_profit)
        delta = scenario_profit_proxy - original_profit_num
        k6.metric("Base Model Profit", f"${original_profit_num:,.0f}", delta=f"{delta:,.0f}")
    except Exception:
        k6.metric("Base Model Profit", str(original_profit))
else:
    k6.metric("Base Model Profit", "Not available")

st.divider()

# =========================================================
# AI insights
# =========================================================
st.subheader("AI-Generated Operational Insights")
insights = generate_ai_insights(df, top_n=3)
for i, text in enumerate(insights, start=1):
    st.markdown(f"**{i}.** {text}")

st.divider()

# =========================================================
# Tabs
# =========================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Executive Overview",
    "Route Explorer",
    "Flow & Network",
    "Geographic Map",
    "Data Drilldown"
])

# =========================================================
# Tab 1 - Executive Overview
# =========================================================
with tab1:
    left, right = st.columns(2)

    with left:
        st.subheader("Top Shipment Routes")
        top_routes = (
            df.sort_values("Scenario Shipment", ascending=False)
            .head(top_n)
        )
        fig_routes = px.bar(
            top_routes,
            x="Scenario Shipment",
            y="Route",
            orientation="h",
            title="Highest-Volume Routes"
        )
        fig_routes.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_routes, use_container_width=True)

    with right:
        st.subheader("Plant Shipment Distribution")
        plant_summary = (
            df.groupby("Plant", as_index=False)["Scenario Shipment"]
            .sum()
            .sort_values("Scenario Shipment", ascending=False)
        )
        fig_plants = px.bar(
            plant_summary,
            x="Plant",
            y="Scenario Shipment",
            title="Scenario Shipment by Plant"
        )
        st.plotly_chart(fig_plants, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Market Concentration")
        market_summary = (
            df.groupby("Market", as_index=False)["Scenario Shipment"]
            .sum()
            .sort_values("Scenario Shipment", ascending=False)
        )
        fig_market = px.pie(
            market_summary,
            values="Scenario Shipment",
            names="Market",
            title="Shipment Distribution by Market"
        )
        st.plotly_chart(fig_market, use_container_width=True)

    with c2:
        st.subheader("Transport Cost Sensitivity")
        cost_summary = (
            df.groupby("Plant", as_index=False)["Scenario Transport Cost"]
            .sum()
            .sort_values("Scenario Transport Cost", ascending=False)
        )
        fig_cost = px.bar(
            cost_summary,
            x="Plant",
            y="Scenario Transport Cost",
            title="Scenario Transport Cost by Plant"
        )
        st.plotly_chart(fig_cost, use_container_width=True)

# =========================================================
# Tab 2 - Route Explorer
# =========================================================
with tab2:
    st.subheader("Route Explorer")

    route_options = df["Route"].drop_duplicates().sort_values().tolist()
    selected_route = st.selectbox("Select a Route", route_options)

    route_df = df[df["Route"] == selected_route].copy()

    a, b, c = st.columns(3)
    a.metric("Route Scenario Shipment", f"{route_df['Scenario Shipment'].sum():,.0f}")
    b.metric("Route Scenario Revenue", f"${route_df['Scenario Revenue'].sum():,.0f}")
    c.metric("Route Scenario Cost", f"${route_df['Scenario Transport Cost'].sum():,.0f}")

    st.dataframe(route_df, use_container_width=True)

# =========================================================
# Tab 3 - Flow & Network
# =========================================================
with tab3:
    st.subheader("Supply Chain Flow")

    top_flow = (
        df.sort_values("Scenario Shipment", ascending=False)
        .head(top_n)
        .copy()
    )

    plants = top_flow["Plant"].unique().tolist()
    markets = top_flow["Market"].unique().tolist()
    labels = plants + markets

    source = top_flow["Plant"].apply(lambda x: plants.index(x)).tolist()
    target = top_flow["Market"].apply(lambda x: markets.index(x) + len(plants)).tolist()
    values = top_flow["Scenario Shipment"].tolist()

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
            value=values
        )
    )])
    fig_sankey.update_layout(height=650, title="Plant-to-Market Flow")
    st.plotly_chart(fig_sankey, use_container_width=True)

    st.subheader("Network Optimization Simulator")
    network_summary = (
        df.groupby("Plant", as_index=False)
        .agg(
            Scenario_Shipment=("Scenario Shipment", "sum"),
            Scenario_Cost=("Scenario Transport Cost", "sum"),
            Scenario_Profit=("Scenario Profit Proxy", "sum")
        )
        .sort_values("Scenario_Profit", ascending=False)
    )
    st.dataframe(network_summary, use_container_width=True)

# =========================================================
# Tab 4 - Geographic Map
# =========================================================
with tab4:
    st.subheader("Geographic Supply Chain Map")

    # Demo coordinates generated from plant / market IDs
    plant_coords = build_coords(df["Plant"].unique(), lat_base=30, lon_base=-125)
    market_coords = build_coords(df["Market"].unique(), lat_base=28, lon_base=-95)

    fig_map = go.Figure()

    # draw routes
    for _, row in df.sort_values("Scenario Shipment", ascending=False).head(top_n).iterrows():
        p_lat, p_lon = plant_coords[row["Plant"]]
        m_lat, m_lon = market_coords[row["Market"]]

        fig_map.add_trace(
            go.Scattergeo(
                lat=[p_lat, m_lat],
                lon=[p_lon, m_lon],
                mode="lines",
                line=dict(width=1 + row["Scenario Shipment"] / df["Scenario Shipment"].max() * 4),
                opacity=0.55,
                hovertemplate=(
                    f"Route: {row['Plant']} → {row['Market']}<br>"
                    f"Scenario Shipment: {row['Scenario Shipment']:,.0f}<extra></extra>"
                )
            )
        )

    # plant markers
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

    # market markers
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
            countrycolor="rgb(204,204,204)",
        ),
        height=700
    )
    st.plotly_chart(fig_map, use_container_width=True)

# =========================================================
# Tab 5 - Data Drilldown
# =========================================================
with tab5:
    st.subheader("Plant Bottleneck View")
    bottleneck_df = (
        df.groupby("Plant", as_index=False)["Scenario Shipment"]
        .sum()
        .sort_values("Scenario Shipment", ascending=False)
    )
    threshold = bottleneck_df["Scenario Shipment"].quantile(0.9)
    bottleneck_df["Bottleneck Risk"] = bottleneck_df["Scenario Shipment"].apply(
        lambda x: "High" if x >= threshold else "Normal"
    )
    st.dataframe(bottleneck_df, use_container_width=True)

    st.subheader("Detailed Scenario Data")
    st.dataframe(df, use_container_width=True)

 













