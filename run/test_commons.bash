#!/bin/bash
#
# Copyright (c) 2025 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).
#
# This file contains unit tests for ./commons.bash (the common bash resources
# for our WPS and WRF[-Chem] simulations). When executed, it exits with a zero
# error code if all tests pass, and with a non-zero error code otherwise.
#

source ./commons.bash

n_failed=0

# Unit tests for: check_paths

valid_path_1=/a/valid/path
valid_path_2=another/valid/path
valid_path_3=.
invalid_path_1="dirname with spaces/subdir"
invalid_path_2=

if ! check_paths "$valid_path_1"; then
    echo A unit test has failed: check_paths "valid_path_1"
    ((n_failed++))
fi
if ! check_paths "$valid_path_1" "$valid_path_2"; then
    echo A unit test has failed: check_paths "$valid_path_1" "$valid_path_2"
    ((n_failed++))
fi
if ! check_paths "$valid_path_1" "$valid_path_2" "$valid_path_3"; then
    echo A unit test has failed: check_paths "$valid_path_1" "$valid_path_2" "$valid_path_3"
    ((n_failed++))
fi
if check_paths "$invalid_path_1"; then
    echo A unit test has failed: "!" check_paths "$invalid_path_1"
    ((n_failed++))
fi
if check_paths "$invalid_path_2"; then
    echo A unit test has failed: "!" check_paths "$invalid_path_2"
    ((n_failed++))
fi
if check_paths "$valid_path_1" "$invalid_path_1"; then
    echo A unit test has failed: "!" check_paths "$valid_path_1" "$invalid_path_1"
    ((n_failed++))
fi

# Unit tests for check_dates

valid_date_1="2025-12-31Z"
valid_date_2="2025-05-12T21:50Z"
valid_date_3="2028-02-29Z"
invalid_date_1="2026-02-29Z"
invalid_date_2="2025-12-31T00:00"
invalid_date_3="hello world"

if ! check_dates "${valid_date_1}"; then
    echo A unit test has failed: check_dates "${valid_date_1}"
    ((n_failed++))
fi
if ! check_dates "${valid_date_2}"; then
    echo A unit test has failed: check_dates "${valid_date_2}"
    ((n_failed++))
fi
if ! check_dates "${valid_date_3}"; then
    echo A unit test has failed: check_dates "${valid_date_3}"
    ((n_failed++))
fi
if ! check_dates "${valid_date_1}" "${valid_date_2}"; then
    echo A unit test has failed: check_dates "${valid_date_1}" "${valid_date_2}"
    ((n_failed++))
fi
if check_dates "${invalid_date_1}"; then
    echo A unit test has failed: check_dates "${invalid_date_1}"
    ((n_failed++))
fi
if check_dates "${invalid_date_2}"; then
    echo A unit test has failed: check_dates "${invalid_date_2}"
    ((n_failed++))
fi
if check_dates "${invalid_date_3}"; then
    echo A unit test has failed: check_dates "${invalid_date_3}"
    ((n_failed++))
fi
if check_dates "${valid_date_1}" "${invalid_date_3}"; then
    echo A unit test has failed: check_dates "${valid_date_1}" "${invalid_date_3}"
    ((n_failed++))
fi

# Unit tests for check_period

valid_date_1="2025-12-31Z"
valid_date_2="2026-05-12T21:50Z"
valid_date_3="1789-07-14Z"
invalid_date_1="2026-02-21"

if ! check_period "${valid_date_1}" "${valid_date_2}"; then
    echo A unit test has failed: check_period "${valid_date_1}" "${valid_date_2}"
    ((n_failed++))
fi
if ! check_period "${valid_date_3}" "${valid_date_1}"; then
    echo A unit test has failed: check_period "${valid_date_3}" "${valid_date_1}"
    ((n_failed++))
fi
if check_period "${valid_date_2}" "${valid_date_1}"; then
    echo A unit test has failed: check_period "${valid_date_2}" "${valid_date_1}"
    ((n_failed++))
fi
if check_period "${valid_date_1}" "${valid_date_1}"; then
    echo A unit test has failed: check_period "${valid_date_1}" "${valid_date_1}"
    ((n_failed++))
fi
if check_period "${valid_date_1}"; then
    echo A unit test has failed: check_period "${valid_date_1}"
    ((n_failed++))
fi
if check_period "${valid_date_1}" "${invalid_date_1}"; then
    echo A unit test has failed: check_period "${valid_date_1}" "${invalid_date_1}"
    ((n_failed++))
fi

# Unit tests for utc

valid_date_1="2025-12-31Z"
valid_date_2="2025-12-31Z + 1 day"
invalid_date="2026-02-21"

if ! utc -d "${valid_date_1}" > /dev/null 2>&1; then
    echo A unit test has failed: utc "${valid_date_1}"
    ((n_failed++))
fi
if ! utc --date "${valid_date_1}" > /dev/null 2>&1; then
    echo A unit test has failed: utc "${valid_date_1}"
    ((n_failed++))
fi
if ! utc --date="${valid_date_1}" > /dev/null 2>&1; then
    echo A unit test has failed: utc "${valid_date_1}"
    ((n_failed++))
fi
if ! utc --date="${valid_date_2}" > /dev/null 2>&1; then
    echo A unit test has failed: utc "${valid_date_2}"
    ((n_failed++))
fi
if utc --date="${invalid_date}" > /dev/null 2>&1; then
    echo A unit test has failed: utc "${invalid_date}"
    ((n_failed++))
fi
if [[ $(utc --date=2025-12-15T21:00Z "+%Y%d %H%M") != "202515 2100" ]]; then
    echo A unit test has failed: utc --date=2025-12-15T21:00Z +%Y%d %H%M
    ((n_failed++))
fi

# Conclusion

echo -e "\nSummary:"
if [[ $n_failed -eq 0 ]]; then
    echo "All tests have passed."
elif [[ $n_failed -eq 1 ]]; then
    echo "$n_failed test has failed."
else
    echo "$n_failed tests have failed."
fi

exit $n_failed
