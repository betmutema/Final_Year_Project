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
       # '#CC79A7',  # pink
        '#E69F00',  # orange/amber
        '#56B4E9',  # sky blue
        '#F0E442',  # yellow
        '#000000',  # black
    ]
    mpl.rcParams['axes.prop_cycle'] = cycler('color', distinct_colors)

    # Return the colors in case needed elsewhere
    return distinct_colors


def setup_plot(xlabel='Number of Wi-Fi/NR-U Nodes', ylabel=None, ylim=None):
    """Create and setup figure and axes with common settings"""
    fig, ax = plt.subplots()
    ax.set_xlabel(xlabel, fontsize=14)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=14)
    if ylim:
        ax.set_ylim(ylim)
    return fig, ax


def save_and_close_figure(fig, filename):
    """Save figure and close it"""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    plt.tight_layout()
    # plt.show()
    plt.savefig(filename)
    print(f"  Saved plot: {filename}")
    plt.close(fig)


def plot_metrics(data_groups, markers, linestyles, legend_labels, ylim, xlabel, ylabel, output_file):
    """Generic function to plot metrics"""
    fig, ax = setup_plot(xlabel=xlabel, ylabel=ylabel, ylim=ylim)

    for data, marker, linestyle, label in zip(data_groups, markers, linestyles, legend_labels):
        data.plot(marker=marker, legend=True, ylim=ylim, linestyle=linestyle, ax=ax)

    ax.legend(legend_labels, loc='best')
    # Explicitly set xlabel to override pandas default
    ax.set_xlabel(xlabel, fontsize=14)  # <-- Add this line
    save_and_close_figure(fig, output_file)


def load_data(filepath):
    """Load CSV data and handle error cases"""
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
    print("\n=== Processing NR-U RS vs NR-U GAP Comparison ===\n")
    # set_viridis_color_palette(0.0, 1.0, 7)
    set_distinct_color_palette()

    print("Loading NR-U RS and GAP mode data...")
    rs_data = load_data('output/simulation_results/nru-only_rs-mode_raw-data.csv')
    gap_data = load_data('output/simulation_results/nru-only_gap-mode_raw-data.csv')

    if rs_data is None or gap_data is None:
        return

    # Group data by nru_node_count and calculate means for different metrics
    metrics = ['channel_occupancy', 'channel_efficiency', 'collision_probability']
    data_by_metric = {}
    print("Calculating metrics for comparison...")

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
            [rs_data, gap_data],
            ["o", "s"],
            ["-", "--"],
            ['NR-U Reservation Signal Mode', 'NR-U Gap-Based Mode'],
            config['ylim'],
            'Number of NR-U Nodes',
            config['ylabel'],
            config['output']
        )

def compare_nru_rs_gap_wifi_performance():
    print("\n=== Processing NR-U RS vs NR-U GAP vs Wi-Fi Comparison ===\n")
    # set_viridis_color_palette(0.0, 1.0, 7)
    set_distinct_color_palette()

    print("Loading Wi-Fi, NR-U RS and GAP mode data...")
    rs_data = load_data('output/simulation_results/nru-only_rs-mode_raw-data.csv')
    gap_data = load_data('output/simulation_results/nru-only_gap-mode_raw-data.csv')
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

    # Group data by nru_node_count and calculate means for different metrics
    metrics = ['channel_occupancy', 'channel_efficiency', 'collision_probability']
    data_by_metric = {}
    print("Calculating metrics for comparison...")

    for metric in metrics:
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
            ["^", "D", "v"],  # Add a marker for wifi
            ["-", "-", "--"],  # Add a linestyle for wifi
            ['NR-U (RS mode)', 'NR-U (Gap mode)', 'Wi-Fi'],  # Update legend labels
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )

def process_coexistence_data(data_file, prefix):
    """Process coexistence data for both NR-U and WiFi"""
    data = load_data(data_file)
    if data is None:
        return None

    results = {}
    metrics = ['channel_occupancy', 'channel_efficiency', 'collision_probability']
    print(f"  Calculating metrics for {prefix} mode...")

    for metric in metrics:
        # NR-U metrics
        results[f'nru_{metric}'] = data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        # WiFi metrics
        results[f'wifi_{metric}'] = data.groupby(['wifi_node_count'])[f'wifi_{metric}'].mean()

    return results

def process_coexistence_rs_vs_gap_mode():
    print("\n=== Processing NR-U RS vs GAP Mode Coexistence Comparison ===\n")
    # set_viridis_color_palette(0.0, 1.0, 8)
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
            [rs_results[f'nru_{metric}'], rs_results[f'wifi_{metric}'],
             gap_results[f'nru_{metric}'], gap_results[f'wifi_{metric}']],
            ["^", "v", "o", "s"],
            [":", "--", "-", "-."],
            ['NR-U (RS mode coexistence)', 'Wi-Fi (with RS mode NR-U)', 'NR-U (Gap mode coexistence)', 'Wi-Fi (with GAP mode NR-U)'],
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )

