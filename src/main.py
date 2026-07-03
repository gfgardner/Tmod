"""
HOXTON STRATEGIC NETWORK MODEL (HSNM)
Main Orchestrator

This script runs the complete model pipeline:
1. Module 1: Build OS Highways graph
2. Module 2: Apply closures (bus gates) for each scenario
3. Module 3: Generate demand (OD pairs)
4. Module 4: Run traffic assignment for baseline + scenarios
5. Module 5: Generate reports and compare scenarios

Run this file to execute the entire model:
    python main.py

The model will:
- Load OS Highways network
- Create baseline graph
- Generate scenario graphs (with bus gates)
- Generate demand patterns
- Assign traffic to baseline and each scenario
- Export results to QGIS

Output locations:
- network/: Graphs and network files
- outputs/: Results, GeoPackages, and reports
"""

import logging
import sys
import os
import time

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR, NETWORK_DIR, BASE_GRAPH
from build_os_graph import build_network
from closures import apply_all_closures, load_base_graph as load_graph_for_closures, load_closures
from demand import load_demand
from assignment import assign_scenario, load_graph
from reporting import generate_report

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_output_directories():
    """Create output directories if they don't exist."""
    for directory in [OUTPUT_DIR, NETWORK_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")


def run_full_model():
    """Execute the complete model pipeline."""
    
    start_time = time.time()
    
    logger.info("\n" + "=" * 70)
    logger.info("HOXTON STRATEGIC NETWORK MODEL (HSNM)")
    logger.info("=" * 70)
    logger.info("\nStarting full model run...\n")
    
    # Create output directories
    logger.info("Step 0: Setting up directories...")
    create_output_directories()
    logger.info("✓ Directories ready\n")
    
    # ================================================================
    # STEP 1: Build base network
    # ================================================================
    logger.info("Step 1: Building OS Highways network...")
    logger.info("-" * 70)
    
    if not build_network():
        logger.error("Failed to build network. Exiting.")
        return False
    
    logger.info("✓ Network built\n")
    
    # ================================================================
    # STEP 2: Apply closures to create scenario graphs
    # ================================================================
    logger.info("Step 2: Creating scenario graphs...")
    logger.info("-" * 70)
    
    G = load_graph_for_closures()
    if G is None:
        logger.error("Failed to load base graph. Exiting.")
        return False
    
    closures = load_closures()
    if closures is None:
        logger.error("Failed to load closures. Exiting.")
        return False
    
    scenarios = apply_all_closures(G, closures)
    
    if len(scenarios) == 0:
        logger.error("Failed to create scenarios. Exiting.")
        return False
    
    logger.info(f"✓ {len(scenarios)} scenario graphs created\n")
    
    # ================================================================
    # STEP 3: Generate demand (OD pairs)
    # ================================================================
    logger.info("Step 3: Generating demand...")
    logger.info("-" * 70)
    
    od_df = load_demand()
    if od_df is None or len(od_df) == 0:
        logger.error("Failed to generate demand. Exiting.")
        return False
    
    logger.info("✓ Demand generated\n")
    
    # ================================================================
    # STEP 4: Run traffic assignment (baseline + all scenarios)
    # ================================================================
    logger.info("Step 4: Running traffic assignment...")
    logger.info("-" * 70)
    
    # 4a. Baseline assignment
    logger.info("\n[Baseline Assignment]")
    baseline_result = assign_scenario(
        graph_file=BASE_GRAPH,
        od_df=od_df,
        scenario_num=0,
        scenario_name="Baseline"
    )
    
    if baseline_result is None:
        logger.error("Failed baseline assignment. Exiting.")
        return False
    
    # 4b. Scenario assignments
    scenario_results = {}
    for scenario_num, scenario_data in scenarios.items():
        logger.info(f"\n[Scenario {scenario_num}: {scenario_data['name']}]")
        
        scenario_graph_file = os.path.join(
            NETWORK_DIR, 
            f"scenario_{scenario_num:02d}_{scenario_data['name']}.graphml"
        )
        
        scenario_result = assign_scenario(
            graph_file=scenario_graph_file,
            od_df=od_df,
            scenario_num=scenario_num,
            scenario_name=scenario_data['name']
        )
        
        if scenario_result is None:
            logger.warning(f"Failed assignment for scenario {scenario_num}")
            continue
        
        scenario_results[scenario_num] = scenario_result
    
    logger.info(f"\n✓ Assignment complete: {len(scenario_results)} scenarios\n")
    
    # ================================================================
    # STEP 5: Generate reports
    # ================================================================
    logger.info("Step 5: Generating reports...")
    logger.info("-" * 70)
    
    generate_report(num_scenarios=len(scenario_results))
    
    logger.info("✓ Reports generated\n")
    
    # ================================================================
    # COMPLETION
    # ================================================================
    elapsed_time = time.time() - start_time
    
    logger.info("=" * 70)
    logger.info("✓ HOXTON MODEL COMPLETE")
    logger.info("=" * 70)
    logger.info(f"\nElapsed time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
    logger.info("\nOutput files:")
    logger.info(f"  - Network graphs: {NETWORK_DIR}/")
    logger.info(f"  - Results: {OUTPUT_DIR}/")
    logger.info("\nNext steps:")
    logger.info("  1. Open QGIS")
    logger.info("  2. Load outputs/AssignedFlows_*.geojson")
    logger.info("  3. Compare baseline vs. scenarios")
    logger.info("  4. Review outputs/Scenario_Performance_Matrix.csv")
    logger.info("\n" + "=" * 70 + "\n")
    
    return True


def main():
    """Entry point."""
    try:
        success = run_full_model()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
