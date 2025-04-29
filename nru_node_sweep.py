import click
import csv
import os
from coexistence_simpy.coexistence_simulator import *

@click.command()
@click.option("--runs", default=10, help="Number of simulation runs")
@click.option("--seed", default=1, help="Seed for simulation")
@click.option("--start_node_number", type=int, default=1, help="Starting number of NR-U nodes")
@click.option("--end_node_number", type=int, default=10, help="Ending number of NR-U nodes")
@click.option("--simulation_time", default=100.0, help="Simulation duration (s)")
@click.option("--min_nru_cw", default=15, help="NR-U minimum contention window")
@click.option("--max_nru_cw", default=63, help="NR-U maximum contention window")
@click.option("--nru_observation_slot", default=3, help="NR-U observation slots")
@click.option("--mcot", default=6, help="Maximum Channel Occupancy Time (ms)")
@click.option("--nru_mode", type=click.Choice(["gap", "rs"], case_sensitive=False), default="gap",
              help="NR-U mode: 'rs' for reservation signal mode, 'gap' for gap-based mode")

def changing_number_nodes(
        runs: int,
        seed: int,
        start_node_number: int,
        end_node_number: int,
        simulation_time: float,
        min_nru_cw: int,
        max_nru_cw: int,
        nru_observation_slot: int,
        mcot: int,
        nru_mode: str,
):

    if nru_mode.lower() == "rs":
        OUTPUT_FILE_PATH = "output/simulation_results/nru-only_rs-mode_raw-data.csv"
    elif nru_mode.lower() == "gap":
        OUTPUT_FILE_PATH = "output/simulation_results/nru-only_gap-mode_raw-data.csv"
    else:
        raise ValueError(f"Invalid NR-U mode: {nru_mode}")

    # Prepare output CSV
    os.makedirs(os.path.dirname(OUTPUT_FILE_PATH), exist_ok=True)

    with open(OUTPUT_FILE_PATH, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency"
        ])

    # Disable Wi-Fi completely but satisfy simulation structure
    wifi_node_number = 0
    min_wifi_cw = 1  # Minimal dummy value
    max_wifi_cw = 1  # Minimal dummy value

    for nru_node_number in range(start_node_number, end_node_number + 1):
        # Initialize combined backoff structure
        max_backoff = max(max_nru_cw, max_wifi_cw)

        backoff_counts = {key: {n: 0 for n in range(end_node_number + 1)} for key in range(max_nru_cw + 1)}

        # NR-U tracking
        airtime_data_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, nru_node_number + 1)}
        airtime_control_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, nru_node_number + 1)}

        # Empty Wi-Fi structures
        data_airtime = {}
        control_airtime = {}

        for i in range(runs):
            curr_seed = seed + i
            simulate_coexistence(
                wifi_node_number,
                nru_node_number,
                curr_seed,
                simulation_time,
                WiFiConfig(  # Dummy Wi-Fi config
                    0.000001,  # 1µs TX time
                    min_wifi_cw,
                    max_wifi_cw,
                    0,  # No retries
                    0  # MCS=0
                ),
                NRUConfig(  # Active NR-U config
                    16, 9, 1000, 1000, 0,
                    nru_observation_slot, min_nru_cw, max_nru_cw, mcot
                ),
                backoff_counts,
                data_airtime,
                control_airtime,
                airtime_data_NR,
                airtime_control_NR,
                nru_mode,
                output_path = OUTPUT_FILE_PATH
            )

if __name__ == "__main__":
    changing_number_nodes()