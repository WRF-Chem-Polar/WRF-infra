# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Get WRF/WRF-Chem-relevant CAMS emissions from Copernius atmos. data store.

The DOI of the data being downloaded is 10.24381/1d158bec.

The corresponding citation is: Granier, C., S. Darras, H. Denier van der Gon,
J. Doubalova, N. Elguindi, B. Galle, M. Gauss, M. Guevara, J.-P. Jalkanen,
J. Kuenen, C. Liousse, B. Quack, D. Simpson, K. Sindelarova, The Copernicus
Atmosphere Monitoring Service global and regional emissions (April 2019
version), Copernicus Atmosphere Monitoring Service (CAMS) report, 2019,
doi:10.24380/d0bn-kx16.

To use this script, you must:

 - have an account at https://ads.atmosphere.copernicus.eu/
 - have properly created the file ~/.cdsapirc with your credentials.
 - log in to your account and accept the terms of service
   for the CAMS global emission inventories dataset

The cdsapi package can be installed via pip or conda-forge.

"""

import argparse
import os

import cdsapi

# Command-line arguments

parser = argparse.ArgumentParser(
    description=(
        "Download CAMS global emission inventory data "
        "from the Copernicus atmospheric data store"
    ),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--years",
    help="Comma-separated list of years.",
    required=True,
)
parser.add_argument(
    "--species",
    help="Comma-separated list of species",
    required=True,
)
parser.add_argument(
    "--sectors",
    help="Comma-separated list of emission sectors",
    default="anthropogenic",
)
parser.add_argument(
    "--versions",
    help="Comma-separated list of CAMS versions.",
    default="v6.2",
)
parser.add_argument(
    "--workdir",
    help="Directory where to download the data. It must already exist.",
    default=".",
)
parser.add_argument(
    "--overwrite",
    help="Whether to allow overwriting existing files.",
    choices=["true", "false"],
    default="false",
)
args = parser.parse_args()

# Pre-process command-line arguments

years = [int(year) for year in args.years.split(",")]
species = [species.strip() for species in args.species.split(",")]
sectors = [sector.strip() for sector in args.sectors.split(",")]
versions = [version.strip() for version in args.versions.split(",")]
dir_work = os.path.abspath(os.path.expanduser(args.workdir))
overwrite = args.overwrite == "true"

# Prepare the API connection and the data request

dataset = "cams-global-emission-inventories"
client = cdsapi.Client(url="https://ads.atmosphere.copernicus.eu/api")
request = {
    "year": years,
    "variable": species,
    "source": sectors,
    "version": versions,
}

# Download the data

client.retrieve(dataset, request).download("cams.zip")
