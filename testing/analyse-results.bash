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

     - outputs_1/wrf_...
     - outputs_2/wrf_...

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

if [[ ! -d ${dir_work} ]]; then
   log "error: work dir (${dir_work}) does not exists."
   exit 1
fi

#-----------------------#
# Hard-coded parameters #
#-----------------------#

# Regular expression(s) for files and directories
d="[0-9]"
re_dir_outputs="outputs_[0-9]+"
re_dir_wrfout="wrf_.+_.+_.+_$d$d$d$d-$d$d-$d$d\\.$d+"

# Variables that should be kept when concatenating wrfout files
essential_variables=(
    XLONG
    XLAT
    XLONG_U
    XLAT_U
    XLONG_V
    XLAT_V
)
used_in_derived_variables=(
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

# Process hard-coded parameters
essential_variables=$(IFS=, ; echo "${essential_variables[*]}")
used_in_derived_variables=$(IFS=, ; echo "${used_in_derived_variables[*]}")
keep_variables="${essential_variables},${used_in_derived_variables}"

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
