"""
Module 3 – Generate Demand (OD Pairs)

This module:
- Loads MSOA_Demand_Data.csv (population/workplace weighting)
- Identifies MSOAs near the Hoxton study area
- Creates weighted trip origins (where people live)
- Creates weighted trip destinations (where people work)
- Generates OD pairs for assignment

For Version 1, we use a simple gravity model:
- All MSOAs within/near study area are both origins and destinations
- Trip weight = residential population (for origins) × workplace population (for destinations)
- This creates realistic demand without needing a full OD matrix
"""

import pandas as pd
import geopandas as gpd
import logging
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MSOA_DEMAND, STUDY_BOUNDARY, OUTPUT_DIR, DEMAND_SCALE
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_demand_data():
    """Load MSOA demand weighting data."""
    logger.info(f"Loading demand data from {MSOA_DEMAND}...")
    
    if not os.path.exists(MSOA_DEMAND):
        logger.error(f"Demand file not found: {MSOA_DEMAND}")
        return None
    
    try:
        demand_df = pd.read_csv(MSOA_DEMAND)
        logger.info(f"  Loaded {len(demand_df)} MSOAs")
        
        # Check required columns
        required_cols = ["Code", "Name", "Residence Total", "WP"]
        missing_cols = [col for col in required_cols if col not in demand_df.columns]
        
        if missing_cols:
            logger.warning(f"Missing columns: {missing_cols}")
            logger.info(f"Available columns: {list(demand_df.columns)}")
        
        return demand_df
    
    except Exception as e:
        logger.error(f"Error loading demand data: {e}")
        return None


def load_study_boundary():
    """Load study area boundary."""
    logger.info(f"Loading study boundary from {STUDY_BOUNDARY}...")
    
    if not os.path.exists(STUDY_BOUNDARY):
        logger.warning(f"Study boundary not found: {STUDY_BOUNDARY}")
        logger.warning("Using all MSOAs as demand sources")
        return None
    
    try:
        boundary = gpd.read_file(STUDY_BOUNDARY)
        logger.info(f"  Loaded study boundary")
        return boundary
    
    except Exception as e:
        logger.error(f"Error loading boundary: {e}")
        return None


def filter_relevant_msoas(demand_df, boundary_gdf):
    """
    Filter MSOAs to those relevant for Hoxton modelling.
    
    For Version 1, we include:
    - All MSOAs in the study area
    - MSOAs adjacent to the study area
    
    Args:
        demand_df: DataFrame with MSOA demand data
        boundary_gdf: GeoDataFrame with study boundary (or None)
    
    Returns:
        Filtered DataFrame
    """
    if boundary_gdf is None:
        logger.warning("No boundary provided, using all MSOAs")
        return demand_df
    
    logger.info("Filtering MSOAs for Hoxton study area...")
    
    # For now, use all MSOAs as demand sources
    # In a full implementation, you would:
    # 1. Find MSOAs that intersect the boundary
    # 2. Find adjacent MSOAs
    # 3. Calculate distance-decay weights
    
    logger.info(f"  Using all {len(demand_df)} MSOAs as potential demand sources")
    
    return demand_df


def generate_od_pairs(demand_df, scale_factor=1.0):
    """
    Generate OD pairs from demand data.
    
    Simple gravity model:
    - Every MSOA is both an origin and destination
    - Trip volume = origin_population × destination_workplace_population
    - Scaled by scale_factor for calibration
    
    Args:
        demand_df: DataFrame with columns [Code, Residence Total, WP]
        scale_factor: Scaling factor for demand (default 1.0)
    
    Returns:
        DataFrame with columns [origin_msoa, destination_msoa, flow]
    """
    logger.info("Generating OD pairs using gravity model...")
    
    od_pairs = []
    
    # Normalize demand to trip rates
    # Assumption: Average trip per person = 1.0 trips/day
    
    for origin_idx, origin_row in demand_df.iterrows():
        origin_code = origin_row["Code"]
        origin_pop = origin_row.get("Residence Total", 0)
        
        # Skip if no population
        if pd.isna(origin_pop) or origin_pop <= 0:
            continue
        
        for dest_idx, dest_row in demand_df.iterrows():
            dest_code = dest_row["Code"]
            dest_jobs = dest_row.get("WP", 0)
            
            # Skip if no destinations
            if pd.isna(dest_jobs) or dest_jobs <= 0:
                continue
            
            # Simple gravity: flow = origin_pop * dest_jobs / total_jobs
            total_jobs = demand_df["WP"].sum()
            
            if total_jobs > 0:
                flow = (origin_pop * dest_jobs / total_jobs) * scale_factor
                
                if flow > 0:
                    od_pairs.append({
                        "origin_msoa": origin_code,
                        "destination_msoa": dest_code,
                        "flow": flow
                    })
    
    od_df = pd.DataFrame(od_pairs)
    logger.info(f"  Generated {len(od_df)} OD pairs")
    logger.info(f"  Total demand: {od_df['flow'].sum():.0f} trips")
    
    return od_df


def save_demand_outputs(demand_df, od_df):
    """Save demand data for reference."""
    logger.info("Saving demand outputs...")
    
    # Save OD pairs
    od_file = os.path.join(OUTPUT_DIR, "od_pairs.csv")
    od_df.to_csv(od_file, index=False)
    logger.info(f"  Saved OD pairs to {od_file}")
    
    # Save MSOA statistics
    msoa_stats = demand_df[[
        "Code", "Name", "Residence Total", "WP"
    ]].copy()
    
    stats_file = os.path.join(OUTPUT_DIR, "msoa_statistics.csv")
    msoa_stats.to_csv(stats_file, index=False)
    logger.info(f"  Saved MSOA statistics to {stats_file}")


def load_demand():
    """
    Main orchestration function for demand module.
    
    Returns:
        DataFrame with columns [origin_msoa, destination_msoa, flow]
    """
    logger.info("=" * 60)
    logger.info("MODULE 3: Generate Demand (OD Pairs)")
    logger.info("=" * 60 + "\n")
    
    # Load demand data
    demand_df = load_demand_data()
    if demand_df is None:
        return None
    
    # Load study boundary (optional)
    boundary_gdf = load_study_boundary()
    
    # Filter to relevant MSOAs
    relevant_msoas = filter_relevant_msoas(demand_df, boundary_gdf)
    
    # Generate OD pairs
    od_df = generate_od_pairs(relevant_msoas, scale_factor=DEMAND_SCALE)
    
    # Save outputs
    save_demand_outputs(relevant_msoas, od_df)
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Module 3 complete")
    logger.info("=" * 60)
    logger.info("\nNext step: python assignment.py\n")
    
    return od_df


if __name__ == "__main__":
    od_df = load_demand()
    success = od_df is not None
    sys.exit(0 if success else 1)
