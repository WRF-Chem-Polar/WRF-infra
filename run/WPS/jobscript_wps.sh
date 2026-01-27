#!/bin/bash
#
# Copyright (c) 2025 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# This script configures and runs WPS, the WRF pre-processor system.
#

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=01:00:00

[[ -f ../header.txt ]] && cat ../header.txt

#-------------#
# Preparation #
#-------------#

# We stop execution of the script as soon as a command fails
set -e

# Load simulation parameters and common resources
source ../simulation.conf
check_simulation_conf=yes
source ../commons.bash

submit_dir=$(pwd)

#-------------------------------#
# User-defined input parameters #
#-------------------------------#

# Note: these will be eventually moved to ../simulation.conf

# Select the input data.
# 0=ERA5 reanalysis, 1=ERA-INTERIM reanalysis 2=NCEP/FNL reanalysis
INPUT_DATA_SELECT=0

# Specifiy whether to write chl-a and DMS in met_em files
# set to true to call add_chloroa_wps.py and add_dmsocean_wps.py
# NB requires additional data to use
USE_CHLA_DMS_WPS=true

#-------------#
# Environment #
#-------------#

module purge
module load /proju/wrf-chem/software/libraries/gcc-v11.2.0/netcdf-fortran-v4.6.2_netcdf-c-v4.9.3_hdf5-v1.14.6_zlib-v1.3.1.module

#-------------------------#
# Sanity checks on inputs #
#-------------------------#

ms_start=$(date -d "${date_start}" +%M%S)
ms_end=$(date -d "${date_end}" +%M%S)
if [[ "${ms_start}" != "0000" || "${ms_end}" != "0000" ]]; then
    echo "This script assumes that start and end dates are o'clock hours." >&2
    exit 1
fi

# The INPUT_DATA_SELECT selector should be set to one of the expected values
if (( (INPUT_DATA_SELECT < 0) | (INPUT_DATA_SELECT > 2) )); then
  echo "Error, INPUT_DATA_SELECT = ${INPUT_DATA_SELECT}, should be between 0 and 2" >&2
  exit 1
fi

#-----------------------------------#
# Prepare WPS files and directories #
#-----------------------------------#

# Directory containing WPS output (i.e. met_em files)
OUTDIR="$dir_outputs/wps_${runid_wps}"
if [ -d "$OUTDIR" ]
then
  echo "Warning: directory $OUTDIR already exists, overwriting"
  rm -rf "${OUTDIR:?}/"*
else
  mkdir -pv "$OUTDIR"
fi

# Also create a temporary run directory
SCRATCH="$dir_work/wps_${runid_wps}.${SLURM_JOBID}"
rm -rf "$SCRATCH"
mkdir -pv "$SCRATCH"
cd "$SCRATCH" || exit

# Write the info on input/output directories to run log file
echo "Running WPS executables from $dir_wps"
echo "Running on scratchdir $SCRATCH"
echo "Writing output to $OUTDIR"
echo "Running from ${date_start} to ${date_end}"

