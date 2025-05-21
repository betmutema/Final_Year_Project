import shutil
import click
import csv
import os
import pandas as pd
import numpy as np
import random
from scipy import interpolate
from pathlib import Path
from coexistence_simpy.coexistence_simulator import *

# Define the list of potential asymmetric AP-gNB pairs
POTENTIAL_ASYMMETRIC_PAIRS = [
    (1, 2), (1, 3), (1, 4), (1, 5), (2, 1), (2, 3), (2, 4),
    (2, 5), (2, 6), (2, 7), (2, 8), (3, 2), (3, 4), (3, 5),
    (3, 6), (3, 7), (3, 8), (4, 2), (4, 3), (4, 5), (4, 6),
    (4, 7), (4, 8), (5, 2), (5, 3), (5, 4), (5, 6), (5, 7),
    (5, 8), (6, 2), (6, 3), (6, 4), (6, 5), (6, 7), (6, 8),
    (7, 3), (7, 4), (7, 5), (7, 6), (7, 8), (8, 3), (8, 4),
    (8, 5), (8, 6), (8, 7),
]


def run_cw_sweep(
        cw_start,
        cw_end,
        cw_step,
        ap_number,
        gnb_number,
        runs=10,
        simulation_time=100.0,
        min_nru_cw=0,
        max_nru_cw=0,
        synchronization_slot_duration=1000,
        min_sync_slot_desync=0,
        max_sync_slot_desync=1000,
        nru_mode="gap"
):
    """
        Performs a parameter sweep over contention window sizes to evaluate
        coexistence performance between Wi-Fi and NR-U networks.
        This function is adapted from contention_window_sweep.py to be called directly
        when we need to generate data for optimal CW calculation.
    """
    print(f"Starting contention window sweep for {ap_number} WiFi and {gnb_number} NRU nodes...")
    print(f"CW range: {cw_start} to {cw_end} with step {cw_step}")

    # Define output file path
    output_file = f"output/simulation_results/airtime_fairness_{cw_start}_{cw_end}_{cw_step}_{ap_number}_{gnb_number}.csv"
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Initialize the output CSV file with header row
    with open(output_file, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "CW", "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency", "jain's_fairness_index", "joint_airtime_fairness"
        ])

    # Loop through the contention window range with specified step size
    for cw in range(cw_start, cw_end + 1, cw_step):
        print(
            f"Running simulations for CW = {cw} ({(cw - cw_start) // (cw_step) + 1}/{(cw_end - cw_start) // (cw_step) + 1})")
        # For each CW value, run multiple simulations with different random seeds
        for seed in range(runs):
            # Use a temporary file for the simulation output
            temp_output_file = "output/simulation_results/temp_results.csv"

            # Run a single simulation with the current parameters
            simulate_coexistence(
                ap_number,  # Number of Wi-Fi access points
                gnb_number,  # Number of NR-U base stations
                seed,  # Random seed for reproducibility
                simulation_time,  # Duration of simulation in seconds
                WiFiConfig(1472, cw, cw, 7, 7),  # Wi-Fi config with current CW value
                NRUConfig(
                    16, 9, synchronization_slot_duration,
                    max_sync_slot_desync, min_sync_slot_desync,
                    3, min_nru_cw, max_nru_cw, 6
                ),  # NR-U configuration
                {key: {ap_number: 0} for key in range(cw + 1)},  # Backoff counters
                {f"WiFiStation {i}": 0 for i in range(1, ap_number + 1)},  # Wi-Fi data airtime
                {f"WiFiStation {i}": 0 for i in range(1, ap_number + 1)},  # Wi-Fi control airtime
                {f"NRUBaseStation {i}": 0 for i in range(1, gnb_number + 1)},  # NR-U data airtime
                {f"NRUBaseStation {i}": 0 for i in range(1, gnb_number + 1)},  # NR-U control airtime
                nru_mode,  # NR-U operational mode
                temp_output_file  # Temporary output file
            )

            # Process the simulation results from the temporary file
            if os.path.exists(temp_output_file):
                with open(temp_output_file, 'r') as temp_file:
                    lines = temp_file.readlines()
                    if lines and len(lines) > 1:  # Make sure there's data
                        # Extract the last line which contains the final simulation metrics
                        last_line = lines[-1].strip().split(',')
                        # Append CW value and metrics to the final output CSV
                        with open(output_file, mode='a', newline='') as out_file:
                            writer = csv.writer(out_file)
                            writer.writerow([cw] + last_line)  # Add CW as first column

                # Remove the temporary file after processing
                os.remove(temp_output_file)

    print(f"Contention window sweep completed. Results saved to {output_file}")
    return output_file


