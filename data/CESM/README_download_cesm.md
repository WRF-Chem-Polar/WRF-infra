# Download and merge CESM daily files

Two Bash scripts:

- `download_cesm.sh` downloads daily NetCDF files into a temporary folder, then calls the merger once per month.
- `merge_cesm_monthly.sh` combines the available daily files using **CDO**. The downloader calls it automatically; it can also run by itself.

## Requirements

Linux with Bash, GNU `date`, `wget`, `cdo` and (for batch jobs) SLURM.
Keep the two `.sh` files in the **same directory**. Load CDO on your cluster if needed (`module load cdo`; module names vary).

## Download and merge

```bash
sbatch download_cesm.sh START_DATE END_DATE OUTPUT_DIR
```

For example:

```bash
sbatch download_cesm.sh 2022-01-01 2022-03-31 /scratch/$USER/cesm
```

Or run interactively:

```bash
bash download_cesm.sh 2022-01-01 2022-01-31 /scratch/$USER/cesm
```

Dates are **inclusive**. Date ranges may cross months and years, including leap years. The output folder is created if needed. The data set covers **2001-01-01 to 2022-12-31**; other dates are not on the server. Daily files are about 2.4 GB, so one month needs about 75 GB of disk space, up to twice as much during processing. Only one run at a time may use an output directory.

## Output files

Files are written directly to `OUTPUT_DIR`:

| Available dates | Output filename |
| --- | --- |
| All days of January 2022 | `2022-01-CESM.nc` |
| January 15–31 only | `2022-01-CESM-15-31.nc` |
| January 1–31 except January 15 | `2022-01-CESM-01-14.nc` and `2022-01-CESM-16-31.nc` |

**A month is complete only when every day of that calendar month is present.** A partial requested range or a failed download generates an `ERROR` and a **nonzero exit status**, even if its partial file was merged successfully. If no days are available, no NetCDF file is produced.

Daily downloads are staged in `OUTPUT_DIR/.cesm_raw_tmp/`. They are deleted after a successful **full-month** merge, but kept if the month is incomplete or the merge fails. Interrupted downloads use `.part` files and can be retried by rerunning the same command.

A successful retry replaces obsolete partial-month outputs with the updated output. Existing complete monthly files are skipped by the downloader.

## Merge already-downloaded files

For one month at a time:

```bash
bash merge_cesm_monthly.sh 2022-01-01 2022-01-31 \
    /scratch/$USER/cesm/.cesm_raw_tmp \
    /scratch/$USER/cesm
```

The standalone merger does **not** delete the daily input files.

## Check a result

```bash
cdo -s ntime /scratch/$USER/cesm/2022-01-CESM.nc
cdo -s showdate /scratch/$USER/cesm/2022-01-CESM.nc
```

The downloaded files use the original NCAR filename prefix and `-21600.nc` suffix. CDO `mergetime` concatenates time records; it does **not** calculate monthly averages. Actual availability of files depends on the NCAR server.
