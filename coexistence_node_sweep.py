import shutil
import click
import csv
import os
from coexistence_simpy.coexistence_simulator import *

# set default values to give you the best coexistence results
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
    contention_window_table = {(1, 1): 196, (2, 2): 197, (3, 3): 197, (4, 4): 183, (5, 5): 161, (6, 6): 174,
                              (7, 7): 174, (8, 8): 177}

    # Ideal Values
    # contention_window_table = {(1, 1): 196, (2, 2): 197, (3, 3): 190, (4, 4): 190, (5, 5): 165, (6, 6): 174,
                               # (7, 7): 179, (8, 8): 185}

    is_variant = (
            min_wifi_cw == 0 and max_wifi_cw == 0 and
            min_nru_cw == 0 and max_nru_cw == 0 and
            nru_mode.lower() == "gap"
    )

    # If variant, use custom CW from table and override CW min/max
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

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency"
        ])

    for num_nodes in range(start_node_number, end_node_number + 1):

        if is_variant:
            cw = contention_window_table.get((num_nodes, num_nodes), 63)
            min_wifi_cw = max_wifi_cw = cw

        backoff_counts = {key: {num_nodes: 0} for key in range(max_wifi_cw + 1)}
        data_airtime = {"WiFiStation {}".format(i): 0 for i in range(1, num_nodes + 1)}
        control_airtime = {"WiFiStation {}".format(i): 0 for i in range(1, num_nodes + 1)}
        airtime_data_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, num_nodes + 1)}
        airtime_control_NR = {"NRUBaseStation {}".format(i): 0 for i in range(1, num_nodes + 1)}

        for i in range(0, runs):
            curr_seed = seed + i
            simulate_coexistence(num_nodes,
                           num_nodes,
                           curr_seed,
                           simulation_time,
                           WiFiConfig(1472, min_wifi_cw, max_wifi_cw, wifi_r_limit, mcs_value),
                           NRUConfig(16, 9, synchronization_slot_duration, max_sync_slot_desync,
                                     min_sync_slot_desync, nru_observation_slot, min_nru_cw, max_nru_cw, mcot),
                           backoff_counts,
                           data_airtime,
                           control_airtime,
                           airtime_data_NR,
                           airtime_control_NR,
                           nru_mode,
                           output_path
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

    base_dir = "output/simulation_results"
    os.makedirs(base_dir, exist_ok=True)

    is_backoff_disabled = (min_nru_cw == 0 and max_nru_cw == 0)
    is_adjusted_cw_fixed = is_backoff_disabled and (min_wifi_cw > 0 and min_wifi_cw == max_wifi_cw)
    is_adjusted_cw_varied = is_backoff_disabled and (min_wifi_cw == 0 and max_wifi_cw == 0)

    if nru_mode.lower() == "rs":
        if min_sync_slot_desync == 0 and max_sync_slot_desync == 0 and min_nru_cw > 0 and max_nru_cw > min_nru_cw:
            print("Done: coex_rs-mode_raw-data.csv")
            return os.path.join(base_dir, "coex_rs-mode_raw-data.csv")

    elif nru_mode.lower() == "gap":
        if min_sync_slot_desync == 0 and max_sync_slot_desync == 0 and min_nru_cw > 0 and max_nru_cw > min_nru_cw:
            return os.path.join(base_dir, "coex_gap-mode_raw-data.csv")

        elif max_sync_slot_desync > min_sync_slot_desync:
            if is_adjusted_cw_varied:
                return os.path.join(base_dir,
                    f"coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_adjusted-cw-Varied_raw-data.csv")

            elif is_adjusted_cw_fixed:
                return os.path.join(base_dir,
                    f"coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_adjusted-cw-{min_wifi_cw}_raw-data.csv")

            elif is_backoff_disabled:
                return os.path.join(base_dir,
                    f"coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_disabled-backoff_raw-data.csv")

            elif min_nru_cw > 0 and max_nru_cw > min_nru_cw:
                return os.path.join(base_dir,
                    f"coex_gap-mode_desync-{min_sync_slot_desync}-{max_sync_slot_desync}_raw-data.csv")

    raise ValueError("Invalid or unsupported parameter combination.")

if __name__ == "__main__":
    changing_number_nodes()