def process_coexistence_gap_timing_comparison():
    print("\n=== Processing Coexistence GAP Sync vs Desync Comparison ===\n")
    # set_viridis_color_palette(0.0, 1.0, 6)
    set_distinct_color_palette()

    print("Loading coexistence sync and desync data...")
    desync_results = process_coexistence_data('output/simulation_results/coex_gap-mode_desync-0-1000_raw-data.csv',
                                              'desync')
    sync_results = process_coexistence_data('output/simulation_results/coex_gap-mode_raw-data.csv', 'sync')

    if desync_results is None or sync_results is None:
        return

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.001, 1),
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
            [desync_results[f'nru_{metric}'], desync_results[f'wifi_{metric}'],
             sync_results[f'nru_{metric}'], sync_results[f'wifi_{metric}']],
            ["o", "v", "D", "^"],
            ["-", "--", "-.", "-"],
            ['NR-U (desynchronized)', 'Wi-Fi (with desynchronized NR-U)',
             'NR-U (synchronized frames)', 'Wi-Fi (with synchronized NR-U)'],
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )

def compare_coexistence_gap_desync_with_without_backoff():
    print("\n=== Processing Coexistence Gap Desync vs Backoff Comparison ===\n")
    set_distinct_color_palette()

    print("Loading coexistence desync and backoff data...")
    # Use glob to find Wi-Fi data files and combine them if multiple exist
    desync_results = glob.glob('output/simulation_results/coex_gap-mode_desync-*-*_raw-data.csv')
    backoff_results = glob.glob('output/simulation_results/coex_gap-mode_desync-*-*_disabled-backoff_raw-data.csv')

    desync_results = [file for file in desync_results if not "disabled-backoff" in file]
    backoff_results = [file for file in backoff_results if not "adjusted" in file]

    if not desync_results:
        print("  No data files found with pattern 'coex_gap-mode_desync-*-*_raw-data.csv'")
        return

    if not backoff_results:
        print("  No data files found with pattern 'coex_gap-mode_desync-*-*_disabled-backoff_raw-data.csv'")
        return

    # Load and combine all desync data files
    desync_results_frames = []
    for file in desync_results:
        data = load_data(file)
        if data is not None:
            desync_results_frames.append(data)

    # Load and combine all backoff data files
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
    desync_metrics = {}
    backoff_metrics = {}

    for metric in metrics:
        # Calculate metrics for desync data
        desync_nru_metric = desync_data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        desync_wifi_metric = desync_data.groupby(['wifi_node_count'])[f'wifi_{metric}'].mean()

        # Calculate metrics for backoff data
        backoff_nru_metric = backoff_data.groupby(['nru_node_count'])[f'nru_{metric}'].mean()
        backoff_wifi_metric = backoff_data.groupby(['wifi_node_count'])[f'wifi_{metric}'].mean()

        # Store the results
        data_by_metric[metric] = (desync_nru_metric, desync_wifi_metric, backoff_nru_metric, backoff_wifi_metric)

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.001, 1),
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
            [desync_nru, desync_wifi, backoff_nru, backoff_wifi],
            ["o", "v", "D", "^"],
            ["-", "--", "-.", "-"],
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
    print("\n=== Processing Coexistence NR-U GAP Desync Adjust CW Comparison ===\n")
    # set_viridis_color_palette(0.0, 1.0, 6)
    set_distinct_color_palette()

    print("Loading disabled backoff and adjusted CW data...")
    disabled_backoff = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_disabled-backoff_raw-data.csv', 'disabled')
    adjusted_cw = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_disabled-backoff_adjusted-cw-Varied_raw-data.csv',
        'adjusted')

    if disabled_backoff is None or adjusted_cw is None:
        return

    labels = [
        'NR-U (desync, no backof)',
        'Wi-Fi (with NR-U: desync, no backoff)',
        'NR-U (desync, no backoff, adj. CW)',
        'Wi-Fi (with NR-U: desync, no backoff, adj. CW)'
    ]

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.001, 1),
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
            [disabled_backoff[f'nru_{metric}'], disabled_backoff[f'wifi_{metric}'],
             adjusted_cw[f'nru_{metric}'], adjusted_cw[f'wifi_{metric}']],
            ["o", "D", "s", "h"], ["-", "--", "-", "-."],
            labels, config['ylim'], 'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'], config['output']
        )


def process_coexistence_rs_vs_coexistence_modified():
    print("\n=== Processing Coexistence RS vs Desync Adjust CW Comparison ===\n")
    set_distinct_color_palette()

    print("Loading coexistence rs and coexistence modified data...")
    # Load data for standard RS mode
    coex_rs = process_coexistence_data(
        'output/simulation_results/coex_rs-mode_raw-data.csv', 'rs')

    # Load data for modified GAP mode (with desync, disabled backoff, and adjusted CW)
    coex_mod = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_disabled-backoff_adjusted-cw-Varied_raw-data.csv',
        'mod')

    if coex_rs is None or coex_mod is None:
        print("  Failed to load one or both of the required data files")
        return

    # Create more descriptive labels for the legend
    labels = [
        'NR-U (standard RS mode)',
        'Wi-Fi (with RS mode NR-U)',
        'NR-U (modified Gap mode: desync, no backoff, adj.CW)',
        'Wi-Fi (with modified Gap mode NR-U)'
    ]

    # Define plot configurations with appropriate axis limits and output paths
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0.001, 1),
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

    # Group files by directory
    # output_dirs = sorted(set([os.path.dirname(f) for f in output_files]))
    #     for dir in output_dirs:
    #         files_in_dir = [os.path.basename(f) for f in output_files if os.path.dirname(f) == dir]
    #         print(f"\n  {dir} ({len(files_in_dir)} files):")
    #         for file in sorted(files_in_dir):
    #             print(f"    - {file}")

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