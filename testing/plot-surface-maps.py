# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Plot surface (or near-surface) maps of variables from WRF run(s)."""

# TODO:
# - fix aesthetics of plots, eg plots are overlapping colourbars
# - add colourbar labels with varname, units
# - check for identical domains between runs...
# - ..and plot diffs if domains are the same
# - take projection from wrf instead of hard coding NorthPolarStereo

import argparse
import datetime
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from matplotlib.backends.backend_pdf import PdfPages
from wrfinfra import generic
import wrfpp


# Functions

def new_page():
    """Create a new A4 page in current document.

    Returns
    -------
    matplotlib.Figure
        Handle to the figure object that represents the new page.

    """
    cm2in = 0.393701
    return plt.figure(figsize=(21 * cm2in, 29.7 * cm2in))


def add_title_page(pdf, runs):
    """Add title page to current document.

    Parameters
    ----------
    pdf: handle to PDF backend.
        The handle to the PDF backend.
    runs: [dict]
        The information about the runs.

    """
    ax = new_page().add_axes([0, 0, 1, 1])
    ax.text(0.5, 0.8, "Vertical profiles", ha="center", va="center")
    y = 0.6
    for i, run in enumerate(runs):
        ax.text(0.1, y, f"Run {i + 1}: {run['ds'].encoding['source']}")
        y -= 0.1
    plt.axis("off")
    pdf.savefig()
    plt.close()


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
    "--wrfouts",
    help=(
        "Comma-separated list of paths to the wrfout files. "
        "There must be one single file per simulation. Use ncrcat to first "
        "concatenate multiple files from a single simulation is nedded."
    ),
)
parser.add_argument(
    "--output",
    help="Path to output file. It must have the .pdf extension.",
    default="surface-maps.pdf",
)
args = parser.parse_args()


# Pre-process command-line arguments and run quality controls

variables = [var.strip() for var in args.variables.split(",")]
if args.start is not None:
    args.start = datetime.datetime.strptime(args.start, "%Y-%m-%d")
if args.end is not None:
    args.end = datetime.datetime.strptime(args.end, "%Y-%m-%d")
if not args.output.endswith(".pdf"):
    msg = "Parameter --output must have the .pdf extension."
    raise ValueError(msg)


# Open and prepare datasets

runs = []
for i_run, path in enumerate(args.wrfouts.split(",")):
    run = {"ds": xr.open_dataset(generic.process_path(path.strip())).wrf}
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


# Create the PDF with the plots

with PdfPages(args.output) as pdf:
    add_title_page(pdf, runs)

    for variable in variables:
        print(f"Plotting {variable} map...")

        fig = new_page()
        fig_width = 0.7
        fig_left = 0.2
        ax_width = 0.8*fig_width/len(runs)
        for i_run, run in enumerate(runs):
            left = fig_left + ax_width*i_run
            ax = fig.add_axes(
                [left, 0.2, ax_width, 0.6],
                projection=ccrs.NorthPolarStereo(),
            )

            print(f"    Processing run {i_run + 1}...")

            # Prepare dataset and arrays
            ds = run["ds"].wrf
            if "bottom_top" in getattr(ds, variable).dims:
                ds = ds.isel(bottom_top=0)
            elif "bottom_top_stag" in getattr(ds, variable).dims:
                ds = ds.isel(bottom_top_stag=0)

            array = getattr(ds, variable)
            data = array.isel(Time=run["time_idx"]).mean(axis=0)

            lon, lat = ds.wrf.lonlat_var(variable)
            C = ax.pcolormesh(
                lon,
                lat,
                data,
                transform=ccrs.PlateCarree()
            )
            plt.colorbar(C, ax=ax, shrink=0.4)
            ax.set_title(f"Run {i_run+1}")

        # Finalize the page
        fig.subplots_adjust(wspace=0.06)
        pdf.savefig()
        plt.close()

# Close connections to wrfout files

for run in runs:
    run["ds"].close()
