import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from cycler import cycler
import os
import warnings
import glob

def set_distinct_color_palette():
    """
    Sets a color palette with visually distinct colors suitable for visualization
    Uses a colorblind-friendly palette based on Color Brewer and ColorSafe recommendations
    """
    # High-contrast and colorblind-friendly palette
    distinct_colors = [
        '#0072B2',  # blue
        '#D55E00',  # vermillion/orange
        '#009E73',  # green
        '#E69F00',  # orange/amber
        '#56B4E9',  # sky blue
        '#F0E442',  # yellow
        '#000000',  # black
    ]
    mpl.rcParams['axes.prop_cycle'] = cycler('color', distinct_colors)

    # Return the colors in case needed elsewhere
    return distinct_colors


def setup_plot(xlabel='Number of Wi-Fi/NR-U Nodes', ylabel=None, ylim=None):
    """
    Create and setup figure and axes with common settings

    Args:
        xlabel: Label for x-axis (default: 'Number of Wi-Fi/NR-U Nodes')
        ylabel: Label for y-axis (default: None)
        ylim: Tuple defining y-axis limits (default: None)

    Returns:
        Tuple of (figure, axes) objects configured with the specified settings
    """
    fig, ax = plt.subplots()
    ax.set_xlabel(xlabel, fontsize=14)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=14)
    if ylim:
        ax.set_ylim(ylim)
    return fig, ax


