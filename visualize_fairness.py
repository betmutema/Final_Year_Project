import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse
import glob
import re
import itertools
import warnings
from cycler import cycler


def set_plot_style():
    """Set consistent plot style for all visualizations"""
    plt.rcParams.update({
        'font.size': 16,  # Increased base font size
        'axes.labelsize': 18,  # Increased label font size
        'axes.titlesize': 20,  # Increased title font size
        'xtick.labelsize': 16,  # Increased tick label font size
        'ytick.labelsize': 16,  # Increased tick label font size
        'legend.fontsize': 14,  # Increased legend font size
    })

    # Define a colorblind-friendly palette
    distinct_colors = [
        '#0072B2',  # blue
        '#D55E00',  # vermillion/orange
        '#009E73',  # green
        '#E69F00',  # orange/amber
        '#56B4E9',  # sky blue
        '#F0E442',  # yellow
        '#000000',  # black
    ]
    plt.rcParams['axes.prop_cycle'] = cycler('color', distinct_colors)

    # Return colors in case needed elsewhere
    return distinct_colors


def should_include_file(filename):
    """Determine if this file should be included in the analysis"""
    # Skip files with airtime_fairness or matching specific pattern
    if "airtime_fairness" in filename:
        return False
    if re.search(r'coex_gap-mode_desync-0-1000_disabled-backoff_adjusted-cw-\d+_raw-data', filename):
        return False

    # Include files with Varied_raw-data.csv
    if "Varied_raw-data.csv" in filename:
        return True

    # Include all other files that don't match exclusion patterns
    return True


def get_custom_legend(file_basename):
    """Extract a custom legend name from the filename"""
    # Special cases for specific filenames
    specific_mappings = {
        'coex_gap-mode_raw-data': 'NR-U Gap Mode',
        'coex_rs-mode_raw-data': 'NR-U RS Mode',
        'coex_gap-mode_desync-0-1000_raw-data': 'NR-U Gap Mode: Desync',
        'coex_gap-mode_desync-0-1000_disabled-backoff_raw-data': 'NR-U Gap Mode: Desync, no Backoff',
        'coex_gap-mode_desync-0-1000_disabled-backoff_dynamic-cw_raw-data': 'NR-U Gap Mode: Desync, no Backoff, adj.CW'
    }

    # Check if this is one of our specific mappings
    if file_basename in specific_mappings:
        return specific_mappings[file_basename]

    # If not a specific mapping, use the generic approach
    parts = []
    if 'gap-mode' in file_basename:
        parts.append('NR-U Gap Mode')
    elif 'rs-mode' in file_basename:
        parts.append('NR-U RS Mode')
    else:
        parts.append('NR-U')

    if 'desync' in file_basename and re.search(r'desync-(\d+-\d+)', file_basename):
        desync_value = re.search(r'desync-(\d+-\d+)', file_basename).group(1)
        parts.append(f"Desync {desync_value}")

    if 'disabled-backoff' in file_basename:
        parts.append("no Backoff")

    if 'adjusted-cw' in file_basename and re.search(r'adjusted-cw-(\d+)', file_basename):
        cw_value = re.search(r'adjusted-cw-(\d+)', file_basename).group(1)
        parts.append(f"adj.CW {cw_value}")
    elif 'adjusted-cw-Varied' in file_basename:
        parts.append("adj.CW")
    elif 'dynamic-cw' in file_basename:
        parts.append("adj.CW")

    if parts:
        return ": ".join(parts)
    else:
        return file_basename.replace('coex_', '').replace('_raw-data', '')


def create_fairness_plot(x_data, y_data, title, xlabel, ylabel, output_path, ylim=(0, 1), marker='o', linestyle='-',
                         color='blue', legend_title=None):
    """Create and save a plot with given data and parameters"""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x_data, y_data, marker=marker, linestyle=linestyle, color=color, linewidth=2)

    if legend_title:
        ax.legend([legend_title], loc='best', frameon=True, shadow=True, fontsize=14)

    ax.set_title(title, fontsize=20)
    ax.set_xlabel(xlabel, fontsize=18)
    ax.set_ylabel(ylabel, fontsize=18)
    ax.set_ylim(ylim)
    ax.grid(True, linestyle='--', alpha=0.7)  # Added grid with dashed lines
    ax.tick_params(axis='both', which='major', labelsize=16)

    plt.tight_layout()

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    plt.savefig(output_path)
    print(f"  Saved plot: {output_path}")
    # plt.show()
    plt.close(fig)


