# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Plot surface (or otherwise single-level) maps of variables from WRF run(s)."""

import os
import argparse
import itertools
import datetime
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from wrfinfra import generic
import wrfpp

# Command-line arguments

parser = argparse.ArgumentParser(
    description="Plot (near-)surface maps of variables from WRF run(s).",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--variables",
    help="Comma-separated list of variables to plot",
    default="T2",
)
parser.add_argument(
    "--start",
    help=(
        "Start date (YYYY-mm-dd) of the averaging period. "
        "If None, then use the entire simulation."
    ),
    default=None,
)
parser.add_argument(
    "--end",
    help=(
        "End date (YYYY-mm-dd) of the averaging period. "
        "If None, then use the entire simulation."
    ),
    default=None,
)
parser.add_argument(
    "--metrics",
    help="Comma-separated list of metrics to plot.",
    default="mean,min,max",
)
parser.add_argument(
    "--wrfouts",
    help=(
        "Comma-separated list of paths to the wrfout files. "
        "There must be one single file per simulation. Use ncrcat to first "
        "concatenate multiple files from a single simulation is needed."
    ),
)
parser.add_argument(
    "--output-dir",
    help="Path to output directory.",
    default=os.getcwd(),
)
parser.add_argument(
    "--license",
    help="License to use for the content created by this script.",
    default="CC-BY-SA-4.0",
)
args = parser.parse_args()

# Pre-process command-line arguments and run quality controls

variables = [var.strip() for var in args.variables.split(",")]
if args.start is not None:
    args.start = datetime.datetime.strptime(args.start, "%Y-%m-%d")
if args.end is not None:
    args.end = datetime.datetime.strptime(args.end, "%Y-%m-%d")
metrics = [metric.strip() for metric in args.metrics.split(",")]

# Open and prepare datasets

runs = []
for i_run, path in enumerate(args.wrfouts.split(",")):
    run = {"ds": wrfpp.open_dataset(generic.process_path(path.strip()))}
    times = list(run["ds"]["XTIME"].values)
    dt = run["ds"].dt

    # Process start date
    if args.start is not None:
        run["start"] = args.start
    elif i_run == 0:
        run["start"] = times[0]
    elif times[0] != runs[0]["start"]:
        msg = "Inconsistent start dates across runs."
        raise RuntimeError(msg)
    else:
        run["start"] = runs[0]["start"]

    # Process end date
    if args.end is not None:
        run["end"] = args.end
    elif i_run == 0:
        run["end"] = times[-1] + dt
    elif times[-1] + dt != runs[0]["end"]:
        msg = "Inconsistent end dates across runs."
        raise RuntimeError(msg)
    else:
        run["end"] = runs[0]["end"]

    # Get time indices for period of interest
    run["time_idx"] = range(
        times.index(run["start"]), times.index(run["end"] - dt) + 1
    )

    runs.append(run)

# Create the output markdown file and the plots

basename = os.path.basename(__file__)[:-3]
if basename.startswith("plot-") and len(basename) > 5:
    basename = basename[5:]

if not os.path.isdir(args.output_dir):
    os.mkdir(args.output_dir)

with open(os.path.join(args.output_dir, f"{basename}.md"), mode="x") as f:
    f.write(f"License: {args.license}.\n")
    f.write("\n# Surface maps\n")

    for metric, variable in itertools.product(metrics, variables):
        print(f"Plotting map: {metric} of {variable}...")

        npnanmetric = getattr(np, f"nan{metric}")

        # Select values for the colourbar min and max
        print("    Preparing colour scale...")
        minvals, maxvals = [], []
        for irun, run in enumerate(runs):
            ds = run["ds"]
            array = getattr(ds, variable)
            if "bottom_top" in array.dims:
                array = array.isel(bottom_top=0)
            elif "bottom_top_stag" in array.dims:
                array = array.isel(bottom_top_stag=0)
            data = npnanmetric(array.isel(Time=run["time_idx"]), axis=0)
            minvals.append(np.ma.amin(data))
            maxvals.append(np.ma.amax(data))
        vmin = np.amin(minvals)
        vmax = np.amax(maxvals)

        # Here we assume that all files use the same projection
        fig, axes = plt.subplots(
            ncols=len(runs), subplot_kw={"projection": ds.crs}
        )
        for i_run, run in enumerate(runs):
            print(f"    Processing run {i_run + 1}...")

            # Prepare dataset and arrays
            ds = run["ds"]
            array = getattr(ds, variable)
            if "bottom_top" in array.dims:
                array = array.isel(bottom_top=0)
            elif "bottom_top_stag" in array.dims:
                array = array.isel(bottom_top_stag=0)
            data = npnanmetric(array.isel(Time=run["time_idx"]), axis=0)
            lon, lat = ds.lonlat_var(variable)

            # Prepare axes and plot
            axes[i_run].coastlines()
            plot = axes[i_run].pcolormesh(
                lon,
                lat,
                data,
                transform=ccrs.PlateCarree(),
                vmin=vmin,
                vmax=vmax,
                rasterized=True,
            )
            axes[i_run].set_title(f"Run {i_run + 1}")

        title = f"{metric[0].upper()}{metric[1:]} of {variable}"
        plt.suptitle(title)
        plt.colorbar(
            plot,
            ax=axes,
            label=f"{metric} of {variable} ({ds.units_mpl(variable)})",
            orientation="horizontal",
        )

        # Finalize and save the plot
        filename = f"{basename}_{variable}_{metric}.png"
        plt.savefig(os.path.join(args.output_dir, filename), dpi=300)
        plt.close()

        # Add the plot to the markdown file
        f.write(f"\n## {title}\n")
        f.write(f"\n![{title}](./{filename})\n")

# Close connections to wrfout files

for run in runs:
    run["ds"].close()
