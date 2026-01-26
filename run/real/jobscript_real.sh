#!/bin/bash
#
# Copyright (c) 2025-now LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# This script configures and runs real.exe and the associated pre-processors.
#

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=06:00:00
#SBATCH --partition=zen16
#SBATCH --mem=6G

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

# Add WRF-Chem preprocessors to PATH
PATH=/proju/wrf-chem/software/wrf-installs/WRF-Chem-Preprocessing-Tools/bin:$PATH

#------------------------------------#
# Prepare REAL files and directories #
#------------------------------------#

date_s="$yys-$mms-$dds"
date_e="$yye-$mme-$dde"

ID="$(date +"%Y%m%d").$SLURM_JOBID"

WPSDIR="$dir_outputs/wps_${runid_wps}"

# Directory containing real.exe output (e.g. wrfinput_d01, wrfbdy_d01 files)
REALDIR="$dir_outputs/real_${runid_wps}_${runid_real}"
if [ -d "$REALDIR" ]; then
  rm -f "$REALDIR/"*
else
  mkdir -pv "$REALDIR"
fi

# Also create a temporary work directory
SCRATCH="$dir_work/real_${runid_real}_$(date -d "$date_s" "+%Y").${ID}.scratch"
rm -rf "$SCRATCH"
mkdir -pv "$SCRATCH"
cd "$SCRATCH" || exit

# Write the info on input/output directories to run log file
echo " "
echo "-------- $SLURM_JOB_NAME: Launch real.exe and preprocessors --------"
echo "Running from $date_s to $date_e"
echo "Running version real.exe from $dir_wrf"
echo "Running on scratchdir $SCRATCH"
echo "Writing output to $REALDIR"
echo "Input files from WPS taken from $WPSDIR"

# Save this slurm script to the output directory
cp $0 $REALDIR/jobscript_real.sh

cd $SCRATCH

#---- Copy all needed files to scrach space
# Input files from run setup directory
cp $submit_dir/* $SCRATCH/
# Copy executables and WRF auxiliary files to work directory
cp $dir_wrf/run/* $SCRATCH/
# met_em WPS files from WPSDIR
cp ${WPSDIR}/met_em.d* $SCRATCH/

#---- Init spectral nudging parameters
# We only nudge over the scale $nudging_scale in meters
nudging_scale=1000000
wrf_dx=$(sed -n -e 's/^[ ]*dx[ ]*=[ ]*//p' "$submit_dir/$namelist_real" | sed -n -e 's/,.*//p')
wrf_dy=$(sed -n -e 's/^[ ]*dy[ ]*=[ ]*//p' "$submit_dir/$namelist_real" | sed -n -e 's/,.*//p')
wrf_e_we=$(sed -n -e 's/^[ ]*e_we[ ]*=[ ]*//p' "$submit_dir/$namelist_real" | sed -n -e 's/,.*//p')
wrf_e_sn=$(sed -n -e 's/^[ ]*e_sn[ ]*=[ ]*//p' "$submit_dir/$namelist_real" | sed -n -e 's/,.*//p')
xwavenum=$(( (wrf_dx * wrf_e_we) / nudging_scale))
ywavenum=$(( (wrf_dy * wrf_e_sn) / nudging_scale))

#-----------------------------------------#
# Run real.exe without biogenic emissions #
#-----------------------------------------#

echo " "
echo "-------- $SLURM_JOB_NAME: run real.exe without bio emissions--------"
echo " "
# Prepare the real.exe namelist, set up run start and end dates
cp -vf $submit_dir/$namelist_real namelist.input
sed -i "s/__STARTYEAR__/${yys}/g" namelist.input
sed -i "s/__STARTMONTH__/${mms}/g" namelist.input
sed -i "s/__STARTDAY__/${dds}/g" namelist.input
sed -i "s/__STARTHOUR__/${hhs}/g" namelist.input
sed -i "s/__ENDYEAR__/${yye}/g" namelist.input
sed -i "s/__ENDMONTH__/${mme}/g" namelist.input
sed -i "s/__ENDDAY__/${dde}/g" namelist.input
sed -i "s/__ENDHOUR__/${hhe}/g" namelist.input
sed -i "s/__BIO_EMISS_OPT__/0/g" namelist.input
sed -i "s/__XWAVENUM__/$xwavenum/g" namelist.input
sed -i "s/__YWAVENUM__/$ywavenum/g" namelist.input
mpirun ./real.exe
# Check the end of the log file in case real crashes
tail -n20 rsl.error.0000