def save_and_close_figure(fig, filename):
    """
    Save figure to disk and close it to free memory

    Args:
        fig: matplotlib Figure object to save
        filename: Path where the figure should be saved
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    plt.tight_layout()
    # plt.show()  # Commented out to avoid displaying figures during batch processing
    plt.savefig(filename)
    print(f"  Saved plot: {filename}")
    plt.close(fig)


def plot_metrics(data_groups, markers, linestyles, legend_labels, ylim, xlabel, ylabel, output_file):
    """
    Generic function to plot metrics from multiple data groups

    Args:
        data_groups: List of pandas Series objects containing the data to plot
        markers: List of marker styles for each data series
        linestyles: List of line styles for each data series
        legend_labels: List of labels for the legend
        ylim: Tuple defining y-axis limits
        xlabel: Label for x-axis
        ylabel: Label for y-axis
        output_file: Path where the figure should be saved
    """
    fig, ax = setup_plot(xlabel=xlabel, ylabel=ylabel, ylim=ylim)

    for data, marker, linestyle, label in zip(data_groups, markers, linestyles, legend_labels):
        data.plot(marker=marker, legend=True, ylim=ylim, linestyle=linestyle, ax=ax)

    ax.legend(legend_labels, loc='best')
    # Explicitly set xlabel to override pandas default
    ax.set_xlabel(xlabel, fontsize=14)
    save_and_close_figure(fig, output_file)


def load_data(filepath):
    """
    Load CSV data and handle error cases gracefully

    Args:
        filepath: Path to the CSV file to load

    Returns:
        Pandas DataFrame containing the data, or None if loading fails
    """
    try:
        data = pd.read_csv(filepath, delimiter=',')
        print(f"  Loaded data from {filepath} ({len(data)} rows)")
        return data
    except FileNotFoundError:
        warnings.warn(f"Error: File not found - {filepath}")
        return None
    except Exception as e:
        warnings.warn(f"Error loading {filepath}: {e}")
        return None


def process_nru_rs_vs_gap_mode_comparison():
    """
    Compare performance metrics between NR-U Reserved Signal (RS) mode and NR-U Gap-based mode

    This function:
    1. Loads data for both NR-U modes
    2. Calculates performance metrics (channel occupancy, efficiency, collision probability)
    3. Generates comparison plots showing the differences between modes
    """
    print("\n=== Processing NR-U RS vs NR-U GAP Comparison ===\n")
    set_distinct_color_palette()

    print("Loading NR-U RS and GAP mode data...")
    rs_data = load_data('output/simulation_results/nru-only_rs-mode_raw-data.csv')
    gap_data = load_data('output/simulation_results/nru-only_gap-mode_raw-data.csv')

    # Exit function if data loading failed
    if rs_data is None or gap_data is None:
        return

    # Group data by nru_node_count and calculate means for different metrics
    metrics = ['channel_occupancy', 'channel_efficiency', 'collision_probability']
    data_by_metric = {}
    print("Calculating metrics for comparison...")

    # Calculate mean values for each metric, grouped by node count
    for metric in metrics:
        rs_metric = rs_data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        gap_metric = gap_data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        data_by_metric[metric] = (rs_metric, gap_metric)

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.6, 1),
            'ylabel': 'Channel Occupancy',
            'output': 'output/metrics_visualizations/comparative_analysis/nru_modes/nru_reserved_signal_vs_gap_channel_occupancy.png'
        },
        'channel_efficiency': {
            'ylim': (0.6, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/nru_modes/nru_reserved_signal_vs_gap_channel_efficiency.png'
        },
        'collision_probability': {
            'ylim': (0, 0.6),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/nru_modes/nru_reserved_signal_vs_gap_collision_probability.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating comparison plots for NR-U RS vs GAP:")
    for metric, (rs_data, gap_data) in data_by_metric.items():
        print(f"  Processing {metric} comparison...")
        config = plot_configs[metric]
        plot_metrics(
            [rs_data, gap_data],  # Data series to plot
            ["o", "s"],  # Markers for each series
            ["-", "--"],  # Line styles
            ['NR-U Reservation Signal Mode', 'NR-U Gap-Based Mode'],  # Legend labels
            config['ylim'],  # Y-axis limits
            'Number of NR-U Nodes',  # X-axis label
            config['ylabel'],  # Y-axis label
            config['output']  # Output file path
        )


def compare_nru_rs_gap_wifi_performance():
    """
    Compare performance metrics among NR-U RS mode, NR-U Gap mode, and Wi-Fi

    This function:
    1. Loads data for all three technologies
    2. Combines multiple Wi-Fi data files if present
    3. Calculates performance metrics for each technology
    4. Generates comparison plots showing differences across all three
    """
    print("\n=== Processing NR-U RS vs NR-U GAP vs Wi-Fi Comparison ===\n")
    set_distinct_color_palette()

    print("Loading Wi-Fi, NR-U RS and GAP mode data...")
    rs_data = load_data('output/simulation_results/nru-only_rs-mode_raw-data.csv')
    gap_data = load_data('output/simulation_results/nru-only_gap-mode_raw-data.csv')

    # Use glob to find Wi-Fi data files and combine them if multiple exist
    wifi_data = glob.glob('output/simulation_results/wifi-only_nodes-*-*_raw-data.csv')

    if not wifi_data:
        print("  No Wi-Fi data files found with pattern 'wifi-only_nodes-*-*_raw-data.csv'")
        return

    # Load and combine all Wi-Fi data files
    wifi_data_frames = []
    for file in wifi_data:
        data = load_data(file)
        if data is not None:
            wifi_data_frames.append(data)

    if not wifi_data_frames:
        print("  Failed to load any Wi-Fi data files")
        return

    # Combine all Wi-Fi data frames
    wifi_data = pd.concat(wifi_data_frames)
    print(f"  Combined {len(wifi_data_frames)} Wi-Fi data files ({len(wifi_data)} rows total)")

    if rs_data is None or gap_data is None or wifi_data is None:
        return

    # Group data by node count and calculate means for different metrics
    metrics = ['channel_occupancy', 'channel_efficiency', 'collision_probability']
    data_by_metric = {}
    print("Calculating metrics for comparison...")

    for metric in metrics:
        # Calculate metrics for each technology
        rs_metric = rs_data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        gap_metric = gap_data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        wifi_metric = wifi_data.groupby(['wifi_node_count'])[f'wifi_{metric}'].mean()
        data_by_metric[metric] = (rs_metric, gap_metric, wifi_metric)

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.6, 1),
            'ylabel': 'Channel Occupancy',
            'output': 'output/metrics_visualizations/comparative_analysis/access_methods/access_methods_comparison_cot.png'
        },
        'channel_efficiency': {
            'ylim': (0.6, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/access_methods/access_methods_comparison_eff.png'
        },
        'collision_probability': {
            'ylim': (0, 0.6),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/access_methods/access_methods_comparison_col.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating comparison plots for NR-U RS vs GAP vs Wi-Fi:")
    for metric, (rs_data, gap_data, wifi_data) in data_by_metric.items():
        print(f"  Processing {metric} comparison...")
        config = plot_configs[metric]
        plot_metrics(
            [rs_data, gap_data, wifi_data],  # Include wifi_data in the data list
            ["^", "D", "v"],  # Markers for each technology
            ["-", "-", "--"],  # Line styles
            ['NR-U (RS mode)', 'NR-U (Gap mode)', 'Wi-Fi'],  # Legend labels
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )


def process_coexistence_data(data_file, prefix):
    """
    Process coexistence data for both NR-U and WiFi from a single file

    Args:
        data_file: Path to the CSV file containing coexistence data
        prefix: String prefix for logging purposes (e.g., 'rs', 'gap')

    Returns:
        Dictionary containing calculated metrics for both NR-U and Wi-Fi,
        or None if data loading fails
    """
    data = load_data(data_file)
    if data is None:
        return None

    results = {}
    metrics = ['channel_occupancy', 'channel_efficiency', 'collision_probability']
    print(f"  Calculating metrics for {prefix} mode...")

    for metric in metrics:
        # NR-U metrics grouped by NR-U node count
        results[f'nru_{metric}'] = data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        # WiFi metrics grouped by WiFi node count
        results[f'wifi_{metric}'] = data.groupby(['wifi_node_count'])[f'wifi_{metric}'].mean()

    return results


def process_coexistence_rs_vs_gap_mode():
    """
    Compare coexistence performance between NR-U Reserved Signal mode and NR-U Gap mode
    when sharing spectrum with Wi-Fi

    This function:
    1. Loads coexistence data for both NR-U modes
    2. Processes performance metrics for both NR-U and Wi-Fi in each scenario
    3. Generates comparison plots showing how each mode affects both technologies
    """
    print("\n=== Processing NR-U RS vs GAP Mode Coexistence Comparison ===\n")
    set_distinct_color_palette()

    print("Loading RS and GAP mode coexistence data...")
    rs_results = process_coexistence_data('output/simulation_results/coex_rs-mode_raw-data.csv', 'rs')
    gap_results = process_coexistence_data('output/simulation_results/coex_gap-mode_raw-data.csv', 'gap')

    if rs_results is None or gap_results is None:
        return

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0, 1),
            'ylabel': 'Channel Occupancy',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/rs_vs_gap_coexistence_cot.png'
        },
        'channel_efficiency': {
            'ylim': (0, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/rs_vs_gap_coexistence_eff.png'
        },
        'collision_probability': {
            'ylim': (0, 1),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/rs_vs_gap_coexistence_pc.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating comparison plots for RS vs GAP mode coexistence performance:")
    for metric, config in plot_configs.items():
        print(f"  Processing {metric} comparison...")
        plot_metrics(
            # Data series: NR-U RS, Wi-Fi with RS, NR-U Gap, Wi-Fi with Gap
            [rs_results[f'nru_{metric}'], rs_results[f'wifi_{metric}'],
             gap_results[f'nru_{metric}'], gap_results[f'wifi_{metric}']],
            ["^", "v", "o", "s"],  # Markers
            [":", "--", "-", "-."],  # Line styles
            ['NR-U (RS mode coexistence)', 'Wi-Fi (with RS mode NR-U)',
             'NR-U (Gap mode coexistence)', 'Wi-Fi (with GAP mode NR-U)'],
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )


def process_coexistence_gap_timing_comparison():
    """
    Compare performance between synchronized and desynchronized Gap mode NR-U
    when coexisting with Wi-Fi

    This function:
    1. Loads coexistence data for synchronized and desynchronized Gap mode
    2. Processes performance metrics for both NR-U and Wi-Fi in each scenario
    3. Generates plots showing the impact of timing synchronization
    """
    print("\n=== Processing Coexistence GAP Sync vs Desync Comparison ===\n")
    set_distinct_color_palette()

    print("Loading coexistence sync and desync data...")
    # Desynchronized Gap mode (frame timing offset between 0-1000μs)
    desync_results = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_raw-data.csv',
        'desync')
    # Standard Gap mode (synchronized frame timing)
    sync_results = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_raw-data.csv',
        'sync')

    if desync_results is None or sync_results is None:
        return

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.001, 1),  # Log scale compatible lower bound
            'ylabel': 'Channel Occupancy',
            'output': 'output/metrics_visualizations/comparative_analysis/synchronization_studies/gap_timing_comparison_channel_occupancy.png'
        },
        'channel_efficiency': {
            'ylim': (0, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/synchronization_studies/gap_timing_comparison_channel_efficiency.png'
        },
        'collision_probability': {
            'ylim': (0, 1),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/synchronization_studies/gap_timing_comparison_collision_probability.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating comparison plots for synchronized vs. desynchronized Gap mode:")
    for metric, config in plot_configs.items():
        print(f"  Processing {metric} comparison...")
        plot_metrics(
            # Data series: NR-U desync, Wi-Fi with desync, NR-U sync, Wi-Fi with sync
            [desync_results[f'nru_{metric}'], desync_results[f'wifi_{metric}'],
             sync_results[f'nru_{metric}'], sync_results[f'wifi_{metric}']],
            ["o", "v", "D", "^"],  # Markers
            ["-", "--", "-.", "-"],  # Line styles
            ['NR-U (desynchronized)', 'Wi-Fi (with desynchronized NR-U)',
             'NR-U (synchronized frames)', 'Wi-Fi (with synchronized NR-U)'],
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )


def compare_coexistence_gap_desync_with_without_backoff():
    """
    Compare performance of desynchronized Gap mode NR-U with and without backoff
    mechanism when coexisting with Wi-Fi

    This function:
    1. Finds and loads data files for desync mode with and without backoff
    2. Calculates performance metrics for both scenarios
    3. Generates comparison plots showing the impact of disabling backoff
    """
    print("\n=== Processing Coexistence Gap Desync vs Backoff Comparison ===\n")
    set_distinct_color_palette()

    print("Loading coexistence desync and backoff data...")
    # Use glob to find and filter relevant data files
    desync_results = glob.glob('output/simulation_results/coex_gap-mode_desync-*-*_raw-data.csv')
    backoff_results = glob.glob('output/simulation_results/coex_gap-mode_desync-*-*_disabled-backoff_raw-data.csv')

    # Filter out files that don't match our criteria
    desync_results = [file for file in desync_results if not "disabled-backoff" in file.lower()]
    backoff_results = [file for file in backoff_results if not "adjusted" in file.lower()]

    if not desync_results:
        print("  No data files found with pattern 'coex_gap-mode_desync-*-*_raw-data.csv'")
        return

    if not backoff_results:
        print("  No data files found with pattern 'coex_gap-mode_desync-*-*_disabled-backoff_raw-data.csv'")
        return

    # Load and combine all desync data files (standard backoff)
    desync_results_frames = []
    for file in desync_results:
        data = load_data(file)
        if data is not None:
            desync_results_frames.append(data)

    # Load and combine all disabled backoff data files
    backoff_results_frames = []
    for file in backoff_results:
        data = load_data(file)
        if data is not None:
            backoff_results_frames.append(data)

    if not desync_results_frames or not backoff_results_frames:
        print("  Failed to load any data files")
        return

    # Combine all desync data frames
    desync_data = pd.concat(desync_results_frames)
    print(f"  Combined {len(desync_results_frames)} Desync data files ({len(desync_data)} rows total)")

    # Combine all backoff data frames
    backoff_data = pd.concat(backoff_results_frames)
    print(f"  Combined {len(backoff_results_frames)} Backoff data files ({len(backoff_data)} rows total)")

    # Group data and calculate means for different metrics
    metrics = ['channel_occupancy', 'channel_efficiency', 'collision_probability']
    data_by_metric = {}
    print("Calculating metrics for comparison...")

    # Process metrics for both desync and backoff data
    for metric in metrics:
        # Calculate metrics for desync data (with standard backoff)
        desync_nru_metric = desync_data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        desync_wifi_metric = desync_data.groupby(['wifi_node_count'])[f'wifi_{metric}'].mean()

        # Calculate metrics for disabled backoff data
        backoff_nru_metric = backoff_data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        backoff_wifi_metric = backoff_data.groupby(['wifi_node_count'])[f'wifi_{metric}'].mean()

        # Store the results
        data_by_metric[metric] = (desync_nru_metric, desync_wifi_metric, backoff_nru_metric, backoff_wifi_metric)

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.001, 1),  # Log scale compatible lower bound
            'ylabel': 'Channel Occupancy',
            'output': 'output/metrics_visualizations/comparative_analysis/disabling_back_off/coexistence_gap_desync_backoff_comparison_cot.png'
        },
        'channel_efficiency': {
            'ylim': (0, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/disabling_back_off/coexistence_gap_desync_backoff_comparison_eff.png'
        },
        'collision_probability': {
            'ylim': (0, 1),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/disabling_back_off/coexistence_gap_desync_backoff_comparison_pc.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating coexistence comparison plots for desync vs backoff:")
    for metric, (desync_nru, desync_wifi, backoff_nru, backoff_wifi) in data_by_metric.items():
        print(f"  Processing {metric} comparison...")
        config = plot_configs[metric]
        plot_metrics(
            # Data series for both configurations and technologies
            [desync_nru, desync_wifi, backoff_nru, backoff_wifi],
            ["o", "v", "D", "^"],  # Markers
            ["-", "--", "-.", "-"],  # Line styles
            ['NR-U (desync, backoff)',
             'Wi-Fi (with NR-U: desync, backoff)',
             'NR-U (desync, no backoff)',
             'Wi-Fi (with NR-U: desync, no backoff)'],
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )


def process_coexistence_nru_gap_desync_adjustcw():
    """
    Compare performance of desynchronized Gap mode NR-U with disabled backoff
    versus the same configuration with adjusted contention window (CW)

    This function:
    1. Loads data for both configurations
    2. Processes performance metrics for both scenarios
    3. Generates plots showing the impact of CW adjustment on fairness and performance
    """
    print("\n=== Processing Coexistence NR-U GAP Desync Adjust CW Comparison ===\n")
    set_distinct_color_palette()

    print("Loading disabled backoff and adjusted CW data...")
    # Standard disabled backoff configuration
    disabled_backoff = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_disabled-backoff_raw-data.csv',
        'disabled')
    # Disabled backoff with varied (adjusted) contention window
    adjusted_cw = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_disabled-backoff_adjusted-cw-Varied_raw-data.csv',
        'adjusted')

    if disabled_backoff is None or adjusted_cw is None:
        return

    # Create descriptive labels for the legend
    labels = [
        'NR-U (desync, no backof)',
        'Wi-Fi (with NR-U: desync, no backoff)',
        'NR-U (desync, no backoff, adj. CW)',
        'Wi-Fi (with NR-U: desync, no backoff, adj. CW)'
    ]

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.001, 1),  # Log scale compatible lower bound
            'ylabel': 'Channel Occupancy',
            'output': 'output/metrics_visualizations/comparative_analysis/contention_window_adjustments/coexistence_gap_desync_adjustcw_cot.png'
        },
        'channel_efficiency': {
            'ylim': (0, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/contention_window_adjustments/coexistence_gap_desync_adjustcw_eff.png'
        },
        'collision_probability': {
            'ylim': (0, 1),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/contention_window_adjustments/coexistence_gap_desync_adjustcw_pc.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating coexistence comparison plots for disabled backoff vs adjusted CW:")
    for metric, config in plot_configs.items():
        print(f"  Processing {metric} comparison...")
        plot_metrics(
            # Data series for both configurations
            [disabled_backoff[f'nru_{metric}'], disabled_backoff[f'wifi_{metric}'],
             adjusted_cw[f'nru_{metric}'], adjusted_cw[f'wifi_{metric}']],
            ["o", "D", "s", "h"],  # Markers
            ["-", "--", "-", "-."],  # Line styles
            labels,
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )


def process_coexistence_rs_vs_coexistence_modified():
    """
    Compare standard RS mode coexistence against optimized Gap mode
    (with desync, disabled backoff, and adjusted CW)

    This function:
    1. Loads data for standard RS mode and optimized Gap mode
    2. Processes metrics for both configurations
    3. Generates plots to evaluate which provides better overall performance
    """
    print("\n=== Processing Coexistence RS vs Desync Adjust CW Comparison ===\n")
    set_distinct_color_palette()

    print("Loading coexistence rs and coexistence modified data...")
    # Load data for standard RS mode
    coex_rs = process_coexistence_data(
        'output/simulation_results/coex_rs-mode_raw-data.csv',
        'rs')

    # Load data for modified GAP mode (with desync, disabled backoff, and adjusted CW)
    coex_mod = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_disabled-backoff_adjusted-cw-Varied_raw-data.csv',
        'mod')

    if coex_rs is None or coex_mod is None:
        print("  Failed to load one or both of the required data files")
        return

    # Create descriptive labels for the legend
    labels = [
        'NR-U (standard RS mode)',
        'Wi-Fi (with RS mode NR-U)',
        'NR-U (modified Gap mode: desync, no backoff, adj.CW)',
        'Wi-Fi (with modified Gap mode NR-U)'
    ]

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.001, 1),  # Log scale compatible lower bound
            'ylabel': 'Channel Occupancy',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/coexistence_rs_vs_modified_gap_cot.png'
        },
        'channel_efficiency': {
            'ylim': (0, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/coexistence_rs_vs_modified_gap_eff.png'
        },
        'collision_probability': {
            'ylim': (0, 1),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/coexistence_rs_vs_modified_gap_pc.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating coexistence comparison plots for RS vs modified GAP:")
    for metric, config in plot_configs.items():
        print(f"  Processing {metric} comparison...")
        # Plot the metrics using the generic plotting function
        plot_metrics(
            [coex_rs[f'nru_{metric}'], coex_rs[f'wifi_{metric}'],
             coex_mod[f'nru_{metric}'], coex_mod[f'wifi_{metric}']],
            ["o", "D", "s", "h"],  # Markers for each data series
            ["-", "--", "-.", "-."],  # Line styles for each data series
            labels,  # Legend labels
            config['ylim'],  # Y-axis limits
            'Number of Wi-Fi/NR-U Nodes',  # X-axis label
            config['ylabel'],  # Y-axis label
            config['output']  # Output file path
        )

    print(f"  Completed RS vs Modified GAP comparison for all metrics")

def list_output_files():
    """List all generated output files"""
    # output_files = glob.glob('output/metrics_visualizations/comparative_analysis/*.png')
    output_files = glob.glob('output/metrics_visualizations/comparative_analysis/**/*.png', recursive=True)

    print(f"Total number of generated plots: {len(output_files)}")

if __name__ == "__main__":
    print("\n=== Starting Comparison Metrics Visualization Process ===\n")

    # Ensure output directories exist
    output_dir = 'output/metrics_visualizations/comparative_analysis'
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory created: {output_dir}")

    process_nru_rs_vs_gap_mode_comparison()
    compare_nru_rs_gap_wifi_performance()
    process_coexistence_rs_vs_gap_mode()
    process_coexistence_gap_timing_comparison()
    compare_coexistence_gap_desync_with_without_backoff() # backoff
    process_coexistence_nru_gap_desync_adjustcw()
    process_coexistence_rs_vs_coexistence_modified()

    print("\n=== Summary of Generated Output Files ===\n")

    # List all generated files
    list_output_files()

    print("\n=== Comparison Metrics Visualization Complete ===\n")