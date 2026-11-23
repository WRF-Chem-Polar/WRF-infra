#!/bin/bash
#
# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# Download CESM daily files, then merge them into monthly NetCDF files.
# Usage: bash download_cesm.sh START_DATE END_DATE OUTPUT_DIR
# Example: bash download_cesm.sh 2022-01-01 2022-03-31 /scratch/$USER/cesm
#
# Submit through your scheduler if needed (eg. sbatch on SLURM clusters,
# oarsub on OAR clusters such as dahu; see README_download_cesm.md).
#
# Written for and tested on the dahu cluster (GRICAD) only; the
# dahu-specific behaviour (downloads through cargo, merge through the
# runtime container) is automatic. Failed downloads are retried by the
# script itself; if a run is cut short (eg. walltime), rerunning the
# same command resumes where it stopped. See README_download_cesm.md.

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

# Where to run wget. The NCAR data caches all use a non-standard
# HTTPS port, which the dahu compute nodes' network blocks. cargo
# (the GRICAD data transfer host) has open network access and mounts
# the same /bettik storage, so on dahu the downloads run on cargo
# through SSH and the files are written directly to the shared
# storage. Everywhere else, wget runs locally.
download_host=""
if [[ "$(hostname)" == dahu* ]]; then
    download_host="cargo"
fi

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
# wget and flock run on the host. The merge tool (ncrcat) is checked by
# the merger itself, which falls back to the WRF-Chem-Polar runtime
# container if ncrcat is not installed (the situation on dahu).
for program in wget flock; do
    command -v "$program" >/dev/null || { echo "ERROR: $program is not installed." >&2; exit 1; }
done
# On dahu, the downloads run on the transfer host; check that it is
# reachable through SSH before starting.
if [[ -n "$download_host" ]]; then
    ssh -o BatchMode=yes "$download_host" true \
        || { echo "ERROR: cannot reach $download_host through SSH." >&2; exit 1; }
fi
[[ -f "$merge_script" ]] || { echo "ERROR: Missing $merge_script" >&2; exit 1; }
mkdir -p "$raw_dir" || exit 1

# Refuse to run if another instance is already using the output directory.
exec 9>"$output_dir/.cesm.lock"
flock -n 9 || { echo "ERROR: $output_dir is already in use by another run." >&2; exit 1; }
# Remove the lock file on exit (the lock itself is released automatically);
# a run must not leave temporary files behind.  Raw files of incomplete
# months are the only exception, kept so that a retry can resume them.
trap 'rm -f "$output_dir/.cesm.lock"' EXIT

# Download one daily file into PART_FILE. Returns 0 on success.
# On dahu, run wget on the transfer host (cargo); the paths are the
# same there as here because /bettik is shared. Elsewhere, run wget
# locally. IPv4 is forced because the OSDF director resolves to an
# IPv6 address first, and IPv6 is not routed everywhere (eg. on
# dahu, wget would time out on every retry).
download_day() {
    local url="$1"
    local part_file="$2"

    if [[ -n "$download_host" ]]; then
        ssh -o BatchMode=yes "$download_host" \
            "wget -4 -nv -c --tries=5 --timeout=60 -O '$part_file' '$url'"
    else
        wget -4 -nv -c --tries=5 --timeout=60 -O "$part_file" "$url"
    fi
}

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
        # Download the days of the month. The NCAR caches fail
        # sporadically with HTTP errors that wget's own retries do not
        # always ride out, so after one pass over the month, the days
        # that are still missing are retried a few times with a pause
        # in between. wget -c resumes the interrupted .part files, so
        # a retry continues where it stopped. This way a run heals
        # itself instead of ending with gaps that need a new job.
        pass=1
        max_passes=5
        while (( pass <= max_passes )); do
            missing=""
            day=$current
            while [[ ! "$day" > "$last_day" ]]; do
                filename="$prefix.$day-21600.nc"
                file="$raw_dir/$filename"
                url="$base_url/${day:0:4}/$filename"

                if [[ ! -s "$file" ]]; then
                    echo "Downloading $day"
                    if download_day "$url" "$file.part" && [[ -s "$file.part" ]]; then
                        mv "$file.part" "$file"
                    else
                        echo "ERROR: Could not download $day" >&2
                        missing="$missing $day"
                    fi
                fi
                day=$(date -u -d "$day +1 day" +%F)
            done

            # Stop as soon as every day of the month is on disk.
            [[ -z "$missing" ]] && break
            # Give up on the last pass and let the merger write the
            # partial output; otherwise wait a bit and try again.
            (( pass == max_passes )) && break
            echo "Retrying failed days of $month (pass $((pass + 1)) of $max_passes):$missing"
            sleep 60
            pass=$((pass + 1))
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