#---------------------#
# Run megan_bio_emiss #
#---------------------#

# This step creates a wrfbiochemi_* file

echo " "
echo "-------- $SLURM_JOB_NAME: run megan_bio_emiss --------"
echo " "
# megan_bio_emiss often SIGSEGVs at the end but this is not an issue
MEGANEMIS_DIR="$dir_shared_data/natural_emissions/terrestrial/megan"
ln -s "${MEGANEMIS_DIR}/"*".nc" .
sed -i "s:MEGANEMIS_DIR:${MEGANEMIS_DIR}:g" megan_bioemiss.inp
sed -i "s:WRFRUNDIR:$PWD/:g" megan_bioemiss.inp
if [ $mms -eq 1 ]; then
  sed -i "s:SMONTH:1:g" megan_bioemiss.inp
  sed -i "s:EMONTH:12:g" megan_bioemiss.inp
else
  sed -i "s:SMONTH:$((10#$mms - 1)):g" megan_bioemiss.inp
  sed -i "s:EMONTH:$mme:g" megan_bioemiss.inp
fi
set +e # Temporary until we fix the seg fault in megan_bio_emiss
megan_bio_emiss < megan_bioemiss.inp > megan_bioemiss.out
set -e # Temporary until we fix the seg fault in megan_bio_emiss
tail megan_bioemiss.out

#-----------------------------------------#
# Re-run real.exe with biogenic emissions #
#-----------------------------------------#

echo " "
echo "-------- $SLURM_JOB_NAME: run real.exe with bio emissions --------"
echo " "
# Prepare the real.exe namelist, set up run start and end dates
cp $submit_dir/$namelist_real namelist.input
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
mpirun ./real.exe
# Check the end of the log file in case real crashes
tail -n20 rsl.error.0000

#-----------#
# Run mozbc #
#-----------#

# (use initial and boundary conditions for chemistry +
# aerosols from a MOZART global run, updates the chemistry and aerosol fields
# in wrfinput* and wrfbdy* files)
echo " "
echo "-------- $SLURM_JOB_NAME: run mozbc --------"
echo " "
# Find the boundary condition file autmatically in MOZBC_DIR, assuming it is called e.g. cesm-201202.nc
MOZBC_DIR="$dir_shared_data/chem_boundary/cesm/"
MOZBC_FILE="$(ls -1 --color=never "$MOZBC_DIR/cesm-$yys$mms"*".nc" | xargs -n 1 basename | tail -n1)"
echo "Run MOZBC for $MOZBC_DIR/$MOZBC_FILE"
if [ -f "$MOZBC_DIR/$MOZBC_FILE" ]; then
  sed -i "s:dir_moz =.*:dir_moz = \'$MOZBC_DIR\':g" cesmbc_mozartmosaic4bin.inp
  sed -i "s/fn_moz  =.*/fn_moz  = \'$MOZBC_FILE\'/g" cesmbc_mozartmosaic4bin.inp
  sed -i "s:WRFRUNDIR:$PWD/:g" cesmbc_mozartmosaic4bin.inp
  mozbc < cesmbc_mozartmosaic4bin.inp > mozbc.out
else
  echo "Error: could not find mozbc file"
  exit 1
fi
tail mozbc.out

#----------------------------#
# Run wesely and exo_coldens #
#----------------------------#