cp $submit_dir/* "$SCRATCH/"

#  Prepare the WPS namelist
cp $namelist_wps namelist.wps
sed -i \
    -e "s/<start_date>/$(date -d ${date_start} +%Y-%m-%d_%H:%M:%S)/g" \
    -e "s/<end_date>/$(date -d ${date_end} +%Y-%m-%d_%H:%M:%S)/g" \
    namelist.wps

#-------------#
# Run geogrid #
#-------------#

mkdir -v geogrid
cp $dir_wps/geogrid/GEOGRID.TBL geogrid/GEOGRID.TBL
echo "-------- Running geogrid.exe --------"
cp $dir_wps/geogrid.exe .
mpirun ./geogrid.exe
# Clean up
rm -f geogrid.exe
rm -rf geogrid

#------------#
# Run ungrib #
#------------#

echo "-------- Running ungrib.exe --------"

# Create a directory containing links to the grib files of interest
mkdir -v grib_links

# Create links to the GRIB files in grib_links/
dir_grib=$dir_shared_data/met_boundary
date_ungrib=$(date +"%Y%m%d" -d "${date_start}")
while (( $(date -d "${date_ungrib}" "+%s") <= $(date -d "${date_end}" "+%s") )); do
  if (( INPUT_DATA_SELECT==0 )); then
    ln -sf "$dir_grib/era5/ERA5_grib1_invariant_fields/e5.oper.invariant."* grib_links/
    ln -sf "$dir_grib/era5/ERA5_grib1_$(date +"%Y" -d "$date_ungrib")/e5"*"pl"*"$(date +"%Y%m" -d "$date_ungrib")"* grib_links/
    ln -sf "$dir_grib/era5/ERA5_grib1_$(date +"%Y" -d "$date_ungrib")/e5"*"sfc"*"$(date +"%Y%m" -d "$date_ungrib")"* grib_links/
  # ERA-interim input
  elif (( INPUT_DATA_SELECT==1 )); then
    # NB we updated the $GRIB_DIR file path but the new path doesn't contain ERA-I
    # so these lines will fail
    ln -sf "$dir_grib/ERAI/ERA-Int_grib1_$(date +"%Y" -d "$date_ungrib")/ei.oper."*"pl"*"$(date +"%Y%m%d" -d "$date_ungrib")"* grib_links/
    ln -sf "$dir_grib/ERAI/ERA-Int_grib1_$(date +"%Y" -d "$date_ungrib")/ei.oper."*"sfc"*"$(date +"%Y%m%d" -d "$date_ungrib")"* grib_links/
  # FNL input
  elif (( INPUT_DATA_SELECT==2 )); then
    ln -sf "$dir_grib/fnl/ds083.2/FNL$(date +"%Y" -d "$date_ungrib")/fnl_$(date +"%Y%m%d" -d "$date_ungrib")"* grib_links/
  fi
  # Go to the next date to ungrib
  date_ungrib=$(date +"%Y%m%d" -d "$date_ungrib + 1 day");
done

# Create links with link_grib.csh, ungrib with ungrib.exe
ls -ltrh grib_links
cp $dir_wps/link_grib.csh .
cp $dir_wps/ungrib.exe .

# ERA-interim input
if (( INPUT_DATA_SELECT==0 )); then
  cp $dir_wps/ungrib/Variable_Tables/Vtable.ERA-interim.pl Vtable
  sed -i 's/_FILE_ungrib_/FILE/g' namelist.wps
  ./link_grib.csh grib_links/e5
elif (( INPUT_DATA_SELECT==1 )); then
  cp $dir_wps/ungrib/Variable_Tables/Vtable.ERA-interim.pl Vtable
  sed -i 's/_FILE_ungrib_/FILE/g' namelist.wps
  ./link_grib.csh grib_links/ei
elif (( INPUT_DATA_SELECT==2 )); then
  cp $dir_wps/ungrib/Variable_Tables/Vtable.GFS Vtable
  sed -i 's/_FILE_ungrib_/FILE/g' namelist.wps
  ./link_grib.csh grib_links/fnl
else
    echo "Error: Unsupported value of INPUT_DATA_SELECT: $INPUT_DATA_SELECT"
    exit 1
fi
./ungrib.exe
ls -ltrh

# Clean up
rm -f link_grib.csh ungrib.exe GRIBFILE* Vtable
rm -rf grib_links

#-------------#
# Run metgrid #
#-------------#

echo "-------- Running metgrid.exe --------"
cp $dir_wps/util/avg_tsfc.exe .
cp $dir_wps/metgrid.exe .

mkdir -v metgrid
ln -sf $dir_wps/metgrid/METGRID.TBL metgrid/METGRID.TBL

# In order to use the daily averaged skin temperature for lakes, tavgsfc (thus also metgrid)
# should be run once per day
date_s_met=$(date +"%Y%m%d" -d "${date_start}")
# Loop on run days
while (( $(date -d "${date_s_met} +1 day" "+%s") <= $(date -d "${date_end}" "+%s") )); do
  date_e_met=$(date +"%Y%m%d" -d "$date_s_met + 1 day");
  echo "$date_s_met"
  #  Prepare the WPS namelist
  cp $namelist_wps namelist.wps
  sed -i \
      -e "s/<start_date>/$(date -d ${date_s_met} +%Y-%m-%d_00:00:00)/g" \
      -e "s/<end_date>/$(date -d ${date_e_met} +%Y-%m-%d_00:00:00)/g" \
      -e "s/<FILE_metgrid>/FILE/" \
      namelist.wps
  # Run avg_tsfc and metgrid
  ./avg_tsfc.exe
  mpirun ./metgrid.exe
  date_s_met=$date_e_met
done # While date < end date
# Clean up
rm -f avg_tsfc.exe metgrid.exe FILE* PFILE* TAVGSFC
rm -rf metgrid

#-----------------------------------#
# Post process outputs from metgrid #
#-----------------------------------#

cmd_python="python"
if [[ -v $conda_run ]]; then
    cmd_python=$conda_run python
fi

if $USE_CHLA_DMS_WPS; then

    date_s=$(date -d "${date_start}" +%Y-%m-%d)
    date_e=$(date -d "${date_end}" +%Y-%m-%d)

    #---- Add chlorophyll-a oceanic concentrations to met_em*
    echo "python -u add_chloroa_wps.py $SCRATCH/ ${date_s} ${date_e}"
    "${cmd_python}" -u add_chloroa_wps.py "$SCRATCH/" "${date_s}" "${date_e}"

    #---- Add DMS oceanic concentrations to met_em*
    echo "python -u add_dmsocean_wps.py $SCRATCH/ ${date_s} ${date_e}"
    "${cmd_python}" -u add_dmsocean_wps.py "$SCRATCH/" "${date_s}" "${date_e}"

fi

#----------#
# Clean up #
#----------#

mv ./geo_em*nc ./met_em* "$OUTDIR/"
mv ./*.log "$OUTDIR/"
mv namelist.wps "$OUTDIR/"
rm -rf "$SCRATCH"
echo "Successful execution of script $0"
