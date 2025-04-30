import glob
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import re
import warnings
from cycler import cycler


def extract_parameters(filename):
    """Extract parameters from filename like wifi-only_nodes-1-10_raw-data.csv"""
    match = re.search(r"wifi-only_nodes-(\d+-\d+)", filename)
    return match.group(1) if match else "unknown"

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

def create_plot(x_data, y_data, title, xlabel, ylabel, output_path, ylim=(0, 1), linestyle="-"):
    """Create and save a plot with given data and parameters"""
    fig, ax = plt.subplots()
    y_data.plot(marker="o", legend=True, ylim=ylim, linestyle='-')
    ax.legend([title])
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    # ax.legend(loc = 'best')
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"  Saved plot: {output_path}")
    # plt.show()
    plt.close(fig)


def create_dual_plot(x_data1, y_data1, x_data2, y_data2, titles, xlabel, ylabel, output_path, ylim=(0, 1)):
    """Create and save a plot with two data series"""
    fig, ax = plt.subplots()
    y_data1.plot(marker="o", legend=True, ylim=ylim, linestyle='-')
    y_data2.plot(marker="D", legend=True, ylim=ylim, linestyle='-.')
    ax.legend(titles)
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    # ax.set_title(titles, fontsize=14)

    plt.tight_layout()
    plt.savefig(output_path)
    print(f"  Saved plot: {output_path}")
    # plt.show() # disp
    plt.close(fig)


def plot_metrics(data, node_count_col, metric_cols, titles, output_dir, filename_prefix, ylims=None,
                 technology_type=None):
    """Generic function to plot metrics data"""
    if ylims is None:
        ylims = [(0, 1), (0, 1), (0, 1)]

    # Group data by node count and calculate mean for each metric
    grouped_data = []
    for col in metric_cols:
        grouped_data.append(data.groupby([node_count_col])[col].mean())

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nGenerating plots for {filename_prefix}:")
    # Plot metrics
    metrics = ['cot', 'eff', 'pcol']

    # Set y-axis labels based on technology type
    if technology_type == "wifi":
        node_label = "Number of Wi-Fi Nodes"
    elif technology_type == "nru":
        node_label = "Number of NR-U Nodes"
    else:
        node_label = "Number of nodes"

    for i, (metric_data, title, ylim) in enumerate(zip(grouped_data, titles, ylims)):
        output_path = os.path.join(output_dir, f"{filename_prefix}_{metrics[i]}.png")
        create_plot(
            None, metric_data, title, node_label,
            ['Channel Occupancy', 'Channel Efficiency', 'Collision Probability'][i],
            output_path, ylim=ylim
        )


