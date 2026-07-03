"""
Module 5 – Reporting and Visualization

This module:
- Compares baseline vs. scenario flows
- Calculates impact metrics:
  - Average detour distance
  - Trips affected
  - Critical bottleneck links
  - Diversion corridors
- Exports summary CSV
- Exports comparison GeoPackages for QGIS

Output files:
- Scenario_Performance_Matrix.csv: Summary metrics for all scenarios
- DiversionRoutes.gpkg: Roads with significant flow changes
- RouteComparison.gpkg: Baseline vs. scenario comparison
"""

import geopandas as gpd
import pandas as pd
import networkx as nx
import logging
import sys
import os
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OUTPUT_DIR, NETWORK_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_scenario_flows(scenario_num):
    """Load assigned flows for a scenario."""
    flow_file = os.path.join(OUTPUT_DIR, f"AssignedFlows_Scenario_{scenario_num}.geojson")
    
    if not os.path.exists(flow_file):
        logger.warning(f"Flow file not found: {flow_file}")
        return None
    
    try:
        flows = gpd.read_file(flow_file)
        return flows
    except Exception as e:
        logger.error(f"Error loading flows: {e}")
        return None


def calculate_flow_changes(baseline_flows, scenario_flows):
    """
    Calculate flow changes between baseline and scenario.
    
    Args:
        baseline_flows: GeoDataFrame with baseline flows
        scenario_flows: GeoDataFrame with scenario flows
    
    Returns:
        GeoDataFrame with flow deltas
    """
    logger.info("Calculating flow changes...")
    
    # Create edge lookup dictionaries
    baseline_dict = {}
    scenario_dict = {}
    
    if baseline_flows is not None:
        for idx, row in baseline_flows.iterrows():
            edge_key = (row["from_node"], row["to_node"])
            baseline_dict[edge_key] = row.get("flow", 0)
    
    for idx, row in scenario_flows.iterrows():
        edge_key = (row["from_node"], row["to_node"])
        scenario_dict[edge_key] = row.get("flow", 0)
    
    # Calculate deltas
    all_edges = set(baseline_dict.keys()) | set(scenario_dict.keys())
    
    changes = []
    for edge in all_edges:
        baseline_flow = baseline_dict.get(edge, 0)
        scenario_flow = scenario_dict.get(edge, 0)
        change = scenario_flow - baseline_flow
        pct_change = (change / baseline_flow * 100) if baseline_flow > 0 else 0
        
        if abs(change) > 0:  # Only record edges with changes
            changes.append({
                "from_node": edge[0],
                "to_node": edge[1],
                "baseline_flow": baseline_flow,
                "scenario_flow": scenario_flow,
                "flow_change": change,
                "pct_change": pct_change
            })
    
    changes_df = pd.DataFrame(changes)
    logger.info(f"  Found {len(changes_df)} edges with flow changes")
    
    return changes_df


def calculate_scenario_metrics(baseline_flows, scenario_flows, scenario_name):
    """
    Calculate summary metrics for a scenario.
    
    Args:
        baseline_flows: GeoDataFrame with baseline flows
        scenario_flows: GeoDataFrame with scenario flows
        scenario_name: Name of scenario
    
    Returns:
        Dictionary with metrics
    """
    logger.info(f"Calculating metrics for {scenario_name}...")
    
    baseline_total = baseline_flows["flow"].sum() if baseline_flows is not None else 0
    scenario_total = scenario_flows["flow"].sum()
    
    # Find edges with increased congestion
    if baseline_flows is not None:
        changes = calculate_flow_changes(baseline_flows, scenario_flows)
        congested_edges = len(changes[changes["flow_change"] > 0])
        relieved_edges = len(changes[changes["flow_change"] < 0])
        max_increase = changes["flow_change"].max() if len(changes) > 0 else 0
        max_decrease = changes["flow_change"].min() if len(changes) > 0 else 0
    else:
        congested_edges = 0
        relieved_edges = 0
        max_increase = 0
        max_decrease = 0
    
    metrics = {
        "scenario_name": scenario_name,
        "baseline_total_trips": baseline_total,
        "scenario_total_trips": scenario_total,
        "trip_change": scenario_total - baseline_total,
        "congested_edges": congested_edges,
        "relieved_edges": relieved_edges,
        "max_flow_increase": max_increase,
        "max_flow_decrease": max_decrease,
        "edges_used": len(scenario_flows)
    }
    
    return metrics


