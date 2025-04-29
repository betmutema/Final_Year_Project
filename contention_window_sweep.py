import click
import csv
import os
from coexistence_simpy.coexistence_simulator import *

@click.command()
@click.option("--cw_start", default=32, show_default=True, help="Starting CW value")
@click.option("--cw_end", default=512, show_default=True, help="Ending CW value")
@click.option('--cw_step', default=48, show_default=True, help='Step size for CW values')
@click.option('--runs', default=10, show_default=True, help='Number of simulation runs per CW value')
@click.option('--ap_number', default=2, show_default=True, help='Number of Wi-Fi APs')
@click.option('--gnb_number', default=2, show_default=True, help='Number of NR-U gNBs')
@click.option("--simulation_time", default=100.0, help="Simulation duration (s)")
@click.option("--min_nru_cw", default=0, show_default=True, help="NNR-U minimum contention window")
@click.option("--max_nru_cw", default=0, show_default=True, help="NR-U maximum contention window")
@click.option("--synchronization_slot_duration", default=1000, show_default=True, help="Synchronization slot duration (μs)")
@click.option("--min_sync_slot_desync", default=0, show_default=True, help="Minimum synchronization slot desynchronization")
@click.option("--max_sync_slot_desync", default=1000, show_default=True, help="Maximum synchronization slot desynchronization")
@click.option("--nru_mode", type=click.Choice(["gap", "rs"], case_sensitive=False), default="gap",
              help="NR-U mode: 'rs' for reservation signal mode, 'gap' for gap-based mode")

def cw_sweep_simulation(
                        cw_start,
                        cw_end,
                        cw_step,
                        runs,
                        ap_number,
                        gnb_number,
                        simulation_time,
                        min_nru_cw,
                        max_nru_cw,
                        synchronization_slot_duration,
                        min_sync_slot_desync,
                        max_sync_slot_desync,
                        nru_mode
                    ):

    SWEEP_OUTPUT_FILE = f"output/simulation_results/airtime_fairness_{cw_start}_{cw_end}_{cw_step}_{ap_number}_{gnb_number}.csv"
    os.makedirs(os.path.dirname(SWEEP_OUTPUT_FILE), exist_ok=True)

    # Prepare output CSV
    with open(SWEEP_OUTPUT_FILE, mode='w', newline='') as out_file:
        writer = csv.writer(out_file)
        writer.writerow([
            "CW", "simulation_seed", "wifi_node_count", "nru_node_count",
            "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
            "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability",
            "total_channel_occupancy", "total_network_efficiency"
        ])

    for cw in range(cw_start, cw_end + 1, cw_step):
        click.echo(f"\nRunning simulations for Wi-Fi CWmin = CWmax = {cw}")
        for seed in range(runs):
            # Use a temporary file to avoid errors
            TEMP_OUTPUT_FILE = "output/simulation_results/temp_results.csv"

            # Run simulation
            simulate_coexistence(
                ap_number,
                gnb_number,
                seed,
                simulation_time,
                WiFiConfig(1472, cw, cw, 7, 7),
                NRUConfig(16, 9, synchronization_slot_duration,
                          max_sync_slot_desync, min_sync_slot_desync,
                          3, min_nru_cw, max_nru_cw, 6),
                {key: {ap_number: 0} for key in range(cw + 1)},
                {f"WiFiStation {i}": 0 for i in range(1, ap_number + 1)},
                {f"WiFiStation {i}": 0 for i in range(1, ap_number + 1)},
                {f"NRUBaseStation {i}": 0 for i in range(1, gnb_number + 1)},
                {f"NRUBaseStation {i}": 0 for i in range(1, gnb_number + 1)},
                nru_mode,
                TEMP_OUTPUT_FILE  # Use temporary file
            )

            # Read from temporary file and append CW
            with open(TEMP_OUTPUT_FILE, 'r') as temp_file:
                lines = temp_file.readlines()
                if lines:
                    last_line = lines[-1].strip().split(',')
                    # Append CW and write to final CSV
                    with open(SWEEP_OUTPUT_FILE, mode='a', newline='') as out_file:
                        writer = csv.writer(out_file)
                        writer.writerow([cw] + last_line[1:])  # Add CW as first column

            # Clean up temporary file
            os.remove(TEMP_OUTPUT_FILE)

if __name__ == "__main__":
    cw_sweep_simulation()