def plot_dual_metrics(data, node_count_cols, metric_cols, titles, output_dir, filename_prefix, ylims=None):
    """Generic function to plot dual metrics data"""
    if ylims is None:
        ylims = [(0, 1), (0, 1), (0, 1)]

    # Group data by node count and calculate mean for each metric
    grouped_data = []
    for col_pair in zip(node_count_cols, metric_cols):
        node_col, metric_col = col_pair
        grouped_data.append(data.groupby([node_col])[metric_col].mean())

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nGenerating plots for {filename_prefix}:")
    # Plot metrics in pairs
    metrics = ['cot', 'eff', 'pcol']
    labels = ['Channel Occupancy', 'Channel Efficiency', 'Collision Probability']

    # For coexisting technologies, use combined label
    node_label = "Number of WiFi/NR-U Nodes"

    for i in range(0, len(grouped_data), 2):
        if i + 1 < len(grouped_data):  # Ensure we have pairs
            output_path = os.path.join(output_dir, f"{filename_prefix}_{metrics[i // 2]}.png")
            create_dual_plot(
                None, grouped_data[i], None, grouped_data[i + 1],
                [titles[i], titles[i + 1]], node_label,
                labels[i // 2], output_path, ylim=ylims[i // 2]
            )


def plot_wifi_metrics():
    # Find WiFi CSV file
    try:
        csv_files = glob.glob('output/simulation_results/wifi-only_nodes-*_raw-data.csv')
        if not csv_files:
            raise ValueError("No WiFi CSV files found")

        csv_path = csv_files[0]
        params = extract_parameters(os.path.basename(csv_path))
        # Load data
        wifi_metrics = pd.read_csv(csv_path)

        # Define metrics to plot
        metric_cols = ['wifi_channel_occupancy', 'wifi_channel_efficiency', 'wifi_collision_probability']
        titles = [
            f'Wi-Fi Channel Occupancy ({params})',
            f'Wi-Fi Channel Efficiency ({params})',
            f'Wi-Fi Collision Probability ({params})'
        ]

        output_dir = 'output/metrics_visualizations/individual_systems/wifi'
        output_prefix = f"wifi_nodes-{params}"
        ylims = [(0.6, 1), (0, 1), (0, 0.5)]

        plot_metrics(
            wifi_metrics, 'wifi_node_count', metric_cols, titles,
            output_dir, output_prefix, ylims, technology_type="wifi"
        )
    except Exception as e:
        warnings.warn(f"Skipping WiFi metrics: {str(e)}")


def plot_nru_metrics(mode):
    # Load data
    csv_path = f'output/simulation_results/nru-only_{mode}-mode_raw-data.csv'
    if not os.path.exists(csv_path):
        warnings.warn(f"NR-U {mode} metrics CSV not found: {csv_path}")
        return

    try:
        nru_metrics = pd.read_csv(csv_path)

        # Define metrics to plot
        metric_cols = ['nru_channel_occupancy', 'nru_channel_efficiency', 'nru_collision_probability']
        titles = [f'NR-U ', f'NR-U ', f'NR-U ']

        output_dir = f'output/metrics_visualizations/individual_systems/nru'
        output_prefix = f"nru_{mode}"
        ylims = [(0.6, 1), (0.6, 1), (0, 0.6)]

        plot_metrics(
            nru_metrics, 'nru_node_count', metric_cols, titles,
            output_dir, output_prefix, ylims, technology_type="nru"
        )
    except Exception as e:
        warnings.warn(f"Error processing NRU {mode} metrics: {str(e)}")


def plot_coexistence_metrics(mode):
    # Load data
    csv_path = f'output/simulation_results/coex_{mode}-mode_raw-data.csv'
    if not os.path.exists(csv_path):
        warnings.warn(f"Coexistence {mode} metrics CSV not found: {csv_path}")
        return

    try:
        coex_metrics = pd.read_csv(csv_path)

        # Define metrics to plot
        node_count_cols = ['nru_node_count', 'wifi_node_count'] * 3
        metric_cols = [
            'nru_channel_occupancy', 'wifi_channel_occupancy',
            'nru_channel_efficiency', 'wifi_channel_efficiency',
            'nru_collision_probability', 'wifi_collision_probability'
        ]
        titles = [
            ' NR-U', ' Wi-Fi',
            ' NR-U', ' Wi-Fi',
            ' NR-U', ' Wi-Fi'
        ]

        output_dir = f'output/metrics_visualizations/coexistence_strategies/coex_{mode}'
        output_prefix = f"coexistence_{mode}"
        ylims = [(0, 1), (0, 1), (0, 1)]

        plot_dual_metrics(
            coex_metrics, node_count_cols, metric_cols, titles,
            output_dir, output_prefix, ylims
        )
    except Exception as e:
        warnings.warn(f"Error processing coexistence {mode} metrics: {str(e)}")


def parse_desync_filename(filename):
    """Parse parameters from desync filenames"""
    result = {}

    # Extract desync values
    desync_match = re.search(r"desync-(\d+)-(\d+)", filename)
    if desync_match:
        result['desync_min'] = desync_match.group(1)
        result['desync_max'] = desync_match.group(2)

    # Check if backoff is disabled
    result['disabled_backoff'] = 'disabled-backoff' in filename

    # Extract CW value if present
    cw_match = re.search(r"adjusted-cw-([^_]+)", filename)
    result['cw_value'] = cw_match.group(1) if cw_match else None

    return result


def get_file_category(filename):
    """Categorize files based on their parameters"""
    params = parse_desync_filename(filename)

    # Basic desync file with no additional parameters
    if not params['disabled_backoff'] and not params['cw_value']:
        return 'basic_desync'

    # Disabled backoff but no CW adjustment
    elif params['disabled_backoff'] and not params['cw_value']:
        return 'disabled_backoff'

    # Disabled backoff with specific CW value
    elif params['disabled_backoff'] and params['cw_value'] != 'Varied':
        return f"cw_{params['cw_value']}"

    # Varied CW value
    elif params['disabled_backoff'] and params['cw_value'] == 'Varied':
        return 'varied_cw'

    # Fallback for unexpected cases
    else:
        return 'other'


def process_desync_files(category='basic_desync'):
    """Process desync files by category and create appropriate plots"""
    # Get all desync files
    all_files = glob.glob('output/simulation_results/coex_gap-mode_desync-*_raw-data.csv')

    # Filter files by category
    if category == 'basic_desync':
        # Simple desync files with no additional parameters
        files = [f for f in all_files if 'disabled-backoff' not in f.lower()]
        output_prefix = 'coexistence_gap_desync'
        output_dir = 'output/metrics_visualizations/coexistence_strategies/coexistence_gap_desync'
        print("\n*** Basic Desync Files ***\n")

    elif category == 'disabled_backoff':
        # Files with disabled backoff
        files = [f for f in all_files if get_file_category(f) == 'disabled_backoff']
        output_prefix = 'coexistence_gap_desync_disabled_backoff'
        output_dir = 'output/metrics_visualizations/coexistence_strategies/coexistence_gap_desync_disabled_backoff'
        print("\n*** Disabled Backoff Files ***\n")

    elif category == 'varied_cw':
        # Files with varied CW
        files = [f for f in all_files if get_file_category(f) == 'varied_cw']
        output_prefix = 'coexistence_gap_desync_disabled_backoff_adjust_cw_Varied'
        output_dir = 'output/metrics_visualizations/coexistence_strategies/coexistence_gap_desync_disabled_backoff_adjust_cw_Varied'
        print("\n*** Varied CW Files ***\n")

    else:
        return  # Unknown category

    if not files:
        print(f"No files found for category: {category}")
        return

    # Print each filename for this category
    for i, file_path in enumerate(files):
        filename = os.path.basename(file_path)
        print(f"{i + 1}. {filename}")

    print(f"\nProcessing {len(files)} files for category: {category}")

    # Load data from all matching files
    coex_metrics = pd.concat([pd.read_csv(f) for f in files])

    # Define metrics to plot
    node_count_cols = ['nru_node_count', 'wifi_node_count'] * 3
    metric_cols = [
        'nru_channel_occupancy', 'wifi_channel_occupancy',
        'nru_channel_efficiency', 'wifi_channel_efficiency',
        'nru_collision_probability', 'wifi_collision_probability'
    ]
    titles = [
        ' NR-U', ' Wi-Fi',
        ' NR-U', ' Wi-Fi',
        ' NR-U', ' Wi-Fi'
    ]

    # output_dir = 'output/metrics_visualizations/coexistence_strategies/coex_gap_desync'
    ylims = [(0.001, 1), (0, 1), (0, 1)]

    # Show what output files will be generated
    # print(f"\nOutput files will be generated in {output_dir}:")
    # metrics = ['cot', 'eff', 'pcol']
    # for metric in metrics:
    #     print(f"  {output_prefix}_{metric}.png")

    plot_dual_metrics(
        coex_metrics, node_count_cols, metric_cols, titles,
        output_dir, output_prefix, ylims
    )


def process_specific_cw_value(cw_value):
    """Process files for a specific CW value"""
    # Find files with this specific CW value
    pattern = f'output/simulation_results/coex_gap-mode_desync-*_disabled-backoff_adjusted-cw-{cw_value}_raw-data.csv'
    files = glob.glob(pattern)

    if not files:
        print(f"No files found for CW value: {cw_value}")
        return

    print(f"\n*** Specific CW Value: {cw_value} ***\n")
    # Print each filename for this CW value
    for i, file_path in enumerate(files):
        filename = os.path.basename(file_path)
        print(f"{i + 1}. {filename}")

    print(f"\nProcessing {len(files)} files for CW value: {cw_value}")

    # Load data from all matching files
    coex_metrics = pd.concat([pd.read_csv(f) for f in files])

    # Define metrics to plot
    node_count_cols = ['nru_node_count', 'wifi_node_count'] * 3
    metric_cols = [
        'nru_channel_occupancy', 'wifi_channel_occupancy',
        'nru_channel_efficiency', 'wifi_channel_efficiency',
        'nru_collision_probability', 'wifi_collision_probability'
    ]
    titles = [
        ' NR-U', ' Wi-Fi',
        ' NR-U', ' Wi-Fi',
        ' NR-U', ' Wi-Fi'
    ]

    output_dir = f'output/metrics_visualizations/coexistence_strategies/coexistence_gap_desync_disabled_backoff_adjust_cw_{cw_value}'
    output_prefix = f"coexistence_gap_desync_disabled_backoff_adjust_cw_{cw_value}"
    ylims = [(0.001, 1), (0.001, 1), (0, 1)]

    # Show what output files will be generated
    # print(f"\nOutput files will be generated in {output_dir}:")
    # metrics = ['cot', 'eff', 'pcol']
    # for metric in metrics:
    #     print(f"  {output_prefix}_{metric}.png")

    plot_dual_metrics(
        coex_metrics, node_count_cols, metric_cols, titles,
        output_dir, output_prefix, ylims
    )


def process_all_cw_files():
    """Find all unique CW values and process each one separately"""
    # Find all files with adjusted CW
    pattern = 'output/simulation_results/coex_gap-mode_desync-*_disabled-backoff_adjusted-cw-*_raw-data.csv'
    files = glob.glob(pattern)

    # Extract unique CW values (excluding "Varied")
    cw_values = set()
    for file in files:
        cw_match = re.search(r"adjusted-cw-([^_]+)", file)
        if cw_match and cw_match.group(1) != 'Varied':
            cw_values.add(cw_match.group(1))

    print(f"\nFound {len(cw_values)} unique CW values: {', '.join(cw_values)}")

    # Process each CW value separately
    for cw_value in cw_values:
        process_specific_cw_value(cw_value)


def main():
    # Set color palette
    # set_viridis_color_palette()
    set_distinct_color_palette()

    print("\n=== Starting Metrics Visualization Process ===\n")

    # Plot individual metrics
    print("Processing WiFi metrics...")
    plot_wifi_metrics()  # Wi-Fi alone

    print("\nProcessing NR-U 'rs' metrics...")
    plot_nru_metrics('rs')  # NR-U rs alone

    print("\nProcessing NR-U 'gap' metrics...")
    plot_nru_metrics('gap')  # NR-U gap alone

    # Plot coexistence metrics
    print("\nProcessing coexistence 'rs' metrics...")
    plot_coexistence_metrics('rs')  # Coexistence with rs

    print("\nProcessing coexistence 'gap' metrics...")
    plot_coexistence_metrics('gap')  # Coexistence with gap

    print("\n=== Processing Desync Files ===")

    # Process desync files by category
    process_desync_files('basic_desync')  # Basic desync files
    process_desync_files('disabled_backoff')  # Files with disabled backoff
    process_desync_files('varied_cw')  # Files with varied CW

    print("\n=== Processing CW Files ===")
    # Process files with specific CW values
    process_all_cw_files()

    print("\n=== Summary of Generated Output Files ===")

    # List all generated image files
    all_output_files = []
    for root, dirs, files in os.walk('output/metrics_visualizations'):
        for file in files:
            if file.endswith('.png'):
                all_output_files.append(os.path.join(root, file))

    print(f"\nTotal number of generated plots: {len(all_output_files)}")
    # print("\nOutput directories:")
    # output_dirs = sorted(set([os.path.dirname(f) for f in all_output_files]))

    # for dir in output_dirs:
    # files_in_dir = [os.path.basename(f) for f in all_output_files if os.path.dirname(f) == dir]
    # print(f"\n  {dir} ({len(files_in_dir)} files):")
    # for file in sorted(files_in_dir):
    # print(f"    - {file}")

    print("\n=== Metrics Visualization Complete ===\n")


if __name__ == "__main__":
    main()