#!/bin/bash
#
# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Merge daily CESM NetCDF files for ONE month.
# Usage: bash merge_cesm_monthly.sh START_DATE END_DATE RAW_DIR OUTPUT_DIR
# Full month:    YYYY-MM-CESM.nc
# Partial month: YYYY-MM-CESM-STARTDAY-ENDDAY.nc (plus an error)
#

set -u

if [[ $# -ne 4 ]]; then
    echo "Usage: $0 START_DATE END_DATE RAW_DIR OUTPUT_DIR" >&2
    exit 1
fi

start=$1
end=$2
raw_dir=$3
output_dir=$4
month=${start:0:7}
prefix="FCnudged_f09.mam.mar27.2000_2021.001.cam.h2"
month_end=$(date -u -d "$month-01 +1 month -1 day" +%F)

if [[ "$month" != "${end:0:7}" ]]; then
    echo "ERROR: Merge only one month at a time." >&2
    exit 1
fi
command -v cdo >/dev/null || { echo "ERROR: cdo is not installed." >&2; exit 1; }
mkdir -p "$output_dir" || exit 1

incomplete=0
failed=0
files=()
outputs=()

if [[ "$start" != "$month-01" || "$end" != "$month_end" ]]; then
    echo "ERROR: Requested dates do not cover all of $month." >&2
    incomplete=1
fi

# Write one file for a consecutive group of available days.
merge_days() {
    [[ ${#files[@]} -eq 0 ]] && return

    if [[ "$first" == "$month-01" && "$last" == "$month_end" ]]; then
        name="$month-CESM.nc"
    else
        name="$month-CESM-${first:8:2}-${last:8:2}.nc"
    fi

    temporary="$output_dir/.$name.tmp.$$"
    echo "Merging $first to $last -> $name"
    operation=mergetime
    [[ ${#files[@]} -eq 1 ]] && operation=copy
    if cdo -O "$operation" "${files[@]}" "$temporary" && \
       [[ -s "$temporary" ]] && mv "$temporary" "$output_dir/$name"; then
        outputs+=("$name")
    else
        echo "ERROR: CDO merge failed for $name" >&2
        rm -f "$temporary"
        failed=1
    fi
    files=()
}

day=$start
while [[ ! "$day" > "$end" ]]; do
    file="$raw_dir/$prefix.$day-21600.nc"

    if [[ -s "$file" ]]; then
        [[ ${#files[@]} -eq 0 ]] && first=$day
        files+=("$file")
        last=$day
    else
        echo "ERROR: Missing daily file for $day" >&2
        incomplete=1
        merge_days
    fi
    day=$(date -u -d "$day +1 day" +%F)
done
merge_days

# Remove obsolete partial outputs after successful merging (e.g. on retry).
if (( failed == 0 && ${#outputs[@]} > 0 )); then
    for old in "$output_dir/$month"-CESM-??-??.nc; do
        [[ -f "$old" ]] || continue
        [[ " ${outputs[*]} " == *" ${old##*/} "* ]] || rm -f "$old"
    done
fi

if (( failed )); then exit 1; fi
if (( incomplete )); then exit 2; fi
exit 0
