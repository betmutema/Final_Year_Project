import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from cycler import cycler
import re
import warnings

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
        '#CC79A7',  # pink
        '#E69F00',  # orange/amber
        '#56B4E9',  # sky blue
        '#F0E442',  # yellow
        '#000000',  # black
    ]
    mpl.rcParams['axes.prop_cycle'] = cycler('color', distinct_colors)

    # Return the colors in case needed elsewhere
    return distinct_colors


def extract_parameters(filename):
    """Extract parameters from filename"""
    # Example: airtime_fairness_nru-5_wifi-10.csv
    match = re.search(r"airtime_fairness_nru-(\d+)_wifi-(\d+)", filename)
    if match:
        return f"NR-U: {match.group(1)}, Wi-Fi: {match.group(2)}"
    return "unknown"


def create_plot(df, x_col, y_cols, labels, title, xlabel, ylabel, output_path, ylim=(0, 1), show_plot=False):
    """Create and save a plot with given data and parameters"""
    fig, ax = plt.subplots()

    # Group by x_col and calculate mean values for each y_col
    grouped_data = [df.groupby([x_col])[y_col].mean() for y_col in y_cols]

    # Plot each data series
    for i, (data, label) in enumerate(zip(grouped_data, labels)):
        linestyle = '--' if i % 2 == 0 else '-'
        data.plot(marker="o", linestyle=linestyle, label=label, ax=ax)

    ax.set_ylim(*ylim)
    ax.legend(loc = 'best')
    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    # ax.set_title(title, fontsize=14)
    plt.tight_layout()

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save the plot
    # plt.show()
    plt.savefig(output_path)
    print(f"  Saved plot: {output_path}")

    if show_plot:
        plt.show()

    plt.close(fig)
    return output_path


def process_equal_airtime_data(csv_pattern="output/simulation_results/airtime_fairness*.csv",
                               output_dir="output/metrics_visualizations/airtime_fairness",
                               show_plots=False):
    """Process equal airtime data from CSV files and create plots"""
    print("\n=== Starting Equal Airtime Metrics Visualization Process ===\n")

    # Set color palette (without notification)
    #    set_color_palette('viridis', 0.0, 1.0, 4)

    set_distinct_color_palette()

    # Get list of matching CSV files
    simulation_results = glob.glob(csv_pattern)

    if not simulation_results:
        warnings.warn(f"No CSV files found matching pattern '{csv_pattern}'.")
        return []

    print(f"Found {len(simulation_results)} CSV files to process:")
    for i, file_path in enumerate(simulation_results):
        params = extract_parameters(os.path.basename(file_path))
        print(f"{i + 1}. {os.path.basename(file_path)}")

    results = []

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nOutput directory created: {output_dir}")

    print("\nGenerating channel cccupancy plots for equal airtime data:")

    for csv_file in simulation_results:
        try:
            # Extract base filename for plot naming
            base_filename = os.path.splitext(os.path.basename(csv_file))[0]
            params = extract_parameters(os.path.basename(csv_file))
            print(f"\nProcessing file: {base_filename}.csv")

            # Generate plot name for Channel Occupancy
            cot_output = os.path.join(output_dir, f"{base_filename}.png")

            # Read CSV into DataFrame
            df = pd.read_csv(csv_file)
            # print(f"  Loaded data with {len(df)} rows and {len(df.columns)} columns")

            # Create Channel Occupancy plot
            saved_path = create_plot(
                df=df,
                x_col='CW',
                y_cols=['wifi_channel_occupancy', 'nru_channel_occupancy'],
                labels=['Wi-Fi', 'NR-U'],
                title='Channel Occupancy vs Contention Window Size',
                xlabel='Wi-Fi Contention Window',
                ylabel='Channel Occupancy',
                output_path=cot_output,
                ylim=(0, 1),
                show_plot=show_plots
            )
            results.append(saved_path)

        except Exception as e:
            warnings.warn(f"Error processing file {csv_file}: {str(e)}")

    # Print summary of generated files
    print("\n=== Summary of Generated Output Files ===")
    print(f"\nTotal number of generated plots: {len(results)}")

    # Group files by directory for cleaner output
    # output_dirs = sorted(set([os.path.dirname(f) for f in results]))
    #     for dir in output_dirs:
    #         files_in_dir = [os.path.basename(f) for f in results if os.path.dirname(f) == dir]
    #         print(f"\n  {dir} ({len(files_in_dir)} files):")
    #         for file in sorted(files_in_dir):
    #             print(f"    - {file}")

    print("\n=== Equal Airtime Metrics Visualization Complete ===\n")
    return results


def main():
    """Main function to run the script"""
    process_equal_airtime_data()


if __name__ == "__main__":
    main()