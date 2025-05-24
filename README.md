# 5G NR-U and Wi-Fi Coexistence Simulator

## Overview

This project provides a SimPy-based discrete-event simulation framework designed to investigate the complex interactions between 5G New Radio Unlicensed (NR-U) and Wi-Fi systems operating in shared spectrum bands. The primary goal is to model, evaluate, and optimize coexistence strategies to mitigate interference and ensure equitable, efficient resource sharing.

The simulator models key channel access mechanisms, including:
-   **Wi-Fi**: Distributed Coordination Function (DCF) with CSMA/CA and binary exponential backoff.
-   **5G NR-U**: Listen-Before-Talk (LBT) based access, supporting both "Gap Mode" and "Reservation Signal (RS) Mode".

It allows for the systematic analysis of various optimization techniques, such as NR-U gNB desynchronization, disabling NR-U's random backoff, and adaptive Wi-Fi Contention Window (CW) adjustments based on network density.

## Features

-   **Detailed MAC Layer Modeling**: Simulates Wi-Fi DCF and 5G NR-U LBT (Gap and RS modes) behaviors.
-   **Parameter Sweeps**: Systematically varies node counts (symmetric and asymmetric), Wi-Fi Contention Window (CW) sizes, and NR-U synchronization parameters.
-   **Coexistence Strategies**: Evaluates multiple strategies including baseline modes, NR-U desynchronization, NR-U backoff modifications, and dynamic/fixed Wi-Fi CW adjustments.
-   **Comprehensive Metrics**: Measures key performance indicators such as Channel Occupancy, Channel Efficiency, Collision Probability, Jain's Fairness Index (JFI), and Joint Airtime Fairness.
-   **Flexible Configuration**: CLI-driven simulations allow for easy customization of parameters like CW ranges, retry limits, Modulation and Coding Schemes (MCS), MCOT, etc.
-   **Automated Visualization**: Includes Python scripts to process raw simulation data (CSV) and generate a wide range of comparative plots and visualizations.

## How the Simulator Works

The core of the simulator is built using **SimPy**, a process-based discrete-event simulation library in Python.
-   **`coexistence_simpy/coexistence_simulator.py`**: Contains the main simulation engine.
    -   `WirelessMedium`: Manages the shared channel, detects collisions, and aggregates statistics.
    -   `WiFiStation`: Models a Wi-Fi device implementing DCF.
    -   `NRUBaseStation`: Models an NR-U gNB implementing LBT (configurable for Gap or RS mode).
-   Packets/transmissions are generated, contend for the channel, and their outcomes (success/collision) are recorded along with airtime usage.
-   Randomness is incorporated via Python's `random` module, with seeds for reproducibility.

## Key Simulation Scripts

The project is organized into several Python scripts for running simulations and analyzing results:

-   **Simulation Runners (`*_sweep.py`)**:
    -   `coexistence_node_sweep.py`: Sweeps the number of Wi-Fi and NR-U nodes (symmetric) for various coexistence scenarios. Can dynamically find optimal Wi-Fi CW.
    -   `coexistence_asymetric_node_sweep.py`: Sweeps asymmetric Wi-Fi and NR-U node configurations. Can dynamically find optimal Wi-Fi CW per pair.
    -   `contention_window_sweep.py`: Sweeps Wi-Fi CW values for fixed node counts, used for optimal CW analysis.
-   **Analysis and Visualization (`analyze_*.py`, `visualize_*.py`)**:
    -   These scripts parse the CSV output from simulations to generate various plots comparing performance across different scenarios and parameters.

## Key Metrics Evaluated

-   **Channel Occupancy**: The proportion of time a technology (Wi-Fi or NR-U) uses the shared radio channel.
-   **Channel Efficiency**: The proportion of time spent transmitting actual user data, excluding overhead.
-   **Collision Probability**: The likelihood that transmission attempts from different nodes overlap and result in a collision.
-   **Jain's Fairness Index (JFI)**: Measures the fairness of airtime distribution between Wi-Fi and NR-U (1.0 indicates perfect fairness).
-   **Joint Airtime Fairness**: Combines JFI with total channel utilization to provide a holistic view of both fairness and efficiency.

## Investigated Coexistence Strategies & Scenarios

The simulator is used to evaluate the impact of:
-   Baseline NR-U RS Mode vs. Default Gap Mode.
-   NR-U gNB Desynchronization: Staggering NR-U LBT attempts.
-   Disabling NR-U Random Backoff: Forcing NR-U to transmit immediately after its gap period if the channel is clear.
-   Fixed Wi-Fi CW Adjustment: Using a predetermined, globally adjusted CW for Wi-Fi.
-   Dynamic Wi-Fi CW Adjustment: Adaptively setting the Wi-Fi CW based on the current density of Wi-Fi and NR-U nodes (for both symmetric and asymmetric configurations).
-   Performance of the fully Optimized Gap Mode (desynchronization + no NR-U backoff + dynamic Wi-Fi CW) compared to RS Mode.

