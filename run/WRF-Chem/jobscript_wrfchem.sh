#!/bin/bash
#
# Copyright (c) 2025-now LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# This script configures and runs WRF+WRF-Chem.
#

# Resources used
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=32
#SBATCH --mem=60G
#SBATCH --time=24:00:00

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

#-------------#
# Environment #
#-------------#

module purge
module load /proju/wrf-chem/software/libraries/gcc-v11.2.0/netcdf-fortran-v4.6.2_netcdf-c-v4.9.3_hdf5-v1.14.6_zlib-v1.3.1.module

#---------#
# Prepare #
#---------#

# Directory containing real output (e.g. wrfinput_d01, wrfbdy_d01 files)
REALDIR="${dir_outputs}/real_${runid_wps}_${runid_real}"
# Directory containing WRF-Chem output
OUTDIR="${dir_outputs}/wrf_${runid_wps}_${runid_real}_${runid_wrf}"
mkdir -pv "$OUTDIR"

# Also create a temporary run directory
SCRATCH="$dir_work/wrf_${runid_wps}_${runid_real}_${runid_wrf}.${SLURM_JOBID}"
rm -rf "$SCRATCH"
mkdir -pv "$SCRATCH"
cd "$SCRATCH" || exit

# Write the info on input/output directories to run log file
echo " "
echo "-------- $SLURM_JOB_NAME --------"
echo "Running from ${date_start} to ${date_end}"
echo "Running version wrf.exe from $dir_wrf"
echo "Running on scratchdir $SCRATCH"
echo "Writing output to $OUTDIR"
echo "Input files from real.exe taken from $REALDIR"

# Save this slurm script to the output directory
cp "$0" "$OUTDIR/jobscript_wrf.sh"

#---------#
# Run WRF #
#---------#

cd "$SCRATCH" || exit

#---- Copy all needed files to scrach space
# Input files from run setup directory
cp "$submit_dir/"* "$SCRATCH/"
# Executables and WRF aux files from dir_wrf
cp "$dir_wrf/run/"* "$SCRATCH/"

#  Copy and prepare the WRF namelist, set up run start and end dates
cp -vf $submit_dir/$namelist_wrf namelist.input
# Init spectral nudging parameters
# We only nudge over the scale $nudging_scale in meters
nudging_scale=1000000
wrf_dx=$(sed -n -e 's/^[ ]*dx[ ]*=[ ]*//p' namelist.input | sed -n -e 's/,.*//p')
wrf_dy=$(sed -n -e 's/^[ ]*dy[ ]*=[ ]*//p' namelist.input | sed -n -e 's/,.*//p')
wrf_e_we=$(sed -n -e 's/^[ ]*e_we[ ]*=[ ]*//p' namelist.input | sed -n -e 's/,.*//p')
wrf_e_sn=$(sed -n -e 's/^[ ]*e_sn[ ]*=[ ]*//p' namelist.input | sed -n -e 's/,.*//p')
xwavenum=$(( (wrf_dx * wrf_e_we) / nudging_scale))
ywavenum=$(( (wrf_dy * wrf_e_sn) / nudging_scale))
# Edit the namelist
sed -i \
    -e "s/<start_year>/$(utc -d ${date_start} +%Y)/g" \
    -e "s/<start_month>/$(utc -d ${date_start} +%m)/g" \
    -e "s/<start_day>/$(utc -d ${date_start} +%d)/g" \
    -e "s/<start_hour>/$(utc -d ${date_start} +%H)/g" \
    -e "s/<end_year>/$(utc -d ${date_end} +%Y)/g" \
    -e "s/<end_month>/$(utc -d ${date_end} +%m)/g" \
    -e "s/<end_day>/$(utc -d ${date_end} +%d)/g" \
    -e "s/<end_hour>/$(utc -d ${date_end} +%H)/g" \
    -e "s/<bio_emiss_opt>/3/g" \
    -e "s/<xwavenum>/${xwavenum}/g" \
    -e "s/<ywavenum>/${ywavenum}/g"\
    namelist.input

# Copy the input files from real.exe
cp "${REALDIR}/wrfinput_d01" "$SCRATCH/"
cp "${REALDIR}/wrfbdy_d01" "$SCRATCH/"
# wrffdda is only needed if fdda (nudging) is active
cp "${REALDIR}/wrffdda_d01" "$SCRATCH/"
# wrflowinp is only needed if sst_update is active (lower boundary condition for SST and sea
# ice cover
cp "${REALDIR}/wrflowinp_d01" "$SCRATCH/"
# wrfchemi and wrffirechemi files are only needed for WRF-Chem if anthropogenic
# and fire emissions are active
date_chem=$(utc +"%Y%m%dZ" -d "${date_start}")
while (( $(utc -d "${date_chem}" "+%s") <= $(utc -d "${date_end}" "+%s") )); do
  suffix=$(utc -d ${date_chem} +%Y-%m-%d)
  cp "${REALDIR}/wrfchemi_d01_${suffix}"* "$SCRATCH/"
  cp "${REALDIR}/wrffirechemi_d01_${suffix}"* "$SCRATCH/"
  date_chem=$(utc +"%Y%m%dZ" -d "${date_chem} + 1 day")
done
# exo_coldens and wrf_season_wes_usgs only  needed for MOZART gas phase chemistry
cp "${REALDIR}/exo_coldens_d01" "$SCRATCH/"
cp "${REALDIR}/wrf_season_wes_usgs_d01.nc" "$SCRATCH/"
# Only needed for TUV photolysis
cp "$dir_shared_data/photolysis/wrf_tuv_xsqy.nc" "$SCRATCH/"
cp -r "$dir_shared_data/photolysis/DATA"?? "$SCRATCH/"

# Transfer other input data
cp "$dir_shared_data/upper_boundary_chem/clim_p_trop.nc" "$SCRATCH/"
cp "$dir_shared_data/upper_boundary_chem/ubvals_b40.20th.track1_1996-2005.nc" "$SCRATCH/"

echo " "
echo "-------- $SLURM_JOB_NAME: run wrf.exe ---------"
echo " "
mpirun ./wrf.exe

#----------#
# Finalize #
#----------#

echo " "
echo "-------- $SLURM_JOB_NAME: transfer WRF results --------"
echo " "

mv ./wrfout_* "$OUTDIR/"
mv ./wrfrst_* "$OUTDIR/"
cp ./rsl.* ./namelist.* "$OUTDIR/"
rm -rf "$SCRATCH"