def plot_consolidated_fairness(
                               input_dir='output/simulation_results',
                               output_dir='output/metrics_visualizations/fairness_plots/consolidated'
                              ):
    """
    Create consolidated plots for Jain's fairness index and joint airtime fairness
    from multiple CSV files, with each file represented as a separate line.
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Find all CSV files in the input directory
        csv_files = glob.glob(os.path.join(input_dir, "*.csv"))

        # Filter files based on inclusion/exclusion criteria
        filtered_files = [f for f in csv_files if should_include_file(f)]

        if not filtered_files:
            print(f"No matching CSV files found in {input_dir}")
            return

        # print(f"Found {len(filtered_files)} CSV files to process for consolidated fairness plots")

        # Setup figures for consolidated plots
        fig_jfi = plt.figure(figsize=(10, 6))
        ax_jfi = fig_jfi.add_subplot(111)
        ax_jfi.set_title("Jain's Fairness Index Comparison", fontsize=20)
        ax_jfi.set_xlabel('Number of Nodes (WiFi and NRU)', fontsize=18)
        ax_jfi.set_ylabel("Jain's Fairness Index", fontsize=18)
        ax_jfi.grid(True, linestyle='--', alpha=0.7)  # Added grid with dashed lines
        ax_jfi.set_ylim(0.4, 1.05)
        ax_jfi.tick_params(axis='both', which='major', labelsize=16)

        fig_jaf = plt.figure(figsize=(10, 6))
        ax_jaf = fig_jaf.add_subplot(111)
        ax_jaf.set_title("Joint Airtime Fairness Comparison", fontsize=20)
        ax_jaf.set_xlabel('Number of Nodes (WiFi and NRU)', fontsize=18)
        ax_jaf.set_ylabel("Joint Airtime Fairness", fontsize=18)
        ax_jaf.grid(True, linestyle='--', alpha=0.7)  # Added grid with dashed lines
        ax_jaf.tick_params(axis='both', which='major', labelsize=16)

        # Define line styles, markers, and colors
        line_styles = ['-', '--', '-.', ':']
        markers = ['o', 's', '^', 'D', 'v', '*', 'x', '+']
        colors = set_plot_style()  # Use the same colors as in visualize_network_metrics.py

        # Create cyclers for styles, markers and colors
        style_cycler = itertools.cycle(line_styles)
        marker_cycler = itertools.cycle(markers)
        color_cycler = itertools.cycle(colors)

        # Process each file and add to consolidated plots
        for csv_file in filtered_files:
            try:
                # Get a short name for the legend
                file_basename = os.path.basename(csv_file).replace('.csv', '')

                # Get custom legend name
                custom_legend = get_custom_legend(file_basename)

                # Get next style, marker and color
                line_style = next(style_cycler)
                marker = next(marker_cycler)
                color = next(color_cycler)

                # Load the data
                print(f"  Processing {os.path.basename(csv_file)}")
                df = pd.read_csv(csv_file)

                # Check if required columns exist
                required_columns = ["wifi_node_count", "jain's_fairness_index", "joint_airtime_fairness"]
                if not all(col in df.columns for col in required_columns):
                    # print(f"  Warning: Required columns not found in {csv_file}. Skipping.")
                    continue

                # Group by node count and calculate averages
                df_avg = df.groupby('wifi_node_count').agg({
                    "jain's_fairness_index": 'mean',
                    "joint_airtime_fairness": 'mean'
                }).reset_index()

                # Add to consolidated plots with custom style
                ax_jfi.plot(df_avg['wifi_node_count'], df_avg["jain's_fairness_index"],
                            marker=marker, linestyle=line_style, color=color, linewidth=2, label=custom_legend)
                ax_jaf.plot(df_avg['wifi_node_count'], df_avg["joint_airtime_fairness"],
                            marker=marker, linestyle=line_style, color=color, linewidth=2, label=custom_legend)

            except Exception as e:
                print(f"  Error processing {csv_file}: {e}")

        # Finalize and save the plots
        ax_jfi.legend(loc='best', frameon=True, shadow=True, fontsize=14)
        plt.figure(fig_jfi.number)
        plt.tight_layout()
        output_file_jfi = os.path.join(output_dir, "consolidated_jains_fairness_index.png")
        plt.savefig(output_file_jfi, dpi=300)
        print(f"  Saved consolidated JFI plot to {output_file_jfi}")

        ax_jaf.legend(loc='best', frameon=True, shadow=True, fontsize=14)
        plt.figure(fig_jaf.number)
        plt.tight_layout()
        output_file_jaf = os.path.join(output_dir, "consolidated_joint_airtime_fairness.png")
        plt.savefig(output_file_jaf, dpi=300)
        print(f"  Saved consolidated JAF plot to {output_file_jaf}")

        plt.close('all')

    except Exception as e:
        warnings.warn(f"Error in plot_consolidated_fairness: {str(e)}")


def plot_individual_fairness(input_dir='output/simulation_results', output_dir='output/metrics_visualizations/fairness_plots/individual'):
    """
    Generate individual plots for each CSV file showing fairness metrics
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Find all CSV files in the input directory
        csv_files = glob.glob(os.path.join(input_dir, "*.csv"))

        # Filter files based on inclusion/exclusion criteria
        filtered_files = [f for f in csv_files if should_include_file(f)]

        if not filtered_files:
            print(f"No matching CSV files found in {input_dir}")
            return

        print(f"\nGenerating individual fairness plots for {len(filtered_files)} CSV files")

        for csv_file in filtered_files:
            try:
                # Get filename for plot title
                file_basename = os.path.basename(csv_file).replace('.csv', '')
                custom_title = get_custom_legend(file_basename)

                print(f"  Processing {file_basename}")

                # Load the data
                df = pd.read_csv(csv_file)

                # Check if required columns exist
                required_columns = ["wifi_node_count", "jain's_fairness_index", "joint_airtime_fairness"]
                if not all(col in df.columns for col in required_columns):
                    print(f"  Warning: Required columns not found in {csv_file}. Skipping.")
                    continue

                # Group by node count and calculate averages
                df_avg = df.groupby('wifi_node_count').agg({
                    "jain's_fairness_index": 'mean',
                    "joint_airtime_fairness": 'mean'
                }).reset_index()

                # Create subfolder for this file
                file_output_dir = os.path.join(output_dir, file_basename)
                os.makedirs(file_output_dir, exist_ok=True)

                # Plot Jain's Fairness Index
                jfi_output_path = os.path.join(file_output_dir, f"{file_basename}_jains_fairness_index.png")
                create_fairness_plot(
                    df_avg['wifi_node_count'],
                    df_avg["jain's_fairness_index"],
                    f"Jain's Fairness Index\n({custom_title})",
                    'Number of Nodes (WiFi and NRU)',
                    "Jain's Fairness Index",
                    jfi_output_path,
                    ylim=(0.4, 1.05),
                    color='blue'
                )

                # Plot Joint Airtime Fairness
                jaf_output_path = os.path.join(file_output_dir, f"{file_basename}_joint_airtime_fairness.png")
                create_fairness_plot(
                    df_avg['wifi_node_count'],
                    df_avg["joint_airtime_fairness"],
                    f"Joint Airtime Fairness\n({custom_title})",
                    'Number of Nodes (WiFi and NRU)',
                    "Joint Airtime Fairness",
                    jaf_output_path,
                    ylim=(0, 1),
                    color='green',
                    marker='s',
                    linestyle='--'
                )

            except Exception as e:
                print(f"  Error processing individual plot for {csv_file}: {e}")

    except Exception as e:
        warnings.warn(f"Error in plot_individual_fairness: {str(e)}")