## Directory Structure

```text
├── coexistence_simpy/
│   ├── coexistence_simulator.py  # Core simulation logic
│   ├── radio_parameters.py       # Radio PHY/MAC parameters
│   └── __init__.py
├── output/
│   ├── simulation_results/       # Raw CSV data from simulations
│   ├── metrics_visualizations/   # Generated plots from most visualization scripts
│   └── plots/                    # Generated plots from visualize_asymetric_network_metrics.py
├── analyze_simulation_results.py # Script for comprehensive comparative analysis
├── coexistence_node_sweep.py     # Main script for symmetric node sweeps
├── coexistence_asymetric_node_sweep.py # Main script for asymmetric node sweeps
├── contention_window_sweep.py  # Script for Wi-Fi CW sweeps
├── visualize_asymetric_network_metrics.py # Visualization for asymmetric results
├── visualize_cw_impact.py        # Visualization for CW sweep impact
├── visualize_fairness.py         # Visualization for fairness metrics
├── visualize_network_metrics.py  # Visualization for general network metrics
├── README.md                     # This file
└── requirements.txt              # Python dependencies
```
## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/betmutema/Final_Year_Project.git
    cd Final_Year_Project
    ```
   *(Note: Adjusted to your GitHub username and likely repo name based on the thesis)*

2.  **Create a virtual environment (recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    If `requirements.txt` is not present, you can install manually:
    ```bash
    pip install simpy pandas matplotlib click scipy
    ```

## Usage

### Running Simulations

Simulations are run from the command line. Here are some examples:

1.  **Sweep Wi-Fi/NR-U Nodes (Symmetric Coexistence with Optimized Gap Mode - Dynamic CW):**
    This is a common scenario for the "Optimized Gap Mode" where CW is dynamically determined.
    The `--min_wifi_cw 0 --max_wifi_cw 0` flags trigger dynamic CW calculation in `coexistence_node_sweep.py` when `nru_mode` is `gap` and NR-U CWs are also 0.
    ```bash
    python coexistence_node_sweep.py --start_node_number 1 --end_node_number 8 --nru_mode gap --min_sync_slot_desync 0 --max_sync_slot_desync 1000 --min_nru_cw 0 --max_nru_cw 0 --min_wifi_cw 0 --max_wifi_cw 0
    ```
    
2.  **Sweep Asymmetric Wi-Fi/NR-U Nodes (Optimized Gap Mode - Dynamic CW per pair):**
    ```bash
    python coexistence_asymetric_node_sweep.py --num_pairs 8 --nru_mode gap --min_sync_slot_desync 0 --max_sync_slot_desync 1000 --min_nru_cw 0 --max_nru_cw 0 --min_wifi_cw 0 --max_wifi_cw 0
    ```
    
3.  **Contention Window (CW) Sweep (e.g., for manual optimal CW analysis):**
    Used by `find_optimal_cw` or can be run standalone.
    ```bash
    python contention_window_sweep.py --cw_start 32 --cw_end 512 --cw_step 48 --ap_number 3 --gnb_number 3
    ```

For detailed parameter explanations for any simulation script, use the `--help` flag:
```bash
python coexistence_node_sweep.py --help

Usage: coexistence_node_sweep.py [OPTIONS]

Options:
  --runs INTEGER                 Number of simulation runs (default: 10)
  --seed INTEGER                     Seed for simulation (default: 1)
  --start_node_number INTEGER        Starting number of nodes (required)
  --end_node_number INTEGER          Ending number of nodes (required)
  --simulation_time FLOAT            Simulation duration in μs (default: 100.0)
  --min_wifi_cw INTEGER              Wi-Fi minimum contention window (default: 0)
  --max_wifi_cw INTEGER              Wi-Fi maximum contention window (default: 0)
  --wifi_r_limit INTEGER             Wi-Fi retry limit (default: 3)
  --mcs_value INTEGER                MCS value (default: 7)
  --min_nru_cw INTEGER               NR-U minimum contention window (default: 0)
  --max_nru_cw INTEGER               NR-U maximum contention window (default: 0)
  --synchronization_slot_duration INTEGER
                                     Sync slot duration in μs (default: 1000)
  --max_sync_slot_desync INTEGER     Max gNB desync in μs (default: 1000)
  --min_sync_slot_desync INTEGER     Min gNB desync in μs (default: 0)
  --nru_observation_slot INTEGER     NR-U observation slots (default: 3)
  --mcot INTEGER                     Max NR-U channel occupancy time (ms) (default: 6)
  --nru_mode [rs|gap]                NR-U mode: 'rs' or 'gap' (default: gap)
  --help                             Show this message and exit.
```
## Analyzing Results & Generating Plots
After running simulations, use the analysis scripts to generate plots:
