import click  # Import Click library for creating command-line interfaces
import csv  # Import CSV module for file operations
import os  # Import OS module for file/directory operations
from coexistence_simpy.coexistence_simulator import *  # Import all functions from the simulator module

@click.command()  # Define a Click command line interface
# Define command-line options with default values and help text
@click.option("--runs", default=10, help="Number of simulation runs")
@click.option("--seed", default=1, help="Seed for random number generation to ensure reproducibility")
@click.option("--start_node_number", type=int, default=1, help="Starting number of Wi-Fi nodes")
@click.option("--end_node_number", type=int, default=10, help="Ending number of Wi-Fi nodes")
@click.option("--simulation_time", default=100.0, help="Duration of the simulation per stations number (s)")
@click.option("--min_wifi_cw", default=15, help="Wi-Fi minimum contention window size")
@click.option("--max_wifi_cw", default=63, help="Wi-Fi maximum contention window size")
@click.option("--wifi_r_limit", default=3, help="Wi-Fi retry limit for failed transmissions")
@click.option("--mcs_value", default=7, help="Value of MCS (Modulation and Coding Scheme) - affects data rate")
@click.option("--wifi_tx_time", default=0.002, help="Wi-Fi transmission time in seconds (2ms default)")

def changing_number_nodes(
        runs: int,  # Number of simulation runs for statistical significance
        seed: int,  # Base seed for random number generation
        start_node_number: int,  # Starting number of Wi-Fi nodes to simulate
        end_node_number: int,  # Final number of Wi-Fi nodes to simulate
        simulation_time: float,  # Duration of each simulation run in seconds
        min_wifi_cw: int,  # Minimum contention window for Wi-Fi (default: 15)
        max_wifi_cw: int,  # Maximum contention window for Wi-Fi (default: 63)
        wifi_r_limit: int,  # Maximum number of retransmissions for Wi-Fi
        mcs_value: int,  # Modulation and Coding Scheme value
        wifi_tx_time: float,  # Duration of Wi-Fi transmissions
):
    """
    Run Wi-Fi-only simulations with varying numbers of nodes.

    This function conducts a parameter sweep by increasing the number of Wi-Fi nodes
    from start_node_number to end_node_number, running multiple simulations for each
    configuration to collect statistically significant performance metrics.
    """

    # Dynamically construct output file path based on node range
    output_filename = f"wifi-only_nodes-{start_node_number}-{end_node_number}_raw-data.csv"
    output_dir = "output/simulation_results"
    os.makedirs(output_dir, exist_ok=True)  # Create output directory if it doesn't exist
    output_file_path = os.path.join(output_dir, output_filename)

    # Prepare output CSV file with header row
    with open(output_file_path, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency", "jain's_fairness_index", "joint airtime fairness"
        ])

    # Disable NR-U by setting node count to 0 (this is a Wi-Fi-only simulation)
    nru_node_number = 0

    # Iterate through different numbers of Wi-Fi nodes
    for wifi_num_nodes in range(start_node_number, end_node_number + 1):
        # Initialize backoff tracking structure - used to collect statistics on backoff distribution
        # Only tracking up to max_wifi_cw values for each node
        backoff_counts = {key: {wifi_num_nodes: 0} for key in range(max_wifi_cw + 1)}

        # Initialize airtime tracking dictionaries for Wi-Fi nodes
        # These dictionaries will accumulate airtime usage across simulation runs
        data_airtime_WiFi = {"WiFiStation {}".format(i): 0 for i in range(1, wifi_num_nodes + 1)}
        control_airtime_WiFi = {"WiFiStation {}".format(i): 0 for i in range(1, wifi_num_nodes + 1)}

        # Empty NR-U structures (not used in this simulation but required by simulator interface)
        airtime_data_NR = {}
        airtime_control_NR = {}

        # Run multiple simulations with different random seeds
        for i in range(runs):
            curr_seed = seed + i  # Increment seed for each run to ensure statistical variation

            # Call the simulator with the current configuration
            simulate_coexistence(
                wifi_num_nodes,  # Current number of Wi-Fi nodes being tested
                nru_node_number,  # No NR-U nodes in this Wi-Fi-only simulation
                curr_seed,  # Random seed for this specific run
                simulation_time,  # Duration of the simulation
                WiFiConfig(  # Active Wi-Fi configuration
                    wifi_tx_time,  # Transmission time (default: 2ms)
                    min_wifi_cw,  # Minimum contention window
                    max_wifi_cw,  # Maximum contention window
                    wifi_r_limit,  # Retry limit for failed transmissions
                    mcs_value,  # MCS (Modulation and Coding Scheme) value
                ),
                NRUConfig(  # Dummy NR-U configuration (unused but required)
                    16,  # OFDM symbols per slot
                    9,  # Slots per subframe
                    1000,  # Subframe duration in µs
                    1000,  # Frame duration in µs
                    0,  # Frame timing offset (0 means synchronized)
                    3,  # Number of observation slots
                    15,  # Minimum contention window
                    63,  # Maximum contention window
                    6  # Maximum Channel Occupancy Time
                ),
                backoff_counts,  # Reference to backoff tracking structure
                data_airtime_WiFi,  # Reference to Wi-Fi data airtime tracking
                control_airtime_WiFi,  # Reference to Wi-Fi control airtime tracking
                airtime_data_NR,  # Reference to NR-U data airtime tracking (unused)
                airtime_control_NR,  # Reference to NR-U control airtime tracking (unused)
                "gap",  # LBT mode (not relevant in Wi-Fi-only simulation)
                output_path=output_file_path  # Path to save results
            )

if __name__ == "__main__":
    changing_number_nodes()  # Execute the Click command when script is run directly