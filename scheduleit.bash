#!/bin/bash
#
# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Run a script through the local scheduler.
#

# Get information about the environment
dir_infra="$(dirname "$(readlink -f $0)")"
source "${dir_infra}/run/commons.bash"
host=$(cd "${dir_infra}"; get_host_name)

# Define default values
declare -A scheduler_opts
scheduler_opts[time]="01:00:00"
scheduler_opts[nodes]="1"
scheduler_opts[ntasks-per-node]="1"

# Parse command line arguments
declare -A scheduler_opts_cdm
while [[ $# -gt 0 && $1 == --* ]]; do
    scheduler_opts_cdm["${1#--}"]="$2"
    shift 2
done
script="$1"
shift
script_args=("$@")

# Parse the scheduler options written in the file
while read -r _ key value; do
    scheduler_opts["${key}"]="${value}"
done < <(grep -E '^#(SCHEDULER|SBATCH)' "${script}")

# Combine the scheduler options from the two sources
# (command-line arguments have precedence)
for key in "${!scheduler_opts_cdm[@]}"; do
    value="${scheduler_opts_cdm[${key}]}"
    scheduler_opts["${key}"]="${value}"
done

# Define the scheduler command for the host
time="${scheduler_opts[time]}"
nodes="${scheduler_opts[nodes]}"
ntasks="${scheduler_opts[ntasks-per-node]}"
other_args=()
for key in "${!scheduler_opts[@]}"; do
    [[ $key == nodes || $key == time || $key == ntasks-per-node ]] && continue
    other_args+=("--${key}" "${scheduler_opts[${key}]}")
done

if [[ "${host}" == "dahu" ]]; then

    cmd="/usr/bin/oarsub -l nodes=${nodes}/core=${ntasks},walltime=${time}"
    cmd="${cmd} ${other_args[*]} -S ./${script} ${script_args}"

fi

# Run the command
echo $cmd
# $cmd
