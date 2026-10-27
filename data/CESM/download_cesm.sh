#!/bin/bash
#
# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Download CESM daily files, then merge them into monthly NetCDF files.
# Usage: sbatch download_cesm.sh START_DATE END_DATE OUTPUT_DIR
# Example: sbatch download_cesm.sh 2022-01-01 2022-03-31 /scratch/$USER/cesm
#
# Add cluster-specific directives below if needed (eg. --account on Jean Zay).

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=24:00:00

set -u

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 START_DATE END_DATE OUTPUT_DIR" >&2
    exit 1
fi

start=$1
end=$2
output_dir=$3
raw_dir="$output_dir/.cesm_raw_tmp"

base_url="https://osdf-director.osg-htc.org/ncar/gdex/d313008/hist"
prefix="FCnudged_f09.mam.mar27.2000_2021.001.cam.h2"
merge_script="$(dirname "$(readlink -f "$0")")/merge_cesm_monthly.sh"

# Check dates and required commands.
for day in "$start" "$end"; do
    if [[ $(date -u -d "$day" +%F 2>/dev/null) != "$day" ]]; then
        echo "ERROR: Invalid date: $day (use YYYY-MM-DD)" >&2
        exit 1
    fi
done
if [[ "$start" > "$end" ]]; then
    echo "ERROR: Start date is after end date." >&2
    exit 1
fi
for program in wget cdo; do
    command -v "$program" >/dev/null || { echo "ERROR: $program is not installed." >&2; exit 1; }
done
[[ -f "$merge_script" ]] || { echo "ERROR: Missing $merge_script" >&2; exit 1; }
mkdir -p "$raw_dir" || exit 1

# Refuse to run if another instance is already using the output directory.
exec 9>"$output_dir/.cesm.lock"
flock -n 9 || { echo "ERROR: $output_dir is already in use by another run." >&2; exit 1; }
# Remove the lock file on exit (the lock itself is released automatically);
# a run must not leave temporary files behind.  Raw files of incomplete
# months are the only exception, kept so that a retry can resume them.
trap 'rm -f "$output_dir/.cesm.lock"' EXIT

errors=0
current=$start

while [[ ! "$current" > "$end" ]]; do
    month=${current:0:7}
    last_day=$(date -u -d "$month-01 +1 month -1 day" +%F)
    [[ "$end" < "$last_day" ]] && last_day=$end

    echo "=== $month: $current to $last_day ==="

    # A finished calendar month does not need downloading again.
    if [[ "$current" == "$month-01" &&
          "$last_day" == "$(date -u -d "$month-01 +1 month -1 day" +%F)" &&
          -s "$output_dir/$month-CESM.nc" ]]; then
        echo "Already complete: $month-CESM.nc"
    else
        day=$current
        while [[ ! "$day" > "$last_day" ]]; do
            filename="$prefix.$day-21600.nc"
            file="$raw_dir/$filename"
            url="$base_url/${day:0:4}/$filename"

            if [[ ! -s "$file" ]]; then
                echo "Downloading $day"
                if wget -nv -c --tries=5 --timeout=60 -O "$file.part" "$url" && [[ -s "$file.part" ]]; then
                    mv "$file.part" "$file"
                else
                    echo "ERROR: Could not download $day" >&2
                fi
            fi
            day=$(date -u -d "$day +1 day" +%F)
        done

        # Missing days are handled by the merger (partial files + an error).
        if bash "$merge_script" "$current" "$last_day" "$raw_dir" "$output_dir"; then
            # Delete raw files only if the entire calendar month succeeded.
            day=$current
            while [[ ! "$day" > "$last_day" ]]; do
                rm -f "$raw_dir/$prefix.$day-21600.nc"
                day=$(date -u -d "$day +1 day" +%F)
            done
        else
            errors=1
            echo "ERROR: $month incomplete or merge failed; raw files kept." >&2
        fi
    fi
    current=$(date -u -d "$last_day +1 day" +%F)
done

rmdir "$raw_dir" 2>/dev/null || true
echo "Finished. Output directory: $output_dir"
exit "$errors"