def plot_fairness_by_categories(input_dir='output/simulation_results', output_dir='output/metrics_visualizations/fairness_plots/categories'):
    """
    Group files by categories and plot fairness metrics for each category
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Define categories and their patterns
        categories = {
            'basic': {
                'pattern': ['coex_gap-mode_raw-data.csv', 'coex_rs-mode_raw-data.csv'],
                'title': 'Basic Coexistence Modes'
            },
            'desync': {
                'pattern': ['coex_gap-mode_desync'],
                'exclude': ['disabled-backoff', 'adjusted-cw', 'dynamic-cw'],
                'title': 'Desynchronization Effects'
            },
            'backoff': {
                'pattern': ['disabled-backoff'],
                'exclude': ['adjusted-cw', 'dynamic-cw'],
                'title': 'Disabled Backoff Effects'
            },
            'cw_adjustment': {
                'pattern': ['adjusted-cw', 'dynamic-cw'],
                'title': 'Contention Window Adjustment Effects'
            }
        }

        # Find all CSV files in the input directory
        all_csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
        filtered_files = [f for f in all_csv_files if should_include_file(f)]

        if not filtered_files:
            print(f"No matching CSV files found in {input_dir}")
            return

        print(f"\nProcessing files by categories from {len(filtered_files)} filtered files")

        # Process each category
        for category, config in categories.items():
            category_files = []

            # Find files matching this category
            for csv_file in filtered_files:
                file_basename = os.path.basename(csv_file)

                # Check if file matches any pattern for this category
                matches_pattern = any(pattern in file_basename for pattern in config['pattern'])

                # Check if file should be excluded
                excluded = False
                if 'exclude' in config:
                    excluded = any(excl in file_basename for excl in config['exclude'])

                if matches_pattern and not excluded:
                    category_files.append(csv_file)

            if not category_files:
                print(f"  No files found for category: {category}")
                continue

            print(f"\n  Processing {len(category_files)} files for category: {category}")

            # Create category output directory
            category_output_dir = os.path.join(output_dir, category)
            os.makedirs(category_output_dir, exist_ok=True)

            # Setup figures for consolidated plots
            fig_jfi = plt.figure(figsize=(10, 6))
            ax_jfi = fig_jfi.add_subplot(111)
            ax_jfi.set_title(f"Jain's Fairness Index - {config['title']}", fontsize=20)
            ax_jfi.set_xlabel('Number of Nodes (WiFi and NRU)', fontsize=18)
            ax_jfi.set_ylabel("Jain's Fairness Index", fontsize=18)
            ax_jfi.grid(True, linestyle='--', alpha=0.7)  # Added grid with dashed lines
            ax_jfi.set_ylim(0.4, 1.05)
            ax_jfi.tick_params(axis='both', which='major', labelsize=16)

            fig_jaf = plt.figure(figsize=(10, 6))
            ax_jaf = fig_jaf.add_subplot(111)
            ax_jaf.set_title(f"Joint Airtime Fairness - {config['title']}", fontsize=20)
            ax_jaf.set_xlabel('Number of Nodes (WiFi and NRU)', fontsize=18)
            ax_jaf.set_ylabel("Joint Airtime Fairness", fontsize=18)
            ax_jaf.grid(True, linestyle='--', alpha=0.7)  # Added grid with dashed lines
            ax_jaf.tick_params(axis='both', which='major', labelsize=16)

            # Define line styles, markers, and colors
            line_styles = ['-', '--', '-.', ':']
            markers = ['o', 's', '^', 'D', 'v', '*', 'x', '+']
            colors = set_plot_style()

            # Create cyclers for styles, markers and colors
            style_cycler = itertools.cycle(line_styles)
            marker_cycler = itertools.cycle(markers)
            color_cycler = itertools.cycle(colors)

            # Process each file in this category
            for csv_file in category_files:
                try:
                    # Get a short name for the legend
                    file_basename = os.path.basename(csv_file).replace('.csv', '')
                    custom_legend = get_custom_legend(file_basename)

                    # Get next style, marker and color
                    line_style = next(style_cycler)
                    marker = next(marker_cycler)
                    color = next(color_cycler)

                    # Load the data
                    print(f"    Processing {os.path.basename(csv_file)}")
                    df = pd.read_csv(csv_file)

                    # Check if required columns exist
                    required_columns = ["wifi_node_count", "jain's_fairness_index", "joint_airtime_fairness"]
                    if not all(col in df.columns for col in required_columns):
                        print(f"    Warning: Required columns not found in {csv_file}. Skipping.")
                        continue

                    # Group by node count and calculate averages
                    df_avg = df.groupby('wifi_node_count').agg({
                        "jain's_fairness_index": 'mean',
                        "joint_airtime_fairness": 'mean'
                    }).reset_index()

                    # Add to plots with custom style
                    ax_jfi.plot(df_avg['wifi_node_count'], df_avg["jain's_fairness_index"],
                                marker=marker, linestyle=line_style, color=color, linewidth=2, label=custom_legend)
                    ax_jaf.plot(df_avg['wifi_node_count'], df_avg["joint_airtime_fairness"],
                                marker=marker, linestyle=line_style, color=color, linewidth=2, label=custom_legend)

                except Exception as e:
                    print(f"    Error processing {csv_file} for category {category}: {e}")

            # Finalize and save the plots
            ax_jfi.legend(loc='best', frameon=True, shadow=True, fontsize=14)
            plt.figure(fig_jfi.number)
            plt.tight_layout()
            output_file_jfi = os.path.join(category_output_dir, f"{category}_jains_fairness_index.png")
            plt.savefig(output_file_jfi, dpi=300)
            print(f"    Saved {category} JFI plot to {output_file_jfi}")

            ax_jaf.legend(loc='best', frameon=True, shadow=True, fontsize=14)
            plt.figure(fig_jaf.number)
            plt.tight_layout()
            output_file_jaf = os.path.join(category_output_dir, f"{category}_joint_airtime_fairness.png")
            plt.savefig(output_file_jaf, dpi=300)
            print(f"    Saved {category} JAF plot to {output_file_jaf}")

            plt.close('all')

    except Exception as e:
        warnings.warn(f"Error in plot_fairness_by_categories: {str(e)}")


def generate_summary():
    """Generate a summary of all fairness plots created"""
    try:
        print("\n=== Summary of Generated Fairness Plots ===")

        count = 0
        for root, dirs, files in os.walk('output/metrics_visualizations/fairness_plots'):
            for file in files:
                if file.endswith('.png'):
                    count += 1

        print(f"\nTotal number of generated fairness plots: {count}")
    except Exception as e:
        warnings.warn(f"Error generating summary: {str(e)}")


def main():
    """Main function to coordinate the fairness analysis and plotting"""
    parser = argparse.ArgumentParser(description='Generate fairness metric plots')
    parser.add_argument('--dir', type=str, default='output/simulation_results',
                        help='Directory containing CSV files to process')
    parser.add_argument('--output', type=str, default='output/metrics_visualizations/fairness_plots',
                        help='Base directory where to save the plots')
    parser.add_argument('--individual', action='store_true', default=True,
                        help='Generate individual plots for each file')
    parser.add_argument('--categories', action='store_true', default=True,
                        help='Generate plots by categories')
    parser.add_argument('--consolidated', action='store_true', default=True,
                        help='Generate consolidated plots')

    args = parser.parse_args()

    # print("\n=== Starting Fairness Visualization Process ===\n")

    # Set plot style
    set_plot_style()

    # Generate consolidated plots
    if args.consolidated:
        # print("\n--- Generating Consolidated Fairness Plots ---")
        consolidated_output_dir = os.path.join(args.output, 'consolidated')
        plot_consolidated_fairness(args.dir, consolidated_output_dir)

    # Generate individual plots if requested
    if args.individual:
        print("\n--- Generating Individual Fairness Plots ---")
        individual_output_dir = os.path.join(args.output, 'individual')
        plot_individual_fairness(args.dir, individual_output_dir)

    # Generate category plots if requested
    if args.categories:
        print("\n--- Generating Category-based Fairness Plots ---")
        categories_output_dir = os.path.join(args.output, 'categories')
        plot_fairness_by_categories(args.dir, categories_output_dir)

    # Generate summary
    generate_summary()

    print("\n=== Fairness Visualization Complete ===\n")


if __name__ == "__main__":
    main()