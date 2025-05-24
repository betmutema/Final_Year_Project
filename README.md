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
### Analyzing Results & Generating Plots

After running simulations, the generated CSV files in `output/simulation_results/` can be processed using the provided Python analysis scripts to generate various plots. These scripts automate the extraction of key metrics and their visualization, enabling comparative analysis of different coexistence strategies and parameter settings.

To generate plots:

1.  **Navigate to the project's root directory** in your terminal.

2.  **Run the desired analysis script.** Below are the primary scripts and their general purpose:

    *   **Comprehensive Comparative Analysis:**
        This script is the main entry point for comparing multiple coexistence strategies and the impact of sequential optimizations (e.g., NR-U RS vs. Gap, desynchronization, backoff disabling, CW adjustments).
        ```bash
        python analyze_simulation_results.py
        ```
        -   **Output:** Plots are saved in `output/metrics_visualizations/comparative_analysis/` subdirectories, categorized by the type of comparison (e.g., `nru_modes/`, `access_methods/`, `coexistence_modes/`).

    *   **General Network Metrics Visualization:**
        This script generates plots for individual technology performance (e.g., Wi-Fi only, NR-U only with specific settings) and for specific coexistence scenarios that might not be covered by the main comparative analysis script. It processes various `coex_*.csv` and `*-only_*.csv` files.
        ```bash
        python visualize_network_metrics.py
        ```
        -   **Output:** Plots are saved in `output/metrics_visualizations/individual_systems/` (for Wi-Fi/NR-U only) and `output/metrics_visualizations/coexistence_strategies/` (for specific coexistence setups).

    *   **Fairness Metrics Visualization:**
        This script focuses specifically on Jain's Fairness Index and Joint Airtime Fairness. It can generate plots in several ways:
        ```bash
        python visualize_fairness.py
        ```
        By default, it attempts to generate:
        -   Consolidated plots (comparing multiple simulation files on one graph).
        -   Individual plots (one set of fairness plots per relevant simulation file).
        -   Category-based plots (grouping similar scenarios).
        You can control which types of plots are generated using flags like `--no-individual`, `--no-categories`, or `--no-consolidated`.
        -   **Output:** Plots are saved in `output/metrics_visualizations/fairness_plots/` subdirectories (`consolidated/`, `individual/`, `categories/`).

    *   **Wi-Fi Contention Window Impact Visualization:**
        This script processes the output from `contention_window_sweep.py` (files typically named `airtime_fairness_*.csv`) to show how varying the Wi-Fi Contention Window size affects channel occupancy for both Wi-Fi and NR-U. This is crucial for understanding the trade-offs involved in CW adjustments.
        ```bash
        python visualize_cw_impact.py
        ```
        -   **Output:** Plots are saved in `output/metrics_visualizations/airtime_fairness/`.

    *   **Asymmetric Network Metrics Visualization:**
        This script is dedicated to visualizing the performance (channel occupancy, efficiency, collision probability, fairness) for asymmetric node configurations (i.e., unequal numbers of Wi-Fi APs and NR-U gNBs). It typically processes files like `coex_asymmetric_*dynamic-cw*.csv`.
        ```bash
        python visualize_asymetric_network_metrics.py
        ```
        You can optionally provide specific input and output directories:
        ```bash
        python visualize_asymetric_network_metrics.py --input output/simulation_results/your_asymmetric_data.csv --output-dir output/my_asymmetric_plots
        ```
        -   **Output:** Plots are saved by default in `output/plots/` or the specified output directory.

### Output Locations for Plots:

-   **Raw Simulation Data (CSV):** All simulation scripts save their output to `output/simulation_results/`.
-   **Generated Plots (PNG):**
    -   `analyze_simulation_results.py`: `output/metrics_visualizations/comparative_analysis/`
    -   `visualize_network_metrics.py`: `output/metrics_visualizations/individual_systems/` and `output/metrics_visualizations/coexistence_strategies/`
    -   `visualize_fairness.py`: `output/metrics_visualizations/fairness_plots/`
    -   `visualize_cw_impact.py`: `output/metrics_visualizations/airtime_fairness/`
    -   `visualize_asymetric_network_metrics.py`: `output/plots/` (default)

**Note:**
Ensure that the simulation CSV files required by an analysis script are present in the `output/simulation_results/` directory before running the analysis script. The scripts are generally designed to find relevant files based on naming conventions.

## Example Results

This section provides a glimpse into the types of visualizations generated by the analysis scripts, showcasing key performance comparisons.

| Metric                                  | Description                                                                    | Visualization Example                                                                                                                         |
| :-------------------------------------- | :----------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| **Channel Occupancy (Access Methods)**  | Comparing channel usage of NR-U (RS & Gap modes) and Wi-Fi in coexistence.     | `![cot_access_plot](output/metrics_visualizations/comparative_analysis/access_methods/access_methods_comparison_cot.png)`                   |
| **Collision Probability (Optimized vs RS)** | Collision rates for the Optimized NR-U Gap Mode vs. NR-U RS Mode in coexistence. | `![pcol_optimized_plot](output/metrics_visualizations/comparative_analysis/coexistence_modes/coexistence_rs_vs_modified_gap_pc.png)`        |
| **Channel Efficiency (Optimized vs RS)**  | Channel efficiency for the Optimized NR-U Gap Mode vs. NR-U RS Mode in coexistence. | `![eff_optimized_plot](output/metrics_visualizations/comparative_analysis/coexistence_modes/coexistence_rs_vs_modified_gap_eff.png)`        |
| **Fairness (Asymmetric Scenarios)**     | Jain's Fairness Index & Joint Airtime Fairness under asymmetric node counts.   | `![fairness_asymm_plot](output/plots/fairness_indices.png)`                                                                               |

*(Note: Ensure these image paths are correct relative to your repository structure and that the images are generated by your scripts. You might need to commit these specific example images to your repository for them to render correctly on GitHub if they are not generated with every run of the analysis scripts.)*

## Acknowledgements
This simulation framework builds upon the foundational work of Jakub Cichoń's "A Wi-Fi and NR-U Coexistence Channel Access Simulator based on the Python SimPy Library" (AGH University of Science and Technology, 2022). His publicly available resources and simulator structure provided an essential starting point for this project.
