# 5G NR-U and Wi-Fi Coexistence Simulator

A SimPy-based simulation framework for analyzing the coexistence mechanisms between 5G NR-U (Unlicensed) and Wi-Fi networks in shared spectrum bands.

## Features

- **Parameter Sweeps**: Sweep nodes, contention window (CW) sizes, and synchronization parameters.
- **Modes of Operation**: Supports NR-U "gap" (listen-before-talk) and "rs" (reservation signal) modes.
- **Comprehensive Metrics**: Measures channel occupancy, efficiency, collision probability, and network fairness.
- **Visualization Tools**: Automated scripts to generate comparative plots (e.g., efficiency vs. node count).
- **Flexible Configuration**: CLI-driven simulations with customizable parameters (CW ranges, retry limits, MCS, etc.).

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/coexistence-simulator.git
   cd coexistence-simulator