def find_optimal_cw(num_wifi_nodes, num_nru_nodes):
    """
    Calculate the optimal contention window by finding the intersection
    of WiFi and NRU channel occupancy curves.

    If the required CSV file doesn't exist, it will run a contention window sweep
    to generate the necessary data.

    Args:
        num_wifi_nodes: Number of WiFi nodes
        num_nru_nodes: Number of NRU nodes

    Returns:
        int: Optimal contention window value
    """
    # Parameters for the contention window sweep
    cw_start = 32
    cw_end = 512
    cw_step = 48

    # Construct the CSV filename based on node density
    csv_filename = f"airtime_fairness_{cw_start}_{cw_end}_{cw_step}_{num_wifi_nodes}_{num_nru_nodes}.csv"
    csv_path = os.path.join('output', 'simulation_results', csv_filename)

    # Check if the required CSV file exists
    if not os.path.exists(csv_path):
        print(f"CSV file {csv_path} not found.")

        # Run the contention window sweep to generate the required data
        csv_path = run_cw_sweep(
            cw_start=cw_start,
            cw_end=cw_end,
            cw_step=cw_step,
            ap_number=num_wifi_nodes,
            gnb_number=num_nru_nodes
        )

        # Double-check if file was created
        if not os.path.exists(csv_path):
            print(f"Failed to create data file. Using default CW value of 63.")
            return 63

    # Now that we have the data, analyze it to find the optimal CW
    try:
        # Load the CSV data
        df = pd.read_csv(csv_path)

        # Check if the dataframe has the expected columns
        expected_columns = ['CW', 'wifi_channel_occupancy', 'nru_channel_occupancy']
        for col in expected_columns:
            if col not in df.columns:
                print(f"Error: Required column '{col}' not found in CSV. Using default CW value of 63.")
                return 63

        # Group by CW and calculate means for each metric
        grouped = df.groupby('CW').mean().reset_index()

        # Get arrays for intersection calculation
        cw_values = grouped['CW'].values
        wifi_occupancy = grouped['wifi_channel_occupancy'].values
        nru_occupancy = grouped['nru_channel_occupancy'].values

        # Create interpolation functions
        wifi_interp = interpolate.interp1d(cw_values, wifi_occupancy, kind='cubic')
        nru_interp = interpolate.interp1d(cw_values, nru_occupancy, kind='cubic')

        # Create a finer grid of CW values for more precise intersection finding
        fine_cw = np.linspace(min(cw_values), max(cw_values), 1000)
        fine_wifi = wifi_interp(fine_cw)
        fine_nru = nru_interp(fine_cw)

        # Find where the difference is closest to zero (intersection point)
        intersection_idx = np.argmin(np.abs(fine_wifi - fine_nru))
        intersection_cw = fine_cw[intersection_idx]

        # Calculate all parameters at the intersection point
        all_metrics = [
            'wifi_channel_efficiency', 'wifi_collision_probability',
            'nru_channel_efficiency', 'nru_collision_probability',
            'total_channel_occupancy', 'total_network_efficiency',
            'jain\'s_fairness_index', 'joint_airtime_fairness'
        ]

        params_at_intersection = {
            'CW': intersection_cw,
            'wifi_channel_occupancy': fine_wifi[intersection_idx],
            'nru_channel_occupancy': fine_nru[intersection_idx]
        }

        # Calculate interpolated values for all metrics at the intersection point
        for metric in all_metrics:
            if metric in grouped.columns:
                metric_interp = interpolate.interp1d(cw_values, grouped[metric].values, kind='cubic')
                params_at_intersection[metric] = metric_interp(intersection_cw)

        # Save analysis to CSV for reference
        intersection_row = pd.DataFrame([params_at_intersection])
        result_df = pd.concat([grouped, intersection_row]).sort_values('CW')
        analysis_path = os.path.join('output', 'analysis',
                                     f'intersection_analysis_{num_wifi_nodes}_{num_nru_nodes}.csv')

        # Create analysis directory if it doesn't exist
        os.makedirs(os.path.dirname(analysis_path), exist_ok=True)
        result_df.to_csv(analysis_path, index=False)

        # Round to nearest integer and return
        optimal_cw = round(intersection_cw)
        print(f"Node density ({num_wifi_nodes}, {num_nru_nodes}): Optimal CW = {optimal_cw}")
        print(
            f"At intersection: WiFi occupancy = {fine_wifi[intersection_idx]:.4f}, NRU occupancy = {fine_nru[intersection_idx]:.4f}")
        return optimal_cw

    except Exception as e:
        print(f"Error calculating optimal CW for node density ({num_wifi_nodes}, {num_nru_nodes}): {str(e)}")
        print("Using default CW value of 63.")
        return 63


