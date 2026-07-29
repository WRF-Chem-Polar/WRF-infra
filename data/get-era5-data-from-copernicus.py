# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Get WRF/WRF-Chem-relevant ERA5 data from the Copernius climate data store.

To use this script, you must have an account at:

https://cds.climate.copernicus.eu/.

and you must have properly created the file ~/.cdsapirc with your credentials.

The cdsapi package can be installed via pip or conda-forge.

Below are listed some decisions we have made in this script:

 - We download data in the GRIB format.
 - We download one file per day, but we group files by year in directories.

"""

import argparse
import os
from datetime import date, timedelta

import cdsapi

# Command-line arguments

parser = argparse.ArgumentParser(
    description="Download ERA5 data from the Copernicus climate data store",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--start-date",
    help="First day of the period of interest (format: YYYY-MM-DD).",
    required=True,
)
parser.add_argument(
    "--end-date",
    help="Last day of the period of interest (format: YYYY-MM-DD).",
    required=True,
)
parser.add_argument(
    "--box",
    help=(
        "Region of interest (4 numbers: min_lon, max_lon, min_lat, max_lat). "
        "Longitude in [-180, 180]. Latitude in [-90, 90]. "
        "Default is entire globe."
    ),
    nargs=4,
    default=(-180, 180, -90, 90),
)
parser.add_argument(
    "--workdir",
    help="Directory where to download the data. It must already exist.",
    default=".",
)
parser.add_argument(
    "--overwrite",
    help="Whether to overwrite existing files.",
    choices=["true", "false"],
    default="false",
)
args = parser.parse_args()

# Pre-process command-line arguments

start_date = date.strptime(args.start_date, "%Y-%m-%d")
end_date = date.strptime(args.end_date, "%Y-%m-%d")
box = tuple(float(v) for v in args.box)
if box[0] < -180 or box[1] > 180 or box[0] >= box[1]:
    msg = "Bad longitude specification."
    raise ValueError(msg)
if box[2] < -90 or box[3] > 90 or box[2] >= box[3]:
    msg = "Bad latitude specification."
    raise ValueError(msg)
dir_work = os.path.abspath(os.path.expanduser(args.workdir))
overwrite = args.overwrite == "true"

# Hard-coded parameters

one_day = timedelta(days=1)
dataset_pressure_levels = "reanalysis-era5-pressure-levels"
dataset_single_levels = "reanalysis-era5-single-levels"
pressure_levels = [
    "1",
    "2",
    "3",
    "5",
    "7",
    "10",
    "20",
    "30",
    "50",
    "70",
    "100",
    "125",
    "150",
    "175",
    "200",
    "225",
    "250",
    "300",
    "350",
    "400",
    "450",
    "500",
    "550",
    "600",
    "650",
    "700",
    "750",
    "775",
    "800",
    "825",
    "850",
    "875",
    "900",
    "925",
    "950",
    "975",
    "1000",
]
variables_pressure_levels = (
    "geopotential",
    "temperature",
    "relative_humidity",
    "u_component_of_wind",
    "v_component_of_wind",
)
variables_single_levels = (
    "2m_temperature",
    "2m_dewpoint_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "surface_pressure",
    "mean_sea_level_pressure",
    "sea_surface_temperature",
    "sea_ice_cover",
    "skin_temperature",
    "snow_depth",
    "soil_temperature_level_1",
    "soil_temperature_level_2",
    "soil_temperature_level_3",
    "soil_temperature_level_4",
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",
    "volumetric_soil_water_layer_4",
)

# Prepare API connection and request

client = cdsapi.Client()
request = {
    "product_type": ["reanalysis"],
    "data_format": "grib",
    "download_format": "unarchived",
    "time": ["00:00", "06:00", "12:00", "18:00"],
    "area": [box[3], box[0], box[2], box[1]],
    "format": "grib",
}

# We download data for each day separately

loop_day = start_date
while loop_day <= end_date:
    print("Processing date", loop_day, "...")
    year, month, day = loop_day.strftime("%Y-%m-%d").split("-")

    # Prepare the work directory
    dir_data = os.path.join(dir_work, f"ERA_grib1_{year}")
    try:
        os.mkdir(dir_data)
    except FileExistsError:
        if not os.path.isdir(dir_data):
            msg = "Target {dir_data} exists but is not a directory."
            raise FileExistsError(msg)

    # Prepare the request
    request["year"] = year
    request["month"] = month
    request["day"] = day

    # Retrieve data on pressure levels
    request["pressure_level"] = pressure_levels
    request["variable"] = variables_pressure_levels
    filepath = os.path.join(dir_data, f"e5.pl.{year}{month}{day}.grib")
    if not os.path.lexists(filepath) or overwrite:
        print(f"    > Retrieving {filepath}...")
        client.retrieve(dataset_pressure_levels, request, filepath)
    else:
        print(f"    > File {filepath} already exists, not overwriting...")

    # Retrieve single-level data
    request.pop("pressure_level")
    request["variable"] = variables_single_levels
    filepath = os.path.join(dir_data, f"e5.sfc.{year}{month}{day}.grib")
    if not os.path.lexists(filepath) or overwrite:
        print(f"    > Retrieving {filepath}...")
        client.retrieve(dataset_single_levels, request, filepath)
    else:
        print(f"    > File {filepath} already exists, not overwriting...")

    # Just another day at work...
    loop_day += one_day
