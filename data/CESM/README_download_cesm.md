# Download and merge CESM daily files

Two Bash scripts:

- `download_cesm.sh` downloads daily NetCDF files into a temporary folder, then calls the merger once per month.
- `merge_cesm_monthly.sh` combines the available daily files using **ncrcat** (NCO). The downloader calls it automatically; it can also run by itself.

These scripts were written for, and have only been tested on, the **dahu** cluster (GRICAD; OAR scheduler). The dahu-specific behaviour is built in and automatic: on dahu the downloads are routed through cargo and the merge runs inside the WRF-Chem-Polar runtime container (see "Running on dahu"). On any other Linux host that meets the requirements below, the scripts download with a local `wget` instead; this has not been tested.

## Requirements

Linux with Bash, GNU `date`, `wget`, `flock` and the NCO tool `ncrcat` (for batch jobs, a scheduler such as SLURM or OAR).
Keep the two `.sh` files in the **same directory**. Load NCO on your cluster if needed (`module load nco`; module names vary). On dahu, `ncrcat` is provided by the WRF-Chem-Polar runtime container: the merger detects this and runs itself inside the container (see "Running on dahu" below).

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

## Running on dahu (GRICAD)

On dahu, all work goes through the queue (OAR jobs; they require a project: `--project pr-regionalchem`). The merge step works in an OAR job: the NCO tools (`ncrcat`) are not installed on the cluster itself, but they are provided by the WRF-Chem-Polar runtime container, and the merger detects this and re-runs itself inside the container automatically. The runtime container is at

    /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/containers/runtime.sif

The downloads and the merges run in a single OAR job (the downloads are routed through cargo; see below):

```bash
oarsub --project pr-regionalchem -l /core=1,walltime=24:00:00 \
    "bash /home/USER/WRF-infra/data/CESM/download_cesm.sh 2022-01-01 2022-03-31 \
     /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/input-data/chem/cesm"
```

### Downloads on dahu go through cargo

The NCAR data caches all use a non-standard HTTPS port, which the dahu compute nodes' network blocks (measured on 2026-11-16: the OSDF director answers from the compute nodes, but connections to the caches time out). The download script therefore runs wget on **cargo** (the GRICAD data transfer host) through SSH when it finds itself on a dahu node. cargo has open network access and mounts the same `/bettik` storage, so the files are written directly to the output directory. The rest of the script (merging through the runtime container) runs in the OAR job as usual.

One-time setup per user, for the SSH step to work:

- key-based SSH from the dahu nodes to cargo (the home directory is shared, so a key in `~/.ssh` works), and
- cargo's host key in `~/.ssh/known_hosts` (eg. run once from a dahu node: `ssh-keyscan cargo >> ~/.ssh/known_hosts`).

Two further dahu notes:

- The container has no `wget`; the download script runs on the host (on dahu: on cargo), not in the container.
- `wget` is forced to IPv4 in the download script: the OSDF director
  resolves to an IPv6 address first, and IPv6 is not routed on dahu
  (wget would otherwise time out on every retry).

## Output files

Files are written directly to `OUTPUT_DIR`:

| Available dates | Output filename |
| --- | --- |
| All days of January 2022 | `2022-01-CESM.nc` |
| January 15–31 only | `2022-01-CESM-15-31.nc` |
| January 1–31 except January 15 | `2022-01-CESM-01-14.nc` and `2022-01-CESM-16-31.nc` |

**A month is complete only when every day of that calendar month is present.** A partial requested range or a failed download generates an `ERROR` and a **nonzero exit status**, even if its partial file was merged successfully. If no days are available, no NetCDF file is produced.

Daily downloads are staged in `OUTPUT_DIR/.cesm_raw_tmp/`. They are deleted after a successful **full-month** merge, but kept if the month is incomplete or the merge fails. Interrupted downloads use `.part` files and can be retried by rerunning the same command.

If a run fails or is interrupted, rerun the same command; it resumes from what is already on disk (see "Restarting after a failure" below).

## Restarting after a failure

The script heals most failures by itself: the NCAR caches answer with sporadic HTTP errors that wget's own retries do not always ride out, so after one pass over a month, the days that are still missing are retried a few times with a pause in between (interrupted `.part` files are resumed, not restarted).

A run can still be cut short from the outside (walltime, network outage). Nothing needs to be cleaned up in that case: **rerun the same command** (on dahu: resubmit the same `oarsub` line), and the new run continues where the old one stopped:

- months whose `YYYY-MM-CESM.nc` already exists are skipped entirely;
- inside an incomplete month, days already present in `.cesm_raw_tmp/` are skipped; only the missing days are downloaded;
- a day whose download was interrupted resumes from its `.part` file (`wget -c`) instead of starting over;
- obsolete partial-month outputs (`YYYY-MM-CESM-DD-DD.nc`) are deleted automatically once the full month is merged;
- the lock file (`OUTPUT_DIR/.cesm.lock`) prevents a second run from using the same output directory while one is still active.

The `ERROR` lines in the job log name the days that are still missing. The exit status says whether a rerun is needed: `0` means every requested month is complete; nonzero means at least one month is incomplete or failed even after the script's own retries. A rerun that only fills a few gaps downloads only the missing days (a few minutes each) and then merges.

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
ncks -M /scratch/$USER/cesm/2022-01-CESM.nc
ncks -v time -H /scratch/$USER/cesm/2022-01-CESM.nc
```

`ncks -M` prints the file header, including the record dimension (`time = UNLIMITED ; // (124 currently)` for a full month, 4 six-hourly records per day).

The downloaded files use the original NCAR filename prefix and `-21600.nc` suffix. `ncrcat` concatenates time records; it does **not** calculate monthly averages. Actual availability of files depends on the NCAR server.