# This script runs multiple simulations of WiFi and NR-U coexistence, varying the number of nodes
# and collecting statistics about channel efficiency, fairness, and collision probability.
@click.command()
@click.option("--runs", default=10, help="Number of simulation runs")
@click.option("--seed", default=1, help="Seed for simulation")
@click.option("--num_pairs", default=8, help="Number of asymmetric pairs to randomly select")
@click.option("--simulation_time", default=100.0, help="Simulation duration (s)")
@click.option("--min_wifi_cw", default=0, help="Wi-Fi minimum contention window")
@click.option("--max_wifi_cw", default=0, help="Wi-Fi maximum contention window")
@click.option("--wifi_r_limit", default=3, help="Wi-Fi retry limit")
@click.option("--min_nru_cw", default=0, help="NR-U minimum contention window")
@click.option("--max_nru_cw", default=0, help="NR-U maximum contention window")
@click.option("--mcs_value", default=7, help="Value of mcs")
@click.option("--synchronization_slot_duration", default=1000, help="Synchronization slot duration (μs)")
@click.option("--max_sync_slot_desync", default=1000, help="Max gNB desynchronization (μs)")
@click.option("--min_sync_slot_desync", default=0, help="Min gNB desynchronization (μs)")
@click.option("--nru_observation_slot", default=3, help="NR-U observation slots")
@click.option("--mcot", default=6, help="Max channel occupancy time for NR-U (ms)")
@click.option("--nru_mode", type=click.Choice(["rs", "gap"], case_sensitive=False), default="gap",
              help="NR-U mode: rs' for reservation signal mode, 'gap' for gap-based mode")
def changing_number_nodes(
        runs: int,
        seed: int,
        num_pairs: int,
        simulation_time: int,
        min_wifi_cw: int,
        max_wifi_cw: int,
        wifi_r_limit: int,
        mcs_value: int,
        min_nru_cw: int,
        max_nru_cw: int,
        synchronization_slot_duration: int,
        max_sync_slot_desync: int,
        min_sync_slot_desync: int,
        nru_observation_slot: int,
        mcot: int,
        nru_mode: str,
):
    """
    Main function that runs multiple simulations with varying numbers of nodes.

    For each randomly selected pair of (WiFi AP, NR-U gNB) node counts,
    runs multiple simulations with the specified parameters and saves results.
    """
    # Determine if we're using the "variant" mode where CW values are dynamically set
    is_variant = (
            min_wifi_cw == 0 and max_wifi_cw == 0 and
            min_nru_cw == 0 and max_nru_cw == 0 and
            nru_mode.lower() == "gap"
    )

    # Set random seed for pair selection
    random.seed(seed)

    # Randomly select num_pairs from the potential pairs
    selected_pairs = random.sample(POTENTIAL_ASYMMETRIC_PAIRS, num_pairs)

    print(f"Selected {num_pairs} asymmetric node pairs: {selected_pairs}")

    # Determine output file path based on configuration parameters
    if is_variant:
        output_path = f"output/simulation_results/coex_asymmetric_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_dynamic-cw_raw-data.csv"
    else:
        output_path = build_output_path(
            min_sync_slot_desync,
            max_sync_slot_desync,
            nru_mode,
            min_nru_cw,
            max_nru_cw,
            min_wifi_cw,
            max_wifi_cw,
            asymmetric=True
        )

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Initialize the CSV output file with headers
    with open(output_path, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency", "jain's_fairness_index", "joint_airtime_fairness"
        ])

    # Loop through each selected pair of node counts
    for wifi_nodes, nru_nodes in selected_pairs:
        print(f"\nProcessing node pair: WiFi APs = {wifi_nodes}, NR-U gNBs = {nru_nodes}")

        # In variant mode, dynamically calculate the optimal contention window
        if is_variant:
            # Use dynamic calculation based on airtime fairness analysis
            cw = find_optimal_cw(wifi_nodes, nru_nodes)
            min_wifi_cw = max_wifi_cw = cw  # Set both min and max to the same value
            print(f"Using calculated contention window {cw} for WiFi nodes: {wifi_nodes}, NR-U nodes: {nru_nodes}")

        # Initialize statistics tracking dictionaries for this node pair
        backoff_counts = {key: {wifi_nodes: 0} for key in range(max_wifi_cw + 1)}
        data_airtime_WiFi = {"WiFiStation {}".format(i): 0 for i in range(1, wifi_nodes + 1)}
        control_airtime_WiFi = {"WiFiStation {}".format(i): 0 for i in range(1, wifi_nodes + 1)}
        data_airtime_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, nru_nodes + 1)}
        control_airtime_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, nru_nodes + 1)}

        # Run multiple simulations with the same node counts but different seeds
        for i in range(0, runs):
            curr_seed = seed + i
            print(f"Running simulation {i + 1}/{runs} with seed {curr_seed}")

            # Run a single simulation with the current configuration
            simulate_coexistence(
                wifi_nodes,  # Number of WiFi nodes
                nru_nodes,  # Number of NR-U nodes
                curr_seed,  # Unique seed for this run
                simulation_time,
                WiFiConfig(  # WiFi configuration
                    1472,  # Data size in bytes
                    min_wifi_cw,  # Minimum contention window
                    max_wifi_cw,  # Maximum contention window
                    wifi_r_limit,  # Retry limit
                    mcs_value  # Modulation and Coding Scheme
                ),
                NRUConfig(  # NR-U configuration
                    16,  # Prioritization period in μs
                    9,  # Observation slot duration
                    synchronization_slot_duration,  # Duration of synchronization slots
                    max_sync_slot_desync,  # Maximum desynchronization offset
                    min_sync_slot_desync,  # Minimum desynchronization offset
                    nru_observation_slot,  # Number of observation slots
                    min_nru_cw,  # Minimum contention window
                    max_nru_cw,  # Maximum contention window
                    mcot  # Maximum Channel Occupancy Time
                ),
                backoff_counts,  # Statistics collection dictionaries
                data_airtime_WiFi,
                control_airtime_WiFi,
                data_airtime_NR,
                control_airtime_NR,
                nru_mode,  # NR-U operation mode
                output_path  # Output file path
            )


