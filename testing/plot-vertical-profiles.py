# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Plot vertical profiles at specific locations for WRF run(s)."""

import os
import argparse
from itertools import product
from collections import namedtuple
import datetime
import matplotlib.pyplot as plt
from wrfinfra import generic
import wrfpp

# Types and functions

Location = namedtuple("Location", "name lon lat")
Variable = namedtuple("Variable", "name window")


def parse_location(location):
    """Parse location (typically obtained from command-line arguments).

    Parameters
    ----------
    location: str
        Location specified as "name:longitude:latitude".

    Returns
    -------
    Location
        The given location parsed as a named tuple.

    """
    split = location.split(":")
    return Location(split[0].strip(), float(split[1]), float(split[2]))


def parse_variable(variable):
    """Parse variable (typically obtained from command-line arguments).

    Parameters
    ----------
    variable: str
        Variable specified as "name" or "name:window".

    Returns
    -------
    Variable
        The given variable parsed as a named tuple.

    """
    split = variable.split(":")
    name = split[0].strip()
    try:
        window = split[1]
    except IndexError:
        window = 1
    else:
        window = int(window)
    return Variable(name, window)


# Command-line arguments

parser = argparse.ArgumentParser(
    description="Plot vertical profiles at specific locations for WRF run(s).",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--variables",
    help="Comma-separated list of variables to plot",
    default="o3,air_temperature",
)
parser.add_argument(
    "--locations",
    help=(
        "Comma-separated list of locations to plot. A location is a "
        "triplet of name:lon:lat."
    ),
    default="North Pole:0:90",
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
    "--output-dir",
    help="Path to output directory.",
    default=os.getcwd(),
)
parser.add_argument(
    "--markdown-file",
    help="Name of the markdown file.",
    default="vertical-profiles.md",
)
parser.add_argument(
    "--license",
    help="License to use for the content created by this script.",
    default="CC-BY-SA-4.0",
)
args = parser.parse_args()

# Pre-process command-line arguments and run quality controls

variables = [parse_variable(var) for var in args.variables.split(",")]
locations = [parse_location(loc) for loc in args.locations.split(",")]
if args.start is not None:
    args.start = datetime.datetime.strptime(args.start, "%Y-%m-%d")
if args.end is not None:
    args.end = datetime.datetime.strptime(args.end, "%Y-%m-%d")

# Hard-coded graphical parameters

colors = ("r", "b", "k", "y", "m")
linestyles = ("-", "--", ":")
markers = ("o", "^", "v", "*", "+", "s")

# Other hard-coded parameters

variable_z_axis = "altitude_agl_c"
dont_drop_these_variables = (
    "XLONG",
    "XLAT",
    "XLONG_U",
    "XLAT_U",
    "XLONG_V",
    "XLAT_V",
    # Variables listed below are used in the calculation of derived variables
    "HGT",
    "MAPFAC_M",
    "P",
    "PB",
    "PH",
    "PHB",
    "QVAPOR",
    "QCLOUD",
    "QRAIN",
    "QICE",
    "QSNOW",
    "QGRAUP",
    "QHAIL",
    "RAINC",
    "RAINNC",
    "T",
)

# Open and prepare datasets

runs = []
for i_run, path in enumerate(args.wrfouts.split(",")):
    run = {"ds": wrfpp.open_dataset(generic.process_path(path.strip())).wrf}
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

    # Drop needless variables (the use of value_around_point later on can lead
    # to memory errors if performed on large numbers of variables at once)
    drop_variables = set(run["ds"].variables.keys())
    drop_variables -= set([var.name for var in variables])
    drop_variables -= set(dont_drop_these_variables)
    run["ds"] = run["ds"].drop_vars(drop_variables).wrf

    runs.append(run)

# Create the output markdown file and the plots

basename = os.path.basename(__file__)[:-3]
if basename.startswith("plot-") and len(basename) > 5:
    basename = basename[5:]

if not os.path.isdir(args.output_dir):
    os.mkdir(args.output_dir)

with open(os.path.join(args.output_dir, args.markdown_file), mode="x") as f:
    f.write(f"License: {args.license}.\n")
    f.write("\n# Vertical profiles\n")

    for variable, location in product(variables, locations):
        print(f"Plotting {variable.name} at {location.name}...")

        lon, lat = location.lon, location.lat
        fig = plt.figure()
        ax = fig.add_axes([0.2, 0.2, 0.7, 0.6])

        for i_run, run in enumerate(runs):
            print(f"    Processing run {i_run + 1}...")

            # Prepare dataset and arrays
            ds = run["ds"].value_around_point(
                lon, lat, method="mean", window=variable.window
            )
            ds = ds.wrf
            array_x = getattr(ds, variable.name)
            array_y = getattr(ds, variable_z_axis)

            # Plot the profiles
            x = array_x.isel(Time=run["time_idx"]).mean(axis=0)
            y = array_y.isel(Time=run["time_idx"]).mean(axis=0)
            ax.plot(
                x,
                y,
                markers[i_run % len(markers)]
                + linestyles[i_run % len(linestyles)],
                color=colors[i_run % len(colors)],
                markersize=3,
                label=f"Run {i_run + 1}",
            )

        # Format the plot
        ax.set_ylim(y.min(), y.max())
        ax.legend()
        ax.set_xlabel(f"{variable.name} ({ds.units_mpl(variable.name)})")
        ax.set_ylabel(f"{array_y.name} ({ds.units_mpl(variable_z_axis)})")
        lon_formatted = f"{abs(lon)}{'E' if lon > 0 else 'W'}"
        lat_formatted = f"{abs(lat)}{'N' if lat > 0 else 'S'}"
        loclonlat = f"{location.name} ({lon_formatted}, {lat_formatted})"
        ax.set_title(
            f"Vertical profile of {variable.name} at {loclonlat}"
            f"\n(window = {variable.window})"
        )

        # Finalize and save the plot
        loclonlat = f"{location.name}_{lon_formatted}_{lat_formatted}"
        varwindow = f"{variable.name}_{variable.window}"
        filename = f"{basename}_{varwindow}_{loclonlat}.png"
        plt.savefig(os.path.join(args.output_dir, filename), dpi=300)
        plt.close()

        # Add the plot to the markdown file
        f.write(f"\n## {variable.name} at {location.name}\n")
        alt_text = f"Vertical profile of {variable.name} at {location.name}"
        f.write(f"\n![{alt_text}](./{filename})\n")

# Close connections to wrfout files

for run in runs:
    run["ds"].close()
