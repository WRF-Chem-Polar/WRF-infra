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

#-------------------------------#
# User-defined input parameters #
#-------------------------------#

# Note: these will be eventually moved to ../simulation.conf

# Simulation start year and month
yys=2012
mms=03
dds=01
hhs=00
# Simulation end year, month, day, hour
yye=2012
mme=03
dde=08
hhe=00

#-------------#
# Environment #
#-------------#

module purge
module load /proju/wrf-chem/software/libraries/gcc-v11.2.0/netcdf-fortran-v4.6.2_netcdf-c-v4.9.3_hdf5-v1.14.6_zlib-v1.3.1.module

#---------#
# Prepare #
#---------#

date_s="$yys-$mms-$dds"
date_e="$yye-$mme-$dde"

ID="$(date +"%Y%m%d").$SLURM_JOBID"

# Directory containing real output (e.g. wrfinput_d01, wrfbdy_d01 files)
REALDIR="${dir_outputs}/real_${runid_real}_$(date -d "$date_s" "+%Y")"
# Directory containing WRF-Chem output
OUTDIR="${dir_outputs}/DONE.${runid_wrf}.$ID"
mkdir -pv "$OUTDIR"

# Also create a temporary run directory
SCRATCH="$dir_work/DONE.${runid_wrf}.$ID.scratch"
rm -rf "$SCRATCH"
mkdir -pv "$SCRATCH"
cd "$SCRATCH" || exit

# Write the info on input/output directories to run log file
echo " "
echo "-------- $SLURM_JOB_NAME --------"
echo "Running from $date_s to $date_e"
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
wrf_dx=$(grep  "dx *=" $submit_dir/$namelist_real | tr -d [:blank:] | cut -d "=" -f 2- | cut -d "," -f 1)
wrf_dy=$(grep  "dy *=" $submit_dir/$namelist_real | tr -d [:blank:] | cut -d "=" -f 2- | cut -d "," -f 1)
wrf_e_we=$(grep  "e_we *=" $submit_dir/$namelist_real | tr -d [:blank:] | cut -d "=" -f 2- | cut -d "," -f 1)
wrf_e_sn=$(grep  "e_sn *=" $submit_dir/$namelist_real | tr -d [:blank:] | cut -d "=" -f 2- | cut -d "," -f 1)
xwavenum=$(( (wrf_dx * wrf_e_we) / nudging_scale))
ywavenum=$(( (wrf_dy * wrf_e_sn) / nudging_scale))
# Edit the namelist
sed -i "s/__STARTYEAR__/${yys}/g" namelist.input
sed -i "s/__STARTMONTH__/${mms}/g" namelist.input
sed -i "s/__STARTDAY__/${dds}/g" namelist.input
sed -i "s/__STARTHOUR__/${hhs}/g" namelist.input
sed -i "s/__ENDYEAR__/${yye}/g" namelist.input
sed -i "s/__ENDMONTH__/${mme}/g" namelist.input
sed -i "s/__ENDDAY__/${dde}/g" namelist.input
sed -i "s/__ENDHOUR__/${hhe}/g" namelist.input
sed -i "s/__BIO_EMISS_OPT__/3/g" namelist.input
sed -i "s/__XWAVENUM__/$xwavenum/g" namelist.input
sed -i "s/__YWAVENUM__/$ywavenum/g" namelist.input

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
date_s_chem=$(date +"%Y%m%d" -d "$date_s")
while (( $(date -d "$date_s_chem" "+%s") <= $(date -d "$date_e" "+%s") )); do
  date_e_chem=$(date +"%Y%m%d" -d "$date_s_chem + 1 day");
  yys_chem=${date_s_chem:0:4}
  mms_chem=${date_s_chem:4:2}
  dds_chem=${date_s_chem:6:2}
  cp "${REALDIR}/wrfchemi_d01_$yys_chem-$mms_chem-$dds_chem"* "$SCRATCH/"
  cp "${REALDIR}/wrffirechemi_d01_$yys_chem-$mms_chem-$dds_chem"* "$SCRATCH/"
  date_s_chem=$date_e_chem
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