# (needed only for the MOZART gas phase mechanism, creates a
# wrf_season* and exo_coldens* file, containing seasonal dry deposition
# coefficients and trace gases above the domain top, respectively)
echo " "
echo "-------- $SLURM_JOB_NAME: run wesely and exo_coldens --------"
echo " "
sed -i "s:WRFRUNDIR:$PWD/:g" wesely.inp
sed -i "s:WRFRUNDIR:$PWD/:g" exo_coldens.inp
cp $dir_shared_data/dry_deposition/*.nc $SCRATCH
wesely < wesely.inp >  wesely.out
tail wesely.out
cp $dir_shared_data/photolysis/*.nc $SCRATCH
exo_coldens < exo_coldens.inp > exo_coldens.out
tail exo_coldens.out
# Bug fix, XLONG can sometimes be empty in exo_coldens_dXX
ncks -x -v XLONG,XLAT exo_coldens_d01 -O exo_coldens_d01
ncks -A -v XLONG,XLAT wrfinput_d01 exo_coldens_d01

#---------------#
# Run fire_emis #
#---------------#

# This steps creates fire emission files (wrffirechemi*)

echo " "
echo "-------- $SLURM_JOB_NAME: run fire_emis --------"
echo " "
# Find the fire emission file autmatically in FIREEMIS_DIR, assuming it is called e.g. GLOBAL_FINNv1.5_2012.MOZ.txt
#TODO update to latest version
FIREEMIS_DIR="$dir_shared_data/fire_emissions/finn/version1/"
FIREEMIS_FILE="$(ls -1 --color=never "$FIREEMIS_DIR/"*"v1.5"*"_${yys}"*"MOZ"*".txt" | xargs -n 1 basename | tail -n1)"
echo "Run FIREEMIS for $FIREEMIS_DIR/$FIREEMIS_FILE"
if [ -f "$FIREEMIS_DIR/$FIREEMIS_FILE" ]; then
  sed -i "s:fire_directory    = .*:fire_directory    = \'$FIREEMIS_DIR\',:g" fire_emis_mozartmosaic.inp
  sed -i "s:fire_filename(1)  = .*:fire_filename(1)  = \'$FIREEMIS_FILE\',:g" fire_emis_mozartmosaic.inp
  sed -i "s:wrf_directory     = .*:wrf_directory     = \'$PWD/\',:g" fire_emis_mozartmosaic.inp
  sed -i "s:start_date        = .*:start_date        = \'$yys-$mms-$dds\',:g" fire_emis_mozartmosaic.inp
  sed -i "s:end_date          = .*:end_date          = \'$yye-$mme-$dde\',:g" fire_emis_mozartmosaic.inp
  fire_emis < fire_emis_mozartmosaic.inp > fire_emis.out
else
  echo "Error: could not find fire emis file"
  exit 1
fi
tail fire_emis.out

#---------------------#
# Run cams2wrfchem.py #
#---------------------#

# This step creates wrfchemi* files

echo " "
echo "-------- $SLURM_JOB_NAME: run emission script --------"
echo " "
ANTHRO_EMS_DIR="$dir_shared_data/anthro_emissions/cams/"
cp $submit_dir/cams2wrfchem.py $SCRATCH/
$conda_run python -u cams2wrfchem.py --start ${date_s} --end ${date_e} --domain 1 --dir-em-in ${ANTHRO_EMS_DIR}

#----------------------------#
# Initialize snow on sea ice #
#----------------------------#

echo " "
echo "-------- $SLURM_JOB_NAME: Initialize snow on sea ice --------"
echo " "
mms_zero=$(echo "$mms" | sed 's/^0*//')
# Only in winter and early spring (December-April)
if ((mms_zero < 5 || mms_zero > 11)); then
# Initialize snow depth on sea ice to 30 cm
  ncap2 -s 'where(SEAICE>0. && XLAT>65.) SNOWH=0.3;' wrfinput_d01 -O wrfinput_d01
# Initialize snow water equivalent to 60 kg/m2 (assuming a snow density of 200 kg/m3)
  ncap2 -s 'where(SEAICE>0. && XLAT>65.) SNOW=0.3*200.;' wrfinput_d01 -O wrfinput_d01
# Initialize snow cover to 1
  ncap2 -s 'where(SEAICE>0. && XLAT>65.) SNOWC=1.;' wrfinput_d01 -O wrfinput_d01
fi

#----------#
# Finalize #
#----------#

echo " "
echo "-------- $SLURM_JOB_NAME: transfer real.exe output --------"
echo " "

rm -f ./met_em*
cp ./*.inp ./*.out ./rsl* "$REALDIR/"
cp ./*d0* "$REALDIR/"
cp ./namelist.input "$REALDIR/namelist.input.real"
cp ./namelist.output "$REALDIR/"
rm -rf "$SCRATCH"
echo "Successful execution of script $0"
