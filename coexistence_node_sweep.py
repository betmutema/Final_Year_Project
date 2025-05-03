import shutil
import click
import csv
import os
from coexistence_simpy.coexistence_simulator import *

# This script runs multiple simulations of WiFi and NR-U coexistence, varying the number of nodes
# and collecting statistics about channel efficiency, fairness, and collision probability.
@click.command()
@click.option("--runs", default=10, help="Number of simulation runs")
@click.option("--seed", default=1, help="Seed for simulation")
@click.option("--start_node_number", type=int, required=True, help="Starting number of nodes")
@click.option("--end_node_number", type=int, required=True, help="Ending number of nodes")
@click.option("--simulation_time", default=100.0, help="Simulation duration (micro s)")
# @click.option("--min_wifi_cw", default=15, help="Wi-Fi minimum contention window")
@click.option("--min_wifi_cw", default=0, help="Wi-Fi minimum contention window")
# @click.option("--max_wifi_cw", default=63, help="Wi-Fi maximum contention window")
@click.option("--max_wifi_cw", default=0, help="Wi-Fi maximum contention window")
@click.option("--wifi_r_limit", default=3, help="Wi-Fi retry limit")
# @click.option("--min_nru_cw", default=15, help="NR-U minimum contention window")
@click.option("--min_nru_cw", default=0, help="NR-U minimum contention window")
#@click.option("--max_nru_cw", default=63, help="NR-U maximum contention window")
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
        start_node_number: int,
        end_node_number: int,
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

    For each node count between start_node_number and end_node_number,
    runs multiple simulations with the specified parameters and saves results.

    Parameters:
        runs: Number of simulation runs for each node count
        seed: Base random seed (each run increments this)
        start_node_number: Starting number of nodes to simulate
        end_node_number: Ending number of nodes to simulate (inclusive)
        simulation_time: Duration of each simulation run in seconds
        min_wifi_cw: Minimum contention window size for Wi-Fi
        max_wifi_cw: Maximum contention window size for Wi-Fi
        wifi_r_limit: Maximum number of retransmission attempts for Wi-Fi
        mcs_value: Modulation and Coding Scheme index for Wi-Fi
        min_nru_cw: Minimum contention window size for NR-U
        max_nru_cw: Maximum contention window size for NR-U
        synchronization_slot_duration: Duration of NR-U synchronization slots in μs
        max_sync_slot_desync: Maximum desynchronization offset for NR-U in μs
        min_sync_slot_desync: Minimum desynchronization offset for NR-U in μs
        nru_observation_slot: Number of observation slots for NR-U
        mcot: Maximum Channel Occupancy Time for NR-U in milliseconds
        nru_mode: NR-U operation mode ("rs" for reservation signal or "gap" for gap-based)
    """
    # Lookup table for optimal contention window values based on node count
    # Used in "variant" mode when CW parameters are set to 0
    contention_window_table = {(1, 1): 196, (2, 2): 197, (3, 3): 197, (4, 4): 183, (5, 5): 161, (6, 6): 174,
                               (7, 7): 174, (8, 8): 177}

    # Ideal Values (commented out)
    # contention_window_table = {(1, 1): 196, (2, 2): 197, (3, 3): 190, (4, 4): 190, (5, 5): 165, (6, 6): 174,
    # (7, 7): 179, (8, 8): 185}

    # Determine if we're using the "variant" mode where CW values are dynamically set from the table
    # and gap mode is enabled
    is_variant = (
            min_wifi_cw == 0 and max_wifi_cw == 0 and
            min_nru_cw == 0 and max_nru_cw == 0 and
            nru_mode.lower() == "gap"
    )

    # Determine output file path based on configuration parameters
    if is_variant:
        output_path = f"output/simulation_results/coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_adjusted-cw-Varied_raw-data.csv"
    else:
        output_path = build_output_path(
            min_sync_slot_desync,
            max_sync_slot_desync,
            nru_mode,
            min_nru_cw,
            max_nru_cw,
            min_wifi_cw,
            max_wifi_cw
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

    # Loop through each node count in the specified range
    for num_nodes in range(start_node_number, end_node_number + 1):

        # In variant mode, look up the optimal contention window value based on node count
        if is_variant:
            cw = contention_window_table.get((num_nodes, num_nodes), 63)  # Default to 63 if not found
            min_wifi_cw = max_wifi_cw = cw  # Set both min and max to the same value

        # Initialize statistics tracking dictionaries for this node count
        backoff_counts = {key: {num_nodes: 0} for key in range(max_wifi_cw + 1)}
        data_airtime_WiFi = {"WiFiStation {}".format(i): 0 for i in range(1, num_nodes + 1)}
        control_airtime_WiFi = {"WiFiStation {}".format(i): 0 for i in range(1, num_nodes + 1)}
        data_airtime_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, num_nodes + 1)}
        control_airtime_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, num_nodes + 1)}

        # Run multiple simulations with the same node count but different seeds
        for i in range(0, runs):
            curr_seed = seed + i

            # Run a single simulation with the current configuration
            simulate_coexistence(
                num_nodes,  # Equal number of WiFi and NR-U nodes
                num_nodes,
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
        max_wifi_cw: int
) -> str:
    """
    Builds an output file path based on simulation parameters.

    The filename encodes key simulation parameters to make results easily identifiable
    and to avoid overwriting previous results.

    Parameters:
        min_sync_slot_desync: Minimum synchronization slot desynchronization value
        max_sync_slot_desync: Maximum synchronization slot desynchronization value
        nru_mode: NR-U operation mode (rs or gap)
        min_nru_cw: Minimum NR-U contention window
        max_nru_cw: Maximum NR-U contention window
        min_wifi_cw: Minimum WiFi contention window
        max_wifi_cw: Maximum WiFi contention window

    Returns:
        str: Output file path for the simulation results
    """
    # Create base output directory
    base_dir = "output/simulation_results"
    os.makedirs(base_dir, exist_ok=True)

    # Determine special configuration modes
    is_backoff_disabled = (min_nru_cw == 0 and max_nru_cw == 0)
    is_adjusted_cw_fixed = is_backoff_disabled and (min_wifi_cw > 0 and min_wifi_cw == max_wifi_cw)
    is_adjusted_cw_varied = is_backoff_disabled and (min_wifi_cw == 0 and max_wifi_cw == 0)

    # Generate output path based on NR-U mode and parameter combinations
    if nru_mode.lower() == "rs":
        # Reservation signal mode path
        if min_sync_slot_desync == 0 and max_sync_slot_desync == 0 and min_nru_cw > 0 and max_nru_cw > min_nru_cw:
            print("Done: coex_rs-mode_raw-data.csv")
            return os.path.join(base_dir, "coex_rs-mode_raw-data.csv")

    elif nru_mode.lower() == "gap":
        # Gap mode paths for different parameter combinations
        if min_sync_slot_desync == 0 and max_sync_slot_desync == 0 and min_nru_cw > 0 and max_nru_cw > min_nru_cw:
            return os.path.join(base_dir, "coex_gap-mode_raw-data.csv")

        elif max_sync_slot_desync > min_sync_slot_desync:
            if is_adjusted_cw_varied:
                # Variable contention window from table
                return os.path.join(base_dir,
                                    f"coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_adjusted-cw-Varied_raw-data.csv")

            elif is_adjusted_cw_fixed:
                # Fixed contention window value
                return os.path.join(base_dir,
                                    f"coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_adjusted-cw-{min_wifi_cw}_raw-data.csv")

            elif is_backoff_disabled:
                # Standard backoff disabled
                return os.path.join(base_dir,
                                    f"coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_raw-data.csv")

            elif min_nru_cw > 0 and max_nru_cw > min_nru_cw:
                # Default gap mode with standard parameters
                return os.path.join(base_dir,
                                    f"coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_raw-data.csv")

    # If no path matches the parameter combination
    raise ValueError("Invalid or unsupported parameter combination.")

if __name__ == "__main__":
    changing_number_nodes()