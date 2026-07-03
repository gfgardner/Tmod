"""
Module 2 – Apply Closures (Bus Gates)

This module:
- Reads Closures.gpkg (GeoPackage with bus gate features)
- Each feature = one scenario
- Finds roadlinks that intersect each closure
- Creates scenario-specific graphs by removing car movement on closed roads
- Saves each scenario graph for assignment

A closure is implemented by:
1. Finding all roadlinks that intersect the closure geometry
2. Removing those edges from the graph for that scenario
3. Creating a new DiGraph for each scenario
"""

import geopandas as gpd
import networkx as nx
import logging
import sys
import os
from shapely.geometry import Point, LineString

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CLOSURES_FILE, BASE_GRAPH, NETWORK_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_base_graph():
    """Load the base NetworkX graph."""
    logger.info(f"Loading base graph from {BASE_GRAPH}...")
    
    if not os.path.exists(BASE_GRAPH):
        logger.error(f"Base graph not found: {BASE_GRAPH}")
        logger.error("Run Module 1 (build_os_graph.py) first")
        return None
    
    try:
        G = nx.read_graphml(BASE_GRAPH)
        logger.info(f"  Loaded graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G
    except Exception as e:
        logger.error(f"Error loading graph: {e}")
        return None


def load_closures():
    """Load bus gate closures from GeoPackage."""
    logger.info(f"Loading closures from {CLOSURES_FILE}...")
    
    if not os.path.exists(CLOSURES_FILE):
        logger.error(f"Closures file not found: {CLOSURES_FILE}")
        return None
    
    try:
        closures = gpd.read_file(CLOSURES_FILE)
        logger.info(f"  Loaded {len(closures)} closures/scenarios")
        
        # List closure names
        if "name" in closures.columns:
            for idx, name in enumerate(closures["name"], 1):
                logger.info(f"    Scenario {idx}: {name}")
        
        return closures
    
    except Exception as e:
        logger.error(f"Error loading closures: {e}")
        return None


def find_intersecting_edges(G, closure_geometry, roadlinks_gdf):
    """
    Find all roadlinks that intersect a closure geometry.
    
    Args:
        G: NetworkX graph
        closure_geometry: Shapely geometry of closure
        roadlinks_gdf: GeoDataFrame of all roadlinks (for reference)
    
    Returns:
        List of edge tuples (from_node, to_node) to remove
    """
    edges_to_remove = []
    
    # Expand closure geometry slightly to catch near-intersections
    closure_buffer = closure_geometry.buffer(5)  # 5 meter buffer
    
    for u, v, data in G.edges(data=True):
        # Skip if no geometry stored in edge
        if "geometry" not in data:
            continue
        
        edge_geom = data["geometry"]
        
        # Check if edge intersects closure
        if edge_geom.intersects(closure_buffer):
            edges_to_remove.append((u, v))
    
    return edges_to_remove


def apply_closure(G, closure_geometry, scenario_name):
    """
    Create a scenario graph by applying a closure.
    
    Args:
        G: Base NetworkX graph
        closure_geometry: Shapely geometry of closure
        scenario_name: Name of the scenario
    
    Returns:
        New graph with closure applied
    """
    logger.info(f"Applying closure: {scenario_name}")
    
    # Create a copy of the graph
    G_scenario = G.copy()
    
    # Find edges to remove
    edges_to_remove = find_intersecting_edges(G_scenario, closure_geometry, None)
    
    logger.info(f"  Found {len(edges_to_remove)} intersecting edges")
    
    # Remove edges
    for u, v in edges_to_remove:
        if G_scenario.has_edge(u, v):
            G_scenario.remove_edge(u, v)
    
    logger.info(f"  Scenario graph: {G_scenario.number_of_nodes()} nodes, {G_scenario.number_of_edges()} edges")
    
    return G_scenario, len(edges_to_remove)


def save_scenario_graph(G, scenario_num, scenario_name):
    """Save scenario graph to GraphML."""
    output_file = os.path.join(NETWORK_DIR, f"scenario_{scenario_num:02d}_{scenario_name}.graphml")
    
    logger.info(f"Saving to {output_file}...")
    
    try:
        nx.write_graphml(G, output_file)
        logger.info("  ✓ Saved")
        return output_file
    except Exception as e:
        logger.error(f"Error saving scenario graph: {e}")
        return None


def apply_all_closures(G, closures):
    """
    Apply all closures from the Closures.gpkg file.
    
    Returns:
        Dictionary mapping scenario_num -> (scenario_graph, closed_edge_count)
    """
    logger.info("=" * 60)
    logger.info("MODULE 2: Apply Closures")
    logger.info("=" * 60 + "\n")
    
    scenarios = {}
    
    for idx, row in closures.iterrows():
        scenario_num = idx + 1
        
        # Get scenario name from attributes
        if "name" in closures.columns:
            scenario_name = row["name"]
        else:
            scenario_name = f"Scenario_{scenario_num}"
        
        logger.info(f"\nScenario {scenario_num}: {scenario_name}")
        logger.info("-" * 60)
        
        # Get closure geometry
        closure_geom = row["geometry"]
        
        # Apply closure
        G_scenario, closed_count = apply_closure(G, closure_geom, scenario_name)
        
        # Save scenario graph
        save_scenario_graph(G_scenario, scenario_num, scenario_name)
        
        # Store scenario
        scenarios[scenario_num] = {
            "name": scenario_name,
            "graph": G_scenario,
            "closed_edges": closed_count
        }
    
    logger.info("\n" + "=" * 60)
    logger.info(f"✓ Module 2 complete: {len(scenarios)} scenarios created")
    logger.info("=" * 60)
    logger.info("\nNext step: python demand.py\n")
    
    return scenarios


def main():
    """Main orchestration."""
    # Load base graph
    G = load_base_graph()
    if G is None:
        return False
    
    # Load closures
    closures = load_closures()
    if closures is None:
        return False
    
    # Apply all closures
    scenarios = apply_all_closures(G, closures)
    
    return len(scenarios) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
