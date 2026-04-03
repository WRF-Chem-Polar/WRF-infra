#!/bin/bash
#
# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Jobscript to analyze the results of one or more WRF runs.
#
# For documentation, run:
#
# ./analyse-results.job --help
#
# (or look at the variable ${docstring} below).

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=00:30:00

set -e

docstring=$(cat <<'EOF'
This script runs our default analysis on one or more WRF-Chem simulations.

This script is intended to be used on the directory produced by the
script plot-vertical-profiles.py.

Options:

--help
    Prints this docstring and exits without error.

--work-dir (default=current directory)
    The directory where the outputs of the simulations are. This directory must
    contain sub-directories such as:

     - outputs_1/wrf.blablabla
     - outputs_2/wrf.blablabla

EOF
)

#-------------#
# Function(s) #
#-------------#

function log {
    # Echoes given arguments as logged message.
    echo -e "analyse-results.bash: ${@%$'\n'}"
}

#------------------------#
# Command-line arguments #
#------------------------#

dir_work="$(pwd)"
for ((i = 1; i <= $#; i++)); do
    arg="${!i}"
    if [[ "${arg}" == "--help" ]]; then
        echo -e "\n${docstring}\n"
        exit 0
    elif [[ "${arg}" == "--work-dir" && $i < $# ]]; then
        i=$((i+1))
        dir_work="${!i}"
    else
        log "error: could not parse command-line arguments."
        exit 1
    fi
done

if [[ ! -d "${dir_work}" ]]; then
   log "error: work dir (${dir_work}) does not exists."
   exit 1
fi
cd "${dir_work}"

#-----------------------#
# Hard-coded parameters #
#-----------------------#

# Regular expression(s) for files and directories
d="[0-9]"
re_dir_outputs="outputs_[0-9]+"
re_dir_wrfout="wrf\\..+\\..+\\..+\\.$d$d$d$d-$d$d-$d${d}Z\\.$d+"

# Variables that should be kept when concatenating wrfout files
essential_vars=(
    XLONG
    XLAT
    XLONG_U
    XLAT_U
    XLONG_V
    XLAT_V
)
used_in_derived_vars=(
    HGT
    MAPFAC_M
    P
    PB
    PH
    PHB
    QCLOUD
    QVAPOR
    RAINC
    RAINNC
    T
)
plotted_vars=(
    o3
    PM2_5_DRY
    PM10
    QCLOUD
)


# Process hard-coded parameters
essential_vars=$(IFS=, ; echo "${essential_vars[*]}")
used_in_derived_vars=$(IFS=, ; echo "${used_in_derived_vars[*]}")
plotted_vars=$(IFS=, ; echo "${plotted_vars[*]}")
keep_variables="${essential_vars},${used_in_derived_vars},${plotted_vars}"

#--------------------------#
# Concatenate wrfout files #
#--------------------------#

# Note: the outputs_$i directories must be processed in the correct order, and
# outputs_11 must be processed after outputs_2 (alphabetical order will not do)

# Get the list of "outputs_$i" directories and the highest such i value
dirs_outputs=($(find . -maxdepth 1 -regex "^./${re_dir_outputs}\$"))
imax=-1
for dir_outputs in ${dirs_outputs[*]}; do
    i=$(echo "${dir_outputs}" | cut -d_ -f2)
    [[ i -gt ${imax} ]] && imax=$i
done

# For each of these directories, concatenate the wrfout files
wrfout_files=()
for ((i = 0; i <= imax; i++)); do

    dir_outputs="./outputs_${i}"
    [[ ! " ${dirs_outputs[@]} " =~ " ${dir_outputs} " ]] && continue
    log "processing directory ${dir_outputs}"

    # Find the name of the directory that contains the wrfout files
    cd "${dir_outputs}"
    dir_wrf=$(find . -maxdepth 1 -regex "^./${re_dir_wrfout}\$")
    if [[ -z "${dir_wrf}" || $(echo "${dir_wrf}" | grep -c "") != 1 ]]; then
        log "error: could not find wrf output directory in ${dir_outputs}."
        exit 1
    fi

    # Concatenate wrfout files into a single file
    cd "${dir_wrf}"
    ncrcat -O \
           -v "${keep_variables}" \
           wrfout_d01_????-??-??_??\:??\:?? \
           wrfout_d01.nc

    wrfout_files+=("$(pwd)/wrfout_d01.nc")
    cd "${dir_work}"

done

#--------------------------#
# Run the plotting scripts #
#--------------------------#

# Prepare the environment
dir_infra="${dir_work}/WRF-infra_1"
check_simulation_conf=no
source "${dir_infra}/run/commons.bash"
source "${dir_infra}/env/$(get_host_name).sh"

# Plot a first series of vertical profiles for non-cloud variables,
# using a one-cell window
variables=(
    "air_temperature:1"
    "relative_humidity:1"
    "o3:1"
    "PM2_5_DRY:1"
    "PM10:1"
)
locations=(
    "NorthPole:0:90"
)
${conda_run} python \
             "${dir_infra}/testing/plot-vertical-profiles.py" \
             --wrfouts=$(IFS=, ; echo "${wrfout_files[*]}")\
             --variables=$(IFS=, ; echo "${variables[*]}") \
             --locations=$(IFS=, ; echo "${locations[*]}") \
             --output="${dir_work}/vertical-profiles_non-clouds.pdf"

# Plot a second series of vertical profiles for cloud variables,
# using a larger window
variables=(
    "QCLOUD:9"
)
locations=(
    "SeaIce:170:84"
    "OpenOcean:-29:55"
    "Siberia:108:60"
)
${conda_run} python \
             "${dir_infra}/testing/plot-vertical-profiles.py" \
             --wrfouts=$(IFS=, ; echo "${wrfout_files[*]}")\
             --variables=$(IFS=, ; echo "${variables[*]}") \
             --locations=$(IFS=, ; echo "${locations[*]}") \
             --output="${dir_work}/vertical-profiles_clouds.pdf"
