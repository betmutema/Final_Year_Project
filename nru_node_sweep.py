import click  # Import Click library for creating command-line interfaces
import csv  # Import CSV module for file operations
import os  # Import OS module for file/directory operations
from coexistence_simpy.coexistence_simulator import *  # Import all functions from the simulator module

@click.command()  # Define a Click command line interface
# Define command-line options with default values and help text
@click.option("--runs", default=10, help="Number of simulation runs")
@click.option("--seed", default=1, help="Seed for random number generation to ensure reproducibility")
@click.option("--start_node_number", type=int, default=1, help="Starting number of NR-U nodes")
@click.option("--end_node_number", type=int, default=10, help="Ending number of NR-U nodes")
@click.option("--simulation_time", default=100.0, help="Simulation duration in seconds")
@click.option("--min_nru_cw", default=15, help="NR-U minimum contention window size")
@click.option("--max_nru_cw", default=63, help="NR-U maximum contention window size")
@click.option("--nru_observation_slot", default=3, help="Number of NR-U observation slots")
@click.option("--mcot", default=6, help="Maximum Channel Occupancy Time in milliseconds")
@click.option("--nru_mode", type=click.Choice(["gap", "rs"], case_sensitive=False), default="gap",
              help="NR-U mode: 'rs' for reservation signal mode, 'gap' for gap-based mode")

def changing_number_nodes(
        runs: int,  # Number of simulation runs for statistical significance
        seed: int,  # Base seed for random number generation
        start_node_number: int,  # Starting number of NR-U nodes to simulate
        end_node_number: int,  # Final number of NR-U nodes to simulate
        simulation_time: float,  # Duration of each simulation run
        min_nru_cw: int,  # Minimum contention window for NR-U
        max_nru_cw: int,  # Maximum contention window for NR-U
        nru_observation_slot: int,  # NR-U observation slots for channel sensing
        mcot: int,  # Maximum Channel Occupancy Time in ms
        nru_mode: str,  # NR-U LBT mode: gap-based or reservation signal
):
    """
    Run NR-U-only simulations with varying numbers of nodes.

    This function conducts a parameter sweep by increasing the number of NR-U nodes
    from start_node_number to end_node_number, running multiple simulations for each
    configuration to collect statistically significant performance metrics.
    """

    # Set output file path based on NR-U mode
    if nru_mode.lower() == "rs":
        OUTPUT_FILE_PATH = "output/simulation_results/nru-only_rs-mode_raw-data.csv"
    elif nru_mode.lower() == "gap":
        OUTPUT_FILE_PATH = "output/simulation_results/nru-only_gap-mode_raw-data.csv"
    else:
        raise ValueError(f"Invalid NR-U mode: {nru_mode}")

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(OUTPUT_FILE_PATH), exist_ok=True)

    # Initialize CSV output file with header row
    with open(OUTPUT_FILE_PATH, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency", "jain's_fairness_index", "joint airtime fairness"
        ])

    # Set Wi-Fi parameters to zero/minimal values since this is an NR-U-only simulation
    wifi_node_number = 0  # No Wi-Fi nodes in this simulation
    min_wifi_cw = 1  # Minimal dummy value for Wi-Fi contention window
    max_wifi_cw = 1  # Minimal dummy value for Wi-Fi contention window

    # Iterate through different numbers of NR-U nodes
    for nru_node_number in range(start_node_number, end_node_number + 1):
        # Initialize backoff tracking structure - used to collect statistics on backoff distribution
        max_backoff = max(max_nru_cw, max_wifi_cw)
        backoff_counts = {key: {n: 0 for n in range(end_node_number + 1)} for key in range(max_nru_cw + 1)}

        # Initialize airtime tracking dictionaries for NR-U nodes
        # These dictionaries will accumulate airtime usage across simulation runs
        airtime_data_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, nru_node_number + 1)}
        airtime_control_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, nru_node_number + 1)}

        # Empty Wi-Fi structures (not used in this simulation but required by simulator interface)
        data_airtime_WiFi = {}
        control_airtime_WiFi = {}

        # Run multiple simulations with different random seeds
        for i in range(runs):
            curr_seed = seed + i  # Increment seed for each run to ensure statistical variation

            # Call the simulator with the current configuration
            simulate_coexistence(
                wifi_node_number,  # No Wi-Fi nodes in this NR-U-only simulation
                nru_node_number,  # Current number of NR-U nodes being tested
                curr_seed,  # Random seed for this specific run
                simulation_time,  # Duration of the simulation
                WiFiConfig(  # Dummy Wi-Fi configuration (unused but required)
                    0.000001,  # 1µs TX time (minimal)
                    min_wifi_cw,  # Minimum contention window (dummy value)
                    max_wifi_cw,  # Maximum contention window (dummy value)
                    0,  # No retries
                    0  # MCS=0 (lowest data rate)
                ),
                NRUConfig(  # Active NR-U configuration
                    16,  # OFDM symbols per slot
                    9,  # Slots per subframe
                    1000,  # Subframe duration in µs
                    1000,  # Frame duration in µs
                    0,  # Frame timing offset (0 means synchronized)
                    nru_observation_slot,  # Number of observation slots
                    min_nru_cw,  # Minimum contention window
                    max_nru_cw,  # Maximum contention window
                    mcot  # Maximum Channel Occupancy Time
                ),
                backoff_counts,  # Reference to backoff tracking structure
                data_airtime_WiFi,  # Reference to Wi-Fi data airtime tracking (unused)
                control_airtime_WiFi,  # Reference to Wi-Fi control airtime tracking (unused)
                airtime_data_NR,  # Reference to NR-U data airtime tracking
                airtime_control_NR,  # Reference to NR-U control airtime tracking
                nru_mode,  # LBT mode: gap-based or reservation signal
                output_path=OUTPUT_FILE_PATH  # Path to save results
            )

if __name__ == "__main__":
    changing_number_nodes()  # Execute the Click command when script is run directly