import click
import csv
import os
from coexistence_simpy.coexistence_simulator import *


# This script implements a parameter sweep over contention window sizes for the coexistence
# simulation of Wi-Fi and NR-U (New Radio - Unlicensed) networks.
# The contention window is a critical parameter that controls channel access fairness.

@click.command()
# CLI options for configuring the parameter sweep
@click.option("--cw_start", default=32, show_default=True, help="Starting CW value")
@click.option("--cw_end", default=512, show_default=True, help="Ending CW value")
@click.option('--cw_step', default=48, show_default=True, help='Step size for CW values')
@click.option('--runs', default=10, show_default=True, help='Number of simulation runs per CW value')
@click.option('--ap_number', default=2, show_default=True, help='Number of Wi-Fi APs')
@click.option('--gnb_number', default=2, show_default=True, help='Number of NR-U gNBs')
@click.option("--simulation_time", default=100.0, help="Simulation duration (s)")
@click.option("--min_nru_cw", default=0, show_default=True, help="NR-U minimum contention window")
@click.option("--max_nru_cw", default=0, show_default=True, help="NR-U maximum contention window")
@click.option("--synchronization_slot_duration", default=1000, show_default=True,
              help="Synchronization slot duration (μs)")
@click.option("--min_sync_slot_desync", default=0, show_default=True,
              help="Minimum synchronization slot desynchronization")
@click.option("--max_sync_slot_desync", default=1000, show_default=True,
              help="Maximum synchronization slot desynchronization")
@click.option("--nru_mode", type=click.Choice(["gap", "rs"], case_sensitive=False), default="gap",
              help="NR-U mode: 'rs' for reservation signal mode, 'gap' for gap-based mode")

def cw_sweep_simulation(
        cw_start,  # Starting contention window value for the sweep
        cw_end,  # Ending contention window value for the sweep
        cw_step,  # Step size for contention window values
        runs,  # Number of simulation runs per CW value
        ap_number,  # Number of Wi-Fi access points
        gnb_number,  # Number of NR-U gNodeBs
        simulation_time,  # Duration of each simulation
        min_nru_cw,  # Minimum contention window for NR-U
        max_nru_cw,  # Maximum contention window for NR-U
        synchronization_slot_duration,  # Duration of NR-U sync slots
        min_sync_slot_desync,  # Minimum sync slot desynchronization
        max_sync_slot_desync,  # Maximum sync slot desynchronization
        nru_mode  # NR-U operational mode (gap or reservation signal)
):
    """
    Performs a parameter sweep over contention window sizes to evaluate
    coexistence performance between Wi-Fi and NR-U networks.

    For each contention window value, this function runs multiple simulations
    with different random seeds to gather statistically significant results.
    """

    # Define output file path with descriptive filename based on parameters
    SWEEP_OUTPUT_FILE = f"output/simulation_results/airtime_fairness_{cw_start}_{cw_end}_{cw_step}_{ap_number}_{gnb_number}.csv"
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(SWEEP_OUTPUT_FILE), exist_ok=True)

    # Initialize the output CSV file with header row
    with open(SWEEP_OUTPUT_FILE, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "CW", "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency", "jain's_fairness_index", "joint_airtime_fairness"
        ])

    # Loop through the contention window range with specified step size
    for cw in range(cw_start, cw_end + 1, cw_step):
        click.echo(f"\nRunning simulations for Wi-Fi CWmin = CWmax = {cw}")
        # For each CW value, run multiple simulations with different random seeds
        for seed in range(runs):
            # Use a temporary file for the simulation output
            TEMP_OUTPUT_FILE = "output/simulation_results/temp_results.csv"

            # Run a single simulation with the current parameters
            simulate_coexistence(
                ap_number,  # Number of Wi-Fi access points
                gnb_number,  # Number of NR-U base stations
                seed,  # Random seed for reproducibility
                simulation_time,  # Duration of simulation in seconds
                WiFiConfig(1472, cw, cw, 7, 7),  # Wi-Fi config with current CW value
                NRUConfig(16, 9, synchronization_slot_duration,
                          max_sync_slot_desync, min_sync_slot_desync,
                          3, min_nru_cw, max_nru_cw, 6),  # NR-U configuration
                {key: {ap_number: 0} for key in range(cw + 1)},  # Backoff counters
                {f"WiFiStation {i}": 0 for i in range(1, ap_number + 1)},  # Wi-Fi data airtime
                {f"WiFiStation {i}": 0 for i in range(1, ap_number + 1)},  # Wi-Fi control airtime
                {f"NRUBaseStation {i}": 0 for i in range(1, gnb_number + 1)},  # NR-U data airtime
                {f"NRUBaseStation {i}": 0 for i in range(1, gnb_number + 1)},  # NR-U control airtime
                nru_mode,  # NR-U operational mode
                TEMP_OUTPUT_FILE  # Temporary output file
            )

            # Process the simulation results from the temporary file
            with open(TEMP_OUTPUT_FILE, 'r') as temp_file:
                lines = temp_file.readlines()
                if lines:
                    # Extract the last line which contains the final simulation metrics
                    last_line = lines[-1].strip().split(',')
                    # Append CW value and metrics to the final output CSV
                    with open(SWEEP_OUTPUT_FILE, mode='a', newline='') as out_file:
                        writer = csv.writer(out_file)
                        writer.writerow([cw] + last_line[1:])  # Add CW as first column

            # Remove the temporary file after processing
            os.remove(TEMP_OUTPUT_FILE)


if __name__ == "__main__":
    cw_sweep_simulation()  # Execute the script when run directly