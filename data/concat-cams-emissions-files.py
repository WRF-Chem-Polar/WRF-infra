# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Concatenate CAMS emissions files.

Incentive to use this script: when downloading CAMS anthropogenic emissions
data, we obtain one file per requested year, and the time units in these files
("months since ...") are non CF-compliant, which makes using ncrcat
difficult. This script handles properly this situation.

"""

import os
import sys
import argparse
import datetime
import numpy as np
from netCDF4 import Dataset


def plus_one_month(year, month):
    """Advance given date by one month.

    Parameters
    ----------
    year: int
        The start year.
    month: int
        The start month.

    Returns
    -------
    int
        The year of given date + one month.
    int
        The month of given date + one month.

    """
    if int(month) != month or month < 1 or month > 12:
        msg = "Bad month value."
        raise ValueError(msg)
    month = month + 1
    if month == 13:
        month = 1
        year = year + 1
    return year, month


# Command-line arguments
script_name = os.path.basename(__file__)
parser = argparse.ArgumentParser(
    description="Concatenate CAMS emissions files.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--filepaths",
    help="Comma-separated list of files to concatenate.",
    required=True,
)
parser.add_argument(
    "--output",
    help="Path to the output file (must not already exist).",
    default=f"{script_name[:-3]}_out.nc",
)
parser.add_argument(
    "--date-ref",
    help=(
        "Reference date for units of timestamps "
        " (seconds since ...) Format: YYYY-MM-DD."
    ),
    default="1990-01-01",
)
args = parser.parse_args()
filepaths = sorted(f.strip() for f in args.filepaths.split(","))
date_ref = datetime.datetime.strptime(args.date_ref, "%Y-%m-%d")

# Prepare input files and initialize variables
nc_in_all = [Dataset(f, mode="r") for f in filepaths]
ntimes = sum(nc.dimensions["time"].size for nc in nc_in_all)

# Process each file...
itime = 0
for i, nc_in in enumerate(nc_in_all):
    if i == 0:
        # Create the output file
        nc_out = Dataset(args.output, mode="x")

        # Create the dimensions in the output file
        for varname, dim in nc_in.dimensions.items():
            size = ntimes if varname == "time" else dim.size
            nc_out.createDimension(varname, size)

        # Create the variables in the output file
        for varname, var_in in nc_in.variables.items():
            dtype = float if varname == "time" else var_in.dtype
            args, kwargs = [varname, dtype, var_in.dimensions], {}
            if "_FillValue" in var_in.ncattrs():
                kwargs["fill_value"] = getattr(var_in, "_FillValue")
            var_out = nc_out.createVariable(*args, **kwargs)
            for attr in [a for a in var_in.ncattrs() if a != "_FillValue"]:
                setattr(var_out, attr, getattr(var_in, attr))
            if varname == "time":
                units = f"seconds since {date_ref.strftime('%Y-%m-%d')}"
                var_out.units = units

        # Create the global attributes in the output file
        for attr in nc_in.ncattrs():
            setattr(nc_out, attr, getattr(nc_in, attr))

    else:
        # Check dimensions between input file and output file
        if sorted(nc_in.dimensions.keys()) != sorted(nc_out.dimensions.keys()):
            msg = "Inconsistent list of dimensions."
            raise ValueError(msg)
        for varname, dim_in in nc_in.dimensions.items():
            size = ntimes if varname == "time" else dim_in.size
            if size != nc_out.dimensions[varname].size:
                msg = f"Inconsistent dimension: {varname}."
                raise ValueError(msg)

        # Check variables between input file and output file
        if sorted(nc_in.variables.keys()) != sorted(nc_out.variables.keys()):
            msg = "Inconsistent list of variables."
            raise ValueError(msg)
        for varname, var_in in nc_in.variables.items():
            var_out = nc_out.variables[varname]
            if var_in.dimensions != var_out.dimensions:
                msg = f"Inconsistent dimensions for variable {varname}."
            for attr in var_in.ncattrs():
                if varname == "time" and attr == "units":
                    continue
                attr_in = getattr(var_in, attr)
                attr_out = getattr(var_out, attr)
                if isinstance(attr_in, str):
                    ok = attr_in == attr_out
                else:
                    ok = (
                        np.isnan(attr_in)
                        and np.isnan(attr_out)
                        or attr_in == attr_out
                    )
                if not ok:
                    msg = f"Inconsistent attribute {attr} for {varname}."
                    raise ValueError(msg)

        # Check global attributes between input file and output file
        if sorted(nc_in.ncattrs()) != sorted(nc_out.ncattrs()):
            msg = "Inconsistent list of global attributes."
            raise ValueError(msg)
        for attr in nc_in.ncattrs():
            if getattr(nc_in, attr) != getattr(nc_out, attr):
                msg = f"Inconsistent values for global attribute {attr}."
                raise ValueError(msg)

    # Put the values in the output file
    ntimes_in = nc_in.dimensions["time"].size
    for varname, var_out in nc_out.variables.items():
        dims = var_out.dimensions
        var_in = nc_in.variables[varname]

        # The time variable needs separate processing
        if varname == "time":
            if dims != ("time",):
                msg = "Unexpected dimensions for time."
                raise ValueError(msg)
            # Process the units
            units = var_in.units
            fmt = "months since %Y-%m-%d"
            try:
                date_since = datetime.datetime.strptime(units, fmt)
            except ValueError:
                msg = "Unexpected units for time."
                raise ValueError(msg)
            if date_since.day != 1:
                msg = "This date reference is not ok for 'months since...'."
                raise ValueError(msg)
            # Calculate proper time steps
            year, month = date_since.year, date_since.month
            dates = []
            for j in range(ntimes_in):
                if var_in[j] != j:
                    msg = "Unexpected time stamp."
                    raise ValueError(msg)
                new_date = datetime.datetime.strptime(
                    f"{year}-{month}-01", "%Y-%m-%d"
                )
                dates.append(new_date)
                year, month = plus_one_month(year, month)
            timestamps = [(d - date_ref).total_seconds() for d in dates]
            var_out[itime : itime + ntimes_in] = timestamps

        else:
            # Process the other variables
            if dims == ("lon",) or dims == ("lat",):
                if i == 0:
                    var_out[:] = var_in[:]
                elif np.any(var_out[:] != var_in[:]):
                    msg = f"Inconsistent values for {varname}."
                    raise ValueError(msg)
            elif dims == ("time", "lat", "lon"):
                var_out[itime : itime + ntimes_in, :, :] = var_in[:, :, :]
            else:
                msg = f"Unknown dimensions: ({', '.join(dims)})."

    itime += ntimes_in

# Make sure that timestamps represent monthly data
times = nc_out["time"][:]
timestamps = [date_ref + datetime.timedelta(seconds=t) for t in times]
for i, timestamp in enumerate(timestamps):
    if timestamp.strftime("%d %H:%M:%S") != "01 00:00:00":
        msg = "Bad timestamp (residual values)."
        raise ValueError(msg)
    if i == 0:
        year, month = timestamp.year, timestamp.month
    else:
        year, month = plus_one_month(year, month)
        if timestamp.year != year or timestamp.month != month:
            msg = "Bad timestamps (not monthly values)."
            raise ValueError(msg)

# Update the history global attribute
try:
    history = nc_out.history
except AttributeError:
    history = ""
else:
    history += " ; "
now = datetime.datetime.now(datetime.UTC)
history += f"{str(now)}: {script_name} {' '.join(sys.argv[1:])}"
setattr(nc_out, "history", history)

# Close all open connections
nc_out.close()
for nc in nc_in_all:
    nc.close()