def build_output_path(
        min_sync_slot_desync: int,
        max_sync_slot_desync: int,
        nru_mode: str,
        min_nru_cw: int,
        max_nru_cw: int,
        min_wifi_cw: int,
        max_wifi_cw: int,
        asymmetric: bool = False
) -> str:
    """
    Builds an output file path based on simulation parameters.

    The filename encodes key simulation parameters to make results easily identifiable
    and to avoid overwriting previous results.
    """
    # Create base output directory
    base_dir = "output/simulation_results"
    os.makedirs(base_dir, exist_ok=True)

    # Add asymmetric identifier to filename
    asymmetric_prefix = "asymmetric_" if asymmetric else ""

    # Determine special configuration modes
    is_backoff_disabled = (min_nru_cw == 0 and max_nru_cw == 0)
    is_adjusted_cw_fixed = is_backoff_disabled and (min_wifi_cw > 0 and min_wifi_cw == max_wifi_cw)
    is_adjusted_cw_varied = is_backoff_disabled and (min_wifi_cw == 0 and max_wifi_cw == 0)

    # Generate output path based on NR-U mode and parameter combinations
    if nru_mode.lower() == "rs":
        # Reservation signal mode path
        if min_sync_slot_desync == 0 and max_sync_slot_desync == 0 and min_nru_cw > 0 and max_nru_cw > min_nru_cw:
            print(f"Done: coex_{asymmetric_prefix}rs-mode_raw-data.csv")
            return os.path.join(base_dir, f"coex_{asymmetric_prefix}rs-mode_raw-data.csv")

    elif nru_mode.lower() == "gap":
        # Gap mode paths for different parameter combinations
        if min_sync_slot_desync == 0 and max_sync_slot_desync == 0 and min_nru_cw > 0 and max_nru_cw > min_nru_cw:
            return os.path.join(base_dir, f"coex_{asymmetric_prefix}gap-mode_raw-data.csv")

        elif max_sync_slot_desync > min_sync_slot_desync:
            if is_adjusted_cw_varied:
                # Variable contention window from dynamic calculation
                return os.path.join(base_dir,
                                    f"coex_{asymmetric_prefix}gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_dynamic-cw_raw-data.csv")

            elif is_adjusted_cw_fixed:
                # Fixed contention window value
                return os.path.join(base_dir,
                                    f"coex_{asymmetric_prefix}gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_adjusted-cw-{min_wifi_cw}_raw-data.csv")

            elif is_backoff_disabled:
                # Standard backoff disabled
                return os.path.join(base_dir,
                                    f"coex_{asymmetric_prefix}gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_raw-data.csv")

            elif min_nru_cw > 0 and max_nru_cw > min_nru_cw:
                # Default gap mode with standard parameters
                return os.path.join(base_dir,
                                    f"coex_{asymmetric_prefix}gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_raw-data.csv")

    # If no path matches the parameter combination
    raise ValueError("Invalid or unsupported parameter combination.")


if __name__ == "__main__":
    changing_number_nodes()