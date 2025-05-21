import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import glob
import argparse
from collections import defaultdict


def plot_asymmetric_results(input_file=None, output_dir=None):
    """
    Plot the results of asymmetric coexistence simulations.

    Args:
        input_file: Path to the CSV file with simulation results
        output_dir: Directory to save the plots
    """
    # Set default values if not provided
    if input_file is None:
        # Find the latest dynamic CW results file
        pattern = "output/simulation_results/coex_asymmetric_*dynamic-cw*.csv"
        files = glob.glob(pattern)
        if not files:
            print(f"No asymmetric simulation results found matching pattern: {pattern}")
            return
        input_file = max(files, key=os.path.getmtime)
        print(f"Using most recent results file: {input_file}")

    if output_dir is None:
        output_dir = "output/plots"

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load the data
    try:
        df = pd.read_csv(input_file)
        print(f"Loaded data with {len(df)} rows")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Check required columns
    required_columns = [
        "wifi_node_count", "nru_node_count",
        "wifi_channel_occupancy", "wifi_channel_efficiency", "wifi_collision_probability",
        "nru_channel_occupancy", "nru_channel_efficiency", "nru_collision_probability"
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        return

    # Group by node counts and calculate means of metrics
    grouped = df.groupby(['wifi_node_count', 'nru_node_count']).mean().reset_index()

    # Calculate AP:gNB ratios and add to dataframe
    grouped['ratio'] = grouped['wifi_node_count'] / grouped['nru_node_count']
    grouped['ratio_str'] = grouped.apply(lambda x: f"{int(x['wifi_node_count'])}:{int(x['nru_node_count'])}", axis=1)

    # Create a sorting key that arranges points as requested:
    # - APs with lowest values closer to zero
    # - For same AP count, order by increasing gNB count
    grouped['sort_key'] = grouped.apply(
        lambda x: (x['wifi_node_count'], x['nru_node_count']),
        axis=1
    )

    # Sort the dataframe
    grouped = grouped.sort_values('sort_key')

    # Set up nice plotting style - use style similar to the reference code
    sns.set_style("whitegrid")
    plt.rcParams.update({
        'font.size': 12,
        'axes.labelsize': 14,
        'axes.titlesize': 16,
        'xtick.labelsize': 26,
        'ytick.labelsize': 26,
        'legend.fontsize': 24,
        'figure.figsize': (12, 8)
    })

    # Set a colorblind-friendly palette as used in the reference code
    distinct_colors = [
        '#0072B2',  # blue
        '#D55E00',  # vermillion/orange
        '#009E73',  # green
        '#E69F00',  # orange/amber
        '#56B4E9',  # sky blue
        '#F0E442',  # yellow
        '#000000',  # black
    ]
    colors = [distinct_colors[0], distinct_colors[1]]  # Use first two colors for WiFi and NR-U
    wifi_color, nru_color = colors

    # Define metrics to plot
    metrics = [
        {
            'wifi': 'wifi_channel_occupancy',
            'nru': 'nru_channel_occupancy',
            'title': 'Channel Occupancy',
            'ylabel': 'Channel Occupancy',
            'filename': 'channel_occupancy.png',
            'ylim': (0, 0.7),  # Keep as percentage (0-1)
            'as_percentage': False  # Flag to indicate this should be shown as percentage
        },
        {
            'wifi': 'wifi_channel_efficiency',
            'nru': 'nru_channel_efficiency',
            'title': 'Channel Efficiency',
            'ylabel': 'Channel Efficiency',
            'filename': 'channel_efficiency.png',
            'ylim': (0, 0.7),  # Changed to normalized range (0-1)
            'as_percentage': False  # Show as normalized value
        },
        {
            'wifi': 'wifi_collision_probability',
            'nru': 'nru_collision_probability',
            'title': 'Collision Probability',
            'ylabel': 'Collision Probability',
            'filename': 'collision_probability.png',
            'ylim': (0, 0.09),  # Changed to normalized range (0-0.5)
            'as_percentage': False  # Show as normalized value
        }
    ]

    # Plot each metric
    for metric in metrics:
        fig, ax = plt.subplots(figsize=(12, 8))

        # Extract x positions and labels
        x_pos = np.arange(len(grouped))
        x_labels = grouped['ratio_str'].tolist()

        # Plot bars for WiFi and NR-U
        # Multiply by 100 only if we're displaying as percentage
        multiplier = 100 if metric['as_percentage'] else 1

        wifi_bars = ax.bar(x_pos - 0.2, grouped[metric['wifi']] * multiplier, width=0.4,
                          color=wifi_color, label='WiFi')
        nru_bars = ax.bar(x_pos + 0.2, grouped[metric['nru']] * multiplier, width=0.4,
                          color=nru_color, label='NR-U')

        # Add value labels on top of bars
        def add_labels(bars):
            for bar in bars:
                height = bar.get_height()
                # Format differently based on percentage or normalized value
                if metric['as_percentage']:
                    value_text = f'{height:.1f}'
                else:
                    value_text = f'{height:.3f}'

                # ax.annotate(value_text,
                            # xy=(bar.get_x() + bar.get_width() / 2, height),
                            # xytext=(0, 3),  # 3 points vertical offset
                            # textcoords="offset points",
                            # ha='center', va='bottom', fontsize=15)

        add_labels(wifi_bars)
        add_labels(nru_bars)

        # Set chart labels and title
        ax.set_xlabel('Wi-Fi:NR-U Node Ratio', fontsize=28)
        ax.set_ylabel(metric['ylabel'], fontsize=28)
        # ax.set_title(metric['title'])
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, rotation=45, ha='right')

        # Set y-axis limits based on metric
        ax.set_ylim(metric['ylim'])

        # Add grid and legend
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.legend(loc='best', fontsize=26)

        # Add horizontal line at 50% for channel occupancy (equal sharing)
        if metric['title'] == 'Channel Occupancy':
            ax.axhline(y=0.5, color='r', linestyle='--', alpha=0.6,
                       label='Equal sharing (0.5)')
            ax.legend()

        # Add horizontal line at 50% for channel efficiency (equal sharing)
        if metric['title'] == 'Channel Efficiency':
            ax.axhline(y=0.5, color='r', linestyle='--', alpha=0.6,
                       label='Best Efficiency (0.5)')
            ax.legend()

        # Save the figure
        plt.tight_layout()
        output_path = os.path.join(output_dir, metric['filename'])
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved {metric['title']} plot to {output_path}")
        plt.close()

    # Generate Fairness Index Plot
    if 'jain\'s_fairness_index' in grouped.columns and 'joint_airtime_fairness' in grouped.columns:
        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot fairness indices
        ax.plot(x_pos, grouped['jain\'s_fairness_index'], 'o-', color=distinct_colors[0],
                label='Jain\'s Fairness Index', linewidth=2.5)
        ax.plot(x_pos, grouped['joint_airtime_fairness'], 's--', color=distinct_colors[1],
                label='Joint Airtime Fairness', linewidth=2.5)

        # Add value labels
        # for i, (ji, jaf) in enumerate(zip(grouped['jain\'s_fairness_index'],
                                          # grouped['joint_airtime_fairness'])):
            # ax.annotate(f'{ji:.3f}', xy=(x_pos[i], ji), xytext=(0, 10),
                        # textcoords="offset points", ha='center', va='bottom')
            # ax.annotate(f'{jaf:.3f}', xy=(x_pos[i], jaf), xytext=(0, -15),
                        # textcoords="offset points", ha='center', va='top')

        # Set chart labels and title
        ax.set_xlabel('Wi-Fi:NR-U Node Ratio', fontsize=28)
        ax.set_ylabel('Fairness Index', fontsize=28)
        # ax.set_title('Fairness Indices')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, rotation=45, ha='right')
        ax.grid(linestyle='--', alpha=0.7)
        ax.legend(loc='best', fontsize=26)

        # Set y-axis range to better visualize fairness indices
        ax.set_ylim(0.8, 1.05)

        # Save the figure
        plt.tight_layout()
        output_path = os.path.join(output_dir, 'fairness_indices.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved fairness indices plot to {output_path}")
        # plt.show()
        plt.close()

    print("All plots generated successfully!")
    return grouped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot asymmetric coexistence simulation results')
    parser.add_argument('--input', type=str, help='Input CSV file path')
    parser.add_argument('--output-dir', type=str, help='Output directory for plots')
    args = parser.parse_args()

    results = plot_asymmetric_results(args.input, args.output_dir)