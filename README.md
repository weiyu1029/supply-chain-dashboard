# Supply Chain Optimization Project

This project builds a supply chain optimization model using linear programming to determine the most profitable shipment plan across a network of plants and markets.

## Project Overview

This project demonstrates how optimization and analytics can support supply chain decision-making.

Workflow includes:

- Data preprocessing
- Linear programming optimization
- Scenario simulation
- Visualization
- Interactive dashboard

## Visualization

### Supply Chain Network Graph

<img src="outputs/charts/supply_chain_network_graph.png" width="700">

### Top Shipment Lanes

<img src="outputs/charts/top_15_shipment_lanes.png" width="700">

### Plant Utilization

<img src="outputs/charts/top_15_plant_utilization.png" width="700">

### Scenario Profit Comparison

<img src="outputs/charts/scenario_profit_comparison.png" width="700">

## Run the Project

python src/preprocess.py  
python src/optimization_model.py  
python src/scenario_simulation.py  
python src/visualize_results.py  
python src/network_graph.py  

Launch dashboard:

streamlit run dashboard/app.py
