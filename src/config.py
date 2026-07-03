# ============================================================
# HOXTON STRATEGIC NETWORK MODEL (HSNM)
# CONFIGURATION FILE
# ============================================================

import os

# Base directory (parent of src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directory paths
INPUT_DIR = os.path.join(BASE_DIR, "input")
NETWORK_DIR = os.path.join(BASE_DIR, "network")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# ============================================================
# INPUT FILES (OS HIGHWAYS)
# ============================================================

OS_NODES = os.path.join(INPUT_DIR, "os_highways_nodes.geojson")
OS_ROADLINKS = os.path.join(INPUT_DIR, "os_highways_roadlinks.geojson")
OS_PATHS = os.path.join(INPUT_DIR, "os_highways_paths.geojson")
OS_STREETS = os.path.join(INPUT_DIR, "os_highways_streets.geojson")
OS_VEHICLE_CROSSOVER = os.path.join(INPUT_DIR, "os_vehicle_crossover.geojson")

# ============================================================
# INPUT FILES (SCENARIOS & DEMAND)
# ============================================================

CLOSURES_FILE = os.path.join(INPUT_DIR, "Closures.gpkg")
STUDY_BOUNDARY = os.path.join(INPUT_DIR, "StudyBoundary.gpkg")
MSOA_DEMAND = os.path.join(INPUT_DIR, "MSOA_Demand_Data.csv")

# ============================================================
# NETWORK OUTPUT FILES
# ============================================================

BASE_GRAPH = os.path.join(NETWORK_DIR, "base_os_graph.graphml")
BASE_NODES = os.path.join(NETWORK_DIR, "base_os_nodes.gpkg")
BASE_EDGES = os.path.join(NETWORK_DIR, "base_os_edges.gpkg")

# ============================================================
# MODEL PARAMETERS
# ============================================================

# Average speeds (km/h) by road type
SPEEDS = {
    "motorway": 50,
    "trunk": 40,
    "primary": 30,
    "secondary": 25,
    "tertiary": 20,
    "residential": 18,
    "living_street": 10,
    "service": 8
}

# Assignment method
ASSIGNMENT_METHOD = "all_or_nothing"

# Demand scaling (for calibration)
DEMAND_SCALE = 1.0

# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL = "INFO"
