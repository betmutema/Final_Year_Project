import click
import csv
import os
from coexistence_simpy.coexistence_simulator import *

@click.command()
@click.option("--runs", default=10, help="Number of simulation runs")
@click.option("--seed", default=1, help="Seed for simulation")
@click.option("--start_node_number", type=int, default=1, help="Starting number of Wi-Fi nodes")
@click.option("--end_node_number", type=int, default=10, help="Ending number of Wi-Fi nodes")
@click.option("--simulation_time", default=100.0, help="Duration of the simulation per stations number (s)")
@click.option("--min_wifi_cw", default=15, help="Wi-Fi minimum contention window")
@click.option("--max_wifi_cw", default=63, help="Wi-Fi maximum contention window")
@click.option("--wifi_r_limit", default=3, help="Wi-Fi retry limit")
@click.option("--mcs_value", default=7, help="Value of mcs")
@click.option("--wifi_tx_time", default=0.002, help="Wi-Fi transmission time in (s)")

def changing_number_nodes(
        runs: int,
        seed: int,
        start_node_number: int,
        end_node_number: int,
        simulation_time: float,
        min_wifi_cw: int,
        max_wifi_cw: int,
        wifi_r_limit: int,
        mcs_value: int,
        wifi_tx_time: float,
):
    # Dynamically construct output file path
    output_filename = f"wifi-only_nodes-{start_node_number}-{end_node_number}_raw-data.csv"
    output_dir = "output/simulation_results"
    os.makedirs(output_dir, exist_ok=True)
    output_file_path = os.path.join(output_dir, output_filename)

    # Prepare output CSV
    with open(output_file_path, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency"
        ])

    # Disable NR-U by setting NR-U node count to 0
    nru_node_number = 0

    for wifi_num_nodes in range(start_node_number, end_node_number + 1):
        backoff_counts = {key: {wifi_num_nodes: 0} for key in range(max_wifi_cw + 1)}
        data_airtime = {"WiFiStation {}".format(i): 0 for i in range(1, wifi_num_nodes + 1)}
        control_airtime = {"WiFiStation {}".format(i): 0 for i in range(1, wifi_num_nodes + 1)}

        # NR-U airtime variables (empty since NR-U is disabled)
        airtime_data_NR = {}
        airtime_control_NR = {}

        for i in range(runs):
            curr_seed = seed + i
            simulate_coexistence(
                wifi_num_nodes,
                nru_node_number,  # NR-U nodes = 0 (Wi-Fi-only)
                curr_seed,
                simulation_time,
                WiFiConfig(
                    wifi_tx_time,  # Transmission time (2ms)
                    min_wifi_cw,  # CWmin = 15
                    max_wifi_cw,  # CWmax = 63
                    wifi_r_limit,  # Retry limit = 3
                    mcs_value,  # MCS = 7
                ),
                NRUConfig(  # NR-U config (ignored since nru_node_number=0)
                    16, 9, 1000, 1000, 0, 3, 15, 63, 6
                ),
                backoff_counts,
                data_airtime,
                control_airtime,
                airtime_data_NR,
                airtime_control_NR,
                "gap",
                output_path = output_file_path
            )

if __name__ == "__main__":
    changing_number_nodes()