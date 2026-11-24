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
import configparser
import os
import re
from zipfile import ZipFile

import cdsapi
from wrfinfra import generic

# Prepare default values

host = generic.identify_host_platform()
config = configparser.ConfigParser()
config.read(os.path.join(generic.path_of_repo(), "env", f"{host}.config"))

default_workdir = os.path.join(
    config["data"]["shared-input-dir"],
    "emissions",
    "anthro",
)

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
    default=default_workdir,
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

# Hard-coded parameters

zip_file = "cams.zip"
re_sector = "[A-Z]+"
re_version = "v[0-9]+\\.[0-9]+(|rev[0-9]+)"
re_species = "[a-z]+((-|_)[a-z]+)*"
re_year = "[0-9][0-9][0-9][0-9]"
re_nc_file = re.compile(
    f"^CAMS-GLOB-{re_sector}_{re_version}_{re_species}_{re_year}\\.nc$"
)

# Prepare the API connection and the data request

dataset = "cams-global-emission-inventories"
client = cdsapi.Client(url="https://ads.atmosphere.copernicus.eu/api")
request = {
    "year": years,
    "variable": species,
    "source": sectors,
    "version": versions,
}

# Remove target zip file, if any

try:
    os.remove(zip_file)
except FileNotFoundError:
    pass

# Download the data, unzip the file, and move files around

os.chdir(args.workdir)
workdir = os.getcwd()
client.retrieve(dataset, request).download("cams.zip")

with ZipFile(zip_file) as z:
    for obj in [obj for obj in z.infolist() if not obj.is_dir()]:
        # Quality controls on the file name
        if re_nc_file.fullmatch(obj.filename) is None:
            msg = f'Unexpected file in zip archive: "{obj.filename}".'
            raise ValueError(msg)

        split = obj.filename.split("_")
        _, _, sector = split[0].split("-")
        version = split[1]
        species = "_".join(split[2:-1])
        year = int(split[-1][:-3])

        # Create target directory
        os.chdir(workdir)
        for subdir in (f"cams-glob-{sector.lower()}", version, str(year)):
            if os.path.lexists(subdir):
                if not os.path.isdir(subdir):
                    msg = f'Target dir. "{subdir}" exists but is not a dir.'
                    raise RuntimeError(msg)
            else:
                os.mkdir(subdir)
            os.chmod(subdir, 0o775)
            os.chdir(subdir)

        # Remove redundant information from the file's name
        target_file = f"{species}.nc"

        # Extract and rename file
        print(f"Extracting {obj.filename} into {target_file}")
        for filename in [obj.filename, target_file]:
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass
        z.extract(obj, path=".")
        os.rename(obj.filename, target_file)
        os.chmod(target_file, 0o444)

# Remove the zip file
os.chdir(workdir)
os.remove(zip_file)
