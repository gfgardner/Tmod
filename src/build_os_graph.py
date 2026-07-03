"""
Module 1 – Build OS Highways Graph

This module:
- Loads OS Highways GeoJSONs (nodes, roadlinks, paths, streets)
- Builds a NetworkX DiGraph for routing
- Preserves OS TOIDs (Topographic Object IDs) as unique link identifiers
- Exports graph to GraphML format
- Exports nodes and edges as GeoPackages for QGIS inspection

Run this once to create the base network. After that, all scenarios use this graph.
"""

import geopandas as gpd
import networkx as nx
import logging
import sys
import os

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    OS_NODES, OS_ROADLINKS, BASE_GRAPH, BASE_NODES, BASE_EDGES, NETWORK_DIR
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_input_files():
    """Verify that all required OS Highways files exist."""
    logger.info("Checking input files...")
    
    files_to_check = [OS_NODES, OS_ROADLINKS]
    missing_files = []
    
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            missing_files.append(filepath)
    
    if missing_files:
        logger.error("Missing input files:")
        for f in missing_files:
            logger.error(f"  - {f}")
        return False
    
    logger.info("✓ All input files found")
    return True


def ensure_output_dir():
    """Create network output directory if it doesn't exist."""
    if not os.path.exists(NETWORK_DIR):
        os.makedirs(NETWORK_DIR)
        logger.info(f"Created directory: {NETWORK_DIR}")


def load_nodes():
    """Load OS Highways nodes from GeoJSON."""
    logger.info(f"Loading nodes from {OS_NODES}...")
    
    try:
        nodes = gpd.read_file(OS_NODES)
        logger.info(f"  Loaded {len(nodes)} nodes")
        
        # Check required columns
        required_cols = ["TOID", "geometry"]
        missing_cols = [col for col in required_cols if col not in nodes.columns]
        
        if missing_cols:
            logger.error(f"Missing columns in nodes: {missing_cols}")
            return None
        
        return nodes
    
    except Exception as e:
        logger.error(f"Error loading nodes: {e}")
        return None


def load_roadlinks():
    """Load OS Highways roadlinks from GeoJSON."""
    logger.info(f"Loading roadlinks from {OS_ROADLINKS}...")
    
    try:
        roadlinks = gpd.read_file(OS_ROADLINKS)
        logger.info(f"  Loaded {len(roadlinks)} roadlinks")
        
        # Check required columns
        required_cols = ["TOID", "startNode", "endNode", "geometry"]
        missing_cols = [col for col in required_cols if col not in roadlinks.columns]
        
        if missing_cols:
            logger.error(f"Missing columns in roadlinks: {missing_cols}")
            return None
        
        return roadlinks
    
    except Exception as e:
        logger.error(f"Error loading roadlinks: {e}")
        return None


def build_graph(nodes, roadlinks):
    """
    Build NetworkX DiGraph from OS data.
    
    Graph structure:
    - Nodes: OS node IDs (junctions)
    - Edges: (from_node, to_node) with attributes:
      - toid: OS roadlink TOID (unique link identifier)
      - length: roadlink length in meters
      - geometry: shapely LineString
    
    Returns: NetworkX DiGraph
    """
    logger.info("Building routing graph...")
    
    G = nx.DiGraph()
    
    # Add nodes from OS Highways nodes layer
    logger.info("Adding nodes to graph...")
    node_count = 0
    
    for idx, row in nodes.iterrows():
        node_id = row["TOID"]
        geom = row["geometry"]
        
        G.add_node(
            node_id,
            x=geom.x,
            y=geom.y,
            geometry=geom
        )
        node_count += 1
    
    logger.info(f"  Added {node_count} nodes")
    
    # Add edges from roadlinks
    logger.info("Adding edges to graph...")
    edge_count = 0
    missing_node_count = 0
    
    for idx, row in roadlinks.iterrows():
        link_toid = row["TOID"]
        start_node = row["startNode"]
        end_node = row["endNode"]
        geom = row["geometry"]
        
        # Check if both nodes exist in graph
        if start_node not in G.nodes():
            logger.warning(f"Start node {start_node} not in graph (link {link_toid})")
            missing_node_count += 1
            continue
        
        if end_node not in G.nodes():
            logger.warning(f"End node {end_node} not in graph (link {link_toid})")
            missing_node_count += 1
            continue
        
        # Calculate length (meters)
        length = geom.length
        
        # Add edge
        G.add_edge(
            start_node, end_node,
            toid=link_toid,
            length=length,
            geometry=geom
        )
        edge_count += 1
    
    logger.info(f"  Added {edge_count} edges")
    if missing_node_count > 0:
        logger.warning(f"  Skipped {missing_node_count} edges with missing nodes")
    
    # Check connectivity
    logger.info("Checking graph connectivity...")
    is_connected = nx.is_strongly_connected(G)
    
    if is_connected:
        logger.info("  ✓ Graph is strongly connected")
    else:
        sccs = list(nx.strongly_connected_components(G))
        logger.warning(f"  Graph has {len(sccs)} strongly connected components")
        largest_scc = max(sccs, key=len)
        pct = 100 * len(largest_scc) / G.number_of_nodes()
        logger.info(f"    Largest component: {len(largest_scc)} nodes ({pct:.1f}%)")
    
    logger.info(f"\n✓ Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")
    
    return G


def save_graph(G):
    """Save graph to GraphML format."""
    logger.info(f"Saving graph to {BASE_GRAPH}...")
    
    try:
        nx.write_graphml(G, BASE_GRAPH)
        logger.info("  ✓ Graph saved")
    except Exception as e:
        logger.error(f"Error saving graph: {e}")
        return False
    
    return True


def save_geopackages(nodes, roadlinks):
    """Save nodes and edges as GeoPackages for QGIS inspection."""
    logger.info("Saving GeoPackages for QGIS...")
    
    try:
        logger.info(f"  Saving nodes to {BASE_NODES}...")
        nodes.to_file(BASE_NODES, driver="GPKG", layer="nodes")
        logger.info("    ✓ Nodes saved")
        
        logger.info(f"  Saving roadlinks to {BASE_EDGES}...")
        roadlinks.to_file(BASE_EDGES, driver="GPKG", layer="roadlinks")
        logger.info("    ✓ Roadlinks saved")
    
    except Exception as e:
        logger.error(f"Error saving GeoPackages: {e}")
        return False
    
    return True


def build_network():
    """Main orchestration function."""
    logger.info("=" * 60)
    logger.info("MODULE 1: Build OS Highways Network Graph")
    logger.info("=" * 60 + "\n")
    
    # Check inputs
    if not check_input_files():
        logger.error("Cannot proceed without input files")
        return False
    
    # Create output directory
    ensure_output_dir()
    
    # Load data
    nodes = load_nodes()
    if nodes is None:
        return False
    
    roadlinks = load_roadlinks()
    if roadlinks is None:
        return False
    
    # Build graph
    G = build_graph(nodes, roadlinks)
    
    # Save outputs
    if not save_graph(G):
        return False
    
    if not save_geopackages(nodes, roadlinks):
        logger.warning("Warning: GeoPackage export failed, but graph is saved")
    
    logger.info("=" * 60)
    logger.info("✓ Module 1 complete")
    logger.info("=" * 60)
    logger.info("\nNext step: python closures.py\n")
    
    return True


if __name__ == "__main__":
    success = build_network()
    sys.exit(0 if success else 1)
