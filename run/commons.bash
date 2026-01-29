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
    # Run quality checks on given dates.
    #
    # Parameters
    # ----------
    # date_1, date_2, ...: str
    #     Dates to check. Accepted formats are anything parsable by the shell
    #     function `date` as long as the timezone is explicitly specified.
    #
    # Returns
    # -------
    # int
    #     Zero if all the dates are parsable and valid, non-zero otherwise.
    #
    for arg in "$@"; do
        echo "commons.bash: check_dates: checking date: \"$arg\""
        if ! date -d "${arg}" > /dev/null 2>&1; then
            echo "commons.bash: check_dates: invalid date." >&2
            return 1
        fi
        local not_forced_to_utc=$(TZ=Australia/Sydney date -d "${arg}" +%s)
        local forced_to_utc=$(TZ=Australia/Sydney date --utc -d "${arg}" +%s)
        if [[ "${not_forced_to_utc}" != "${forced_to_utc}" ]]; then
            echo "commons.bash: check_dates: implicit timezone." >&2
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

function utc {
    # Call the date function with parameters "as is" but enforce use of UTC.
    #
    # Parameters
    # ----------
    # Any: str
    #     Any parameter that can be passed to the date function. If a date is
    #     given (with -d or --date) then the timezone must be explicitly
    #     specified in the date.
    #
    # Returns
    # -------
    # int
    #     Zero if everything went well, non-zero otherwise.
    #
    # Echoes
    # ------
    # Whatever the date function echoes.
    #
    local i arg the_date
    for ((i = 1; i <= $#; i++)); do
        arg=${!i}
        if [[ "${arg}" == "-d" || "${arg}" == "--date" ]]; then
            if [[ $i < $# ]]; then
                i=$((i+1))
                the_date=${!i}
            else
                echo "commons.bash: utc: missing date." >&2
                return 3
            fi
        elif [[ "${arg}" == --date=* ]]; then
            the_date=${arg#--date=}
        fi
        if [[ -v the_date ]]; then
            if ! check_dates "${the_date}" > /dev/null 2>&1 ; then
                echo "commons.bash: utc: invalid date: ${the_date}." >&2
                return 4
            fi
        fi
    done
    date --utc "${@%$'\n'}"
    return $?
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
