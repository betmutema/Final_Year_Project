import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from cycler import cycler
import os
import warnings
import glob


def set_viridis_color_palette(a, b, color_amount):
    cmap = mpl.colormaps['viridis']
    color = cmap(np.linspace(a, b, color_amount))
    mpl.rcParams['axes.prop_cycle'] = cycler('color', color)


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


def process_nru_rs_vs_nru_gap():
    print("\n=== Processing NR-U RS vs NR-U GAP Comparison ===\n")
    set_viridis_color_palette(0.0, 1.0, 7)

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
            'output': 'output/metrics_visualizations/comparative_analysis/nru_modes/nru_rs_vs_gap_cot.png'
        },
        'channel_efficiency': {
            'ylim': (0.6, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/nru_modes/nru_rs_vs_gap_eff.png'
        },
        'collision_probability': {
            'ylim': (0, 0.6),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/nru_modes/nru_rs_vs_gap_col.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating comparison plots for NR-U RS vs GAP:")
    for metric, (rs_data, gap_data) in data_by_metric.items():
        print(f"  Processing {metric} comparison...")
        config = plot_configs[metric]
        plot_metrics(
            [rs_data, gap_data],
            ["o", "o"],
            ["-", "-"],
            [' NR-U rs', ' NR-U gap'],
            config['ylim'],
            'Number of NR-U Nodes',
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


def process_coexistence_rs_vs_nru_gap():
    print("\n=== Processing Coexistence RS vs GAP Mode Comparison ===\n")
    set_viridis_color_palette(0.0, 1.0, 8)

    print("Loading coexistence RS and GAP mode data...")
    rs_results = process_coexistence_data('output/simulation_results/coex_rs-mode_raw-data.csv', 'rs')
    gap_results = process_coexistence_data('output/simulation_results/coex_gap-mode_raw-data.csv', 'gap')

    if rs_results is None or gap_results is None:
        return

    # Define plot configurations
    plot_configs = {
        'channel_occupancy': {
            'ylim': (0, 1),
            'ylabel': 'Channel Occupancy',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/coexistence_sync_vs_desync_cot.png'
        },
        'channel_efficiency': {
            'ylim': (0, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/coexistence_sync_vs_desync_eff.png'
        },
        'collision_probability': {
            'ylim': (0, 1),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/coexistence_modes/coexistence_sync_vs_desync_pc.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating coexistence comparison plots for RS vs GAP:")
    for metric, config in plot_configs.items():
        print(f"  Processing {metric} comparison...")
        plot_metrics(
            [rs_results[f'nru_{metric}'], rs_results[f'wifi_{metric}'],
             gap_results[f'nru_{metric}'], gap_results[f'wifi_{metric}']],
            ["o", "o", "o", "o"],
            ["-", "--", "-", "--"],
            [' NR-U rs', ' Wi-Fi rs',
             ' NR-U gap', ' Wi-Fi gap'],
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )


def process_coexistence_gap_sync_vs_desync():
    print("\n=== Processing Coexistence GAP Sync vs Desync Comparison ===\n")
    set_viridis_color_palette(0.0, 1.0, 6)

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
            'output': 'output/metrics_visualizations/comparative_analysis/synchronization_studies/coexistence_gap_sync_vs_desync_cot.png'
        },
        'channel_efficiency': {
            'ylim': (0, 1),
            'ylabel': 'Channel Efficiency',
            'output': 'output/metrics_visualizations/comparative_analysis/synchronization_studies/coexistence_gap_sync_vs_desync_eff.png'
        },
        'collision_probability': {
            'ylim': (0, 1),
            'ylabel': 'Collision Probability',
            'output': 'output/metrics_visualizations/comparative_analysis/synchronization_studies/coexistence_gap_sync_vs_desync_pc.png'
        }
    }

    # Create plots for each metric
    print("\nGenerating coexistence comparison plots for sync vs desync:")
    for metric, config in plot_configs.items():
        print(f"  Processing {metric} comparison...")
        plot_metrics(
            [desync_results[f'nru_{metric}'], desync_results[f'wifi_{metric}'],
             sync_results[f'nru_{metric}'], sync_results[f'wifi_{metric}']],
            ["o", "o", "o", "o"],
            ["-", "--", "-", "--"],
            [' NR-U desync', ' Wi-Fi desync',
             ' NR-U sync', ' Wi-Fi sync'],
            config['ylim'],
            'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'],
            config['output']
        )

def process_coexistence_nru_gap_desync_adjustcw():
    print("\n=== Processing Coexistence NR-U GAP Desync Adjust CW Comparison ===\n")
    set_viridis_color_palette(0.0, 1.0, 6)

    print("Loading disabled backoff and adjusted CW data...")
    disabled_backoff = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_disabled-backoff_raw-data.csv', 'disabled')
    adjusted_cw = process_coexistence_data(
        'output/simulation_results/coex_gap-mode_desync-0-1000_disabled-backoff_adjusted-cw-Varied_raw-data.csv',
        'adjusted')

    if disabled_backoff is None or adjusted_cw is None:
        return

    labels = [
        'NR-U (desync + disabled backoff)',
        'Wi-Fi (desync + disabled backoff)',
        'NR-U (desync + disabled backoff + adjusted wifi CW)',
        'Wi-Fi (desync + disabled backoff + adjusted wifi CW)'
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
            ["o", "o", "o", "o"], ["-", "--", "-", "--"],
            labels, config['ylim'], 'Number of Wi-Fi/NR-U Nodes',
            config['ylabel'], config['output']
        )


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

    process_nru_rs_vs_nru_gap()
    process_coexistence_rs_vs_nru_gap()
    process_coexistence_gap_sync_vs_desync()
    process_coexistence_nru_gap_desync_adjustcw()

    print("\n=== Summary of Generated Output Files ===\n")

    # List all generated files
    list_output_files()

    print("\n=== Comparison Metrics Visualization Complete ===\n")