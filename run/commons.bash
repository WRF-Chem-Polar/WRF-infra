#!/bin/bash
#
# Copyright (c) 2025 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# This file contains common resources for running WPS and WRF[-Chem].
#

function check_paths {
    # Run quality checks on given path(s).
    #
    # Parameters
    # ----------
    # path_1, path_2, ...: str
    #     Paths to check
    #
    # Returns
    # -------
    # int
    #     Zero if all given paths pass all quality checks, non-zero otherwise.
    #
    # Notes
    # -----
    # List of quality checks:
    # - The path is not empty.
    # - The path contains no spaces.
    #
    for arg in "$@"; do
        echo "commons.bash: check_paths: checking path: $arg"
        if [[ $(echo $arg | grep -cE "[[:space:]]") -ne 0 ]]; then
            return 1
        elif [[ -z $arg ]]; then
            return 2
        fi
    done
    return 0
}

function check_dates {
    # Run quality check on given dates.
    #
    # Parameters
    # ----------
    # date_1, date_2, ...: str
    #     Dates to check. Accepted formats are:
    #     - YYYY-mm-ddZ
    #     - YYYY-mm-ddTHH:MMZ
    #     (the Z at the end enforces UTC)
    #
    # Returns
    # -------
    # int
    #     Zero if all the dates are parsable and valid, non-zero otherwise.
    #
    local d="[0-9]"
    local re_date="$d$d$d$d-$d$d-$d$d"
    local re_time="$d$d:$d$d"
    for arg in "$@"; do
        echo "commons.bash: check_dates: checking date: \"$arg\""
        if [[ ! "${arg}" =~ ^${re_date}(|T${re_time})Z$ ]]; then
            echo "commons.bash: check_dates: invalid format." >&2
            return 1
        elif ! date -d "${arg}" > /dev/null 2>&1; then
            echo "commons.bash: check_dates: invalid date." >&2
            return 2
        fi
    done
    return 0
}

function check_period {
    # Run quality check on given period.
    #
    # Parameters
    # ----------
    # date_start: str
    #     Start date of the period.
    # date_end: str
    #     End date of the period.
    #
    # Returns
    # -------
    # int
    #     Zero if the period is correct (dates are valid and
    #     end_date > start_date), non-zero otherwise.
    #
    echo "commons.bash: check_period: $@."
    if [[ $# -ne 2 ]]; then
        echo "commons.bash: check_period: need exactly 2 arguments." >&2
        return 1
    elif ! check_dates "$1" "$2"; then
        echo "commons.bash: check_period: invalid date(s)." >&2
        return 2
    fi
    local opts="--utc --rfc-3339=ns"
    local start=$(date ${opts} --date="$1")
    local end=$(date ${opts} --date="$2")
    if [[ ! "${end}" > "${start}" ]]; then
        echo "commons.bash: check_period: start >= end." >&2
        return 3
    fi
    return 0
}

if [[ $check_simulation_conf == yes ]]; then

    echo "commons.bash: Quality checking the simulation's configuration..."
    echo "commons.bash: This will stop execution of the script in case of"
    echo "commons.bash: problem only if the Bash \"e\" option is set. This"
    if [[ $- == *e* ]]; then
        echo "commons.bash: option is currently set."
    else
        echo "commons.bash: option is currently NOT set."
    fi

    # Run quality-checks on paths (note that the user-provided runids will be
    # used in paths, so we check them in the same way)
    check_paths "$runid_wps"
    check_paths "$runid_real"
    check_paths "$runid_wrf"
    check_paths "$(pwd)"
    check_paths "$dir_wps"
    check_paths "$dir_wrf"
    check_paths "$dir_shared_data"
    check_paths "$dir_outputs"
    check_paths "$dir_work"
    check_paths "$namelist_wps"
    check_paths "$namelist_real"
    check_paths "$namelist_wrf"

    # Run quality checks on dates
    check_period "${date_start}" "${date_end}"

    if [[ $- == *e* ]]; then
        echo "commons.bash: no problem detected in the simulation's config."
    fi

fi
