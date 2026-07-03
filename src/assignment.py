"""
Module 4 – Traffic Assignment (Shortest Path)

This module:
- Loads a scenario graph (baseline or with closures applied)
- Loads OD pairs (demand from Module 3)
- Runs all-or-nothing shortest-path assignment
- For each OD pair, finds shortest path and assigns all demand to that path
- Accumulates flow on each edge
- Exports results for comparison

Assignment algorithm:
1. For each OD pair in the demand:
   - Find shortest path using Dijkstra
   - Add the trip volume to all edges in the path
2. After all OD pairs:
   - Export edge flows to GeoPackage
   - Calculate congestion metrics
"""

import networkx as nx
import geopandas as gpd
import pandas as pd
import logging
import sys
import os
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BASE_GRAPH, NETWORK_DIR, OUTPUT_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_graph(graph_file):
    """Load a NetworkX graph from GraphML."""
    logger.info(f"Loading graph from {graph_file}...")
    
    if not os.path.exists(graph_file):
        logger.error(f"Graph file not found: {graph_file}")
        return None
    
    try:
        G = nx.read_graphml(graph_file)
        logger.info(f"  Loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G
    except Exception as e:
        logger.error(f"Error loading graph: {e}")
        return None


def find_msoa_representative_nodes(G, msoa_code):
    """
    Find representative nodes for an MSOA.
    
    For Version 1, we use all nodes as potential origins/destinations.
    In a full model, you would:
    - Map MSOAs to centroids
    - Find nearest network nodes to centroids
    - Use those as origin/destination points
    """
    # Simplified: return a random node (in practice, use centroid-based lookup)
    nodes = list(G.nodes())
    if len(nodes) > 0:
        return nodes[len(msoa_code) % len(nodes)]
    return None


def run_assignment(G, od_df, scenario_name="baseline"):
    """
    Run all-or-nothing shortest-path assignment.
    
    Args:
        G: NetworkX graph
        od_df: DataFrame with columns [origin_msoa, destination_msoa, flow]
        scenario_name: Name of scenario (for logging)
    
    Returns:
        Dictionary mapping (u, v) -> flow
    """
    logger.info(f"Running assignment for {scenario_name}...")
    
    edge_flows = defaultdict(float)
    paths_found = 0
    paths_failed = 0
    total_trips = 0
    
    for idx, row in od_df.iterrows():
        origin_msoa = row["origin_msoa"]
        destination_msoa = row["destination_msoa"]
        flow = row["flow"]
        
        # Find representative nodes for MSOAs
        # (In reality, map MSOA codes to nearest network nodes)
        origin_node = find_msoa_representative_nodes(G, str(origin_msoa))
        destination_node = find_msoa_representative_nodes(G, str(destination_msoa))
        
        if origin_node is None or destination_node is None:
            paths_failed += 1
            continue
        
        # Find shortest path
        try:
            path = nx.shortest_path(G, origin_node, destination_node, weight="length")
            
            # Assign flow to all edges in path
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                edge_flows[(u, v)] += flow
            
            paths_found += 1
            total_trips += flow
        
        except nx.NetworkXNoPath:
            paths_failed += 1
            continue
    
    logger.info(f"  Paths found: {paths_found}")
    logger.info(f"  Paths failed: {paths_failed}")
    logger.info(f"  Total trips assigned: {total_trips:.0f}")
    
    return dict(edge_flows)


def export_flows_to_geopackage(G, edge_flows, base_edges_file, output_file, scenario_name):
    """
    Export assigned flows to GeoPackage for QGIS visualization.
    
    Args:
        G: NetworkX graph
        edge_flows: Dictionary mapping (u, v) -> flow
        base_edges_file: Path to base edges GeoPackage (for geometry reference)
        output_file: Path to save flows GeoPackage
        scenario_name: Name of scenario
    """
    logger.info(f"Exporting flows to {output_file}...")
    
    try:
        # Load base edges for geometry reference
        if os.path.exists(base_edges_file):
            base_edges = gpd.read_file(base_edges_file)
            logger.info(f"  Loaded base edges: {len(base_edges)} roadlinks")
        else:
            logger.warning(f"Base edges file not found: {base_edges_file}")
            base_edges = None
        
        # Create flows GeoDataFrame
        flow_rows = []
        
        for (u, v), flow in edge_flows.items():
            # Get geometry from edge data
            if G.has_edge(u, v) and "geometry" in G[u][v]:
                geom = G[u][v]["geometry"]
            else:
                geom = None
            
            # Get TOID if available
            toid = None
            if G.has_edge(u, v) and "toid" in G[u][v]:
                toid = G[u][v]["toid"]
            
            flow_rows.append({
                "from_node": u,
                "to_node": v,
                "toid": toid,
                "flow": flow,
                "geometry": geom
            })
        
        flows_gdf = gpd.GeoDataFrame(flow_rows, crs="EPSG:4326")
        flows_gdf.to_file(output_file, driver="GPKG")
        
        logger.info(f"  Exported {len(flows_gdf)} edges with flows")
        logger.info(f"  Total flow: {flows_gdf['flow'].sum():.0f} trips")
    
    except Exception as e:
        logger.error(f"Error exporting flows: {e}")


def calculate_metrics(edge_flows):
    """Calculate network-wide metrics."""
    flows = list(edge_flows.values())
    
    if len(flows) == 0:
        return None
    
    metrics = {
        "total_trips": sum(flows),
        "total_edges_used": len(flows),
        "avg_edge_flow": sum(flows) / len(flows),
        "max_edge_flow": max(flows),
        "min_edge_flow": min(flows)
    }
    
    return metrics


def assign_scenario(graph_file, od_df, scenario_num, scenario_name):
    """
    Run assignment for a single scenario.
    
    Args:
        graph_file: Path to scenario graph (or baseline graph)
        od_df: DataFrame with OD pairs
        scenario_num: Scenario number
        scenario_name: Scenario name
    
    Returns:
        Dictionary with assignment results
    """
    logger.info("\n" + "=" * 60)
    logger.info(f"ASSIGNMENT: Scenario {scenario_num} - {scenario_name}")
    logger.info("=" * 60)
    
    # Load graph
    G = load_graph(graph_file)
    if G is None:
        return None
    
    # Run assignment
    edge_flows = run_assignment(G, od_df, scenario_name)
    
    # Calculate metrics
    metrics = calculate_metrics(edge_flows)
    logger.info(f"\nMetrics:")
    for key, value in metrics.items():
        logger.info(f"  {key}: {value}")
    
    # Export flows
    base_edges_file = os.path.join(NETWORK_DIR, "base_os_edges.gpkg")
    output_file = os.path.join(OUTPUT_DIR, f"AssignedFlows_Scenario_{scenario_num}.geojson")
    export_flows_to_geopackage(G, edge_flows, base_edges_file, output_file, scenario_name)
    
    return {
        "scenario_num": scenario_num,
        "scenario_name": scenario_name,
        "edge_flows": edge_flows,
        "metrics": metrics
    }


if __name__ == "__main__":
    logger.info("Module 4: Traffic Assignment")