def export_performance_matrix(all_metrics):
    """
    Export scenario performance matrix to CSV.
    
    Args:
        all_metrics: List of metric dictionaries
    """
    logger.info("Exporting performance matrix...")
    
    metrics_df = pd.DataFrame(all_metrics)
    
    output_file = os.path.join(OUTPUT_DIR, "Scenario_Performance_Matrix.csv")
    metrics_df.to_csv(output_file, index=False)
    
    logger.info(f"  Saved to {output_file}")
    logger.info("\nScenario Performance Summary:")
    logger.info(metrics_df.to_string())
    
    return metrics_df


def export_diversion_routes(scenario_num, scenario_name, baseline_flows):
    """
    Export roads with significant flow diversions.
    
    Args:
        scenario_num: Scenario number
        scenario_name: Scenario name
        baseline_flows: Baseline flows GeoDataFrame
    """
    logger.info(f"Exporting diversion routes for {scenario_name}...")
    
    scenario_flows = load_scenario_flows(scenario_num)
    if scenario_flows is None:
        logger.warning("Cannot export diversion routes without scenario flows")
        return
    
    # Calculate changes
    changes = calculate_flow_changes(baseline_flows, scenario_flows)
    
    if len(changes) == 0:
        logger.info("  No flow changes detected")
        return
    
    # Filter for significant changes (>10% or >10 trips)
    significant = changes[
        (changes["pct_change"].abs() > 10) | (changes["flow_change"].abs() > 10)
    ]
    
    if len(significant) > 0:
        output_file = os.path.join(
            OUTPUT_DIR, 
            f"DiversionRoutes_Scenario_{scenario_num}.geojson"
        )
        
        # Add geometry from scenario flows
        diverted = significant.merge(
            scenario_flows[["from_node", "to_node", "geometry"]],
            on=["from_node", "to_node"],
            how="left"
        )
        
        diverted_gdf = gpd.GeoDataFrame(diverted, crs="EPSG:4326")
        diverted_gdf.to_file(output_file, driver="GeoJSON")
        
        logger.info(f"  Exported {len(diverted_gdf)} diversions to {output_file}")
    else:
        logger.info("  No significant diversions found")


def generate_report(num_scenarios):
    """
    Main reporting orchestration.
    
    Args:
        num_scenarios: Number of scenarios to analyze
    """
    logger.info("=" * 60)
    logger.info("MODULE 5: Reporting and Visualization")
    logger.info("=" * 60 + "\n")
    
    # Load baseline flows
    baseline_flows = load_scenario_flows(0)
    if baseline_flows is None:
        logger.warning("Baseline flows not found, proceeding without baseline comparison")
    
    # Calculate metrics for all scenarios
    all_metrics = []
    
    for scenario_num in range(1, num_scenarios + 1):
        scenario_name = f"Scenario {scenario_num}"
        scenario_flows = load_scenario_flows(scenario_num)
        
        if scenario_flows is None:
            logger.warning(f"Flows not found for scenario {scenario_num}")
            continue
        
        # Calculate metrics
        metrics = calculate_scenario_metrics(baseline_flows, scenario_flows, scenario_name)
        all_metrics.append(metrics)
        
        # Export diversion routes
        if baseline_flows is not None:
            export_diversion_routes(scenario_num, scenario_name, baseline_flows)
    
    # Export performance matrix
    if len(all_metrics) > 0:
        export_performance_matrix(all_metrics)
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Module 5 complete")
    logger.info("=" * 60)
    logger.info("\nNext step: python main.py (to run full model)\n")


if __name__ == "__main__":
    generate_report(num_scenarios=8)
