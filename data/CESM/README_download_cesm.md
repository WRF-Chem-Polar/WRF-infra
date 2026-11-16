# Download and merge CESM daily files

Two Bash scripts:

- `download_cesm.sh` downloads daily NetCDF files into a temporary folder, then calls the merger once per month.
- `merge_cesm_monthly.sh` combines the available daily files using **ncrcat** (NCO). The downloader calls it automatically; it can also run by itself.

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

Once the download step works (see the known problem below), the downloads and the merges run in a single OAR job:

```bash
oarsub --project pr-regionalchem -l /core=1,walltime=24:00:00 \
    "bash /home/USER/WRF-infra/data/CESM/download_cesm.sh 2022-01-01 2022-03-31 \
     /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/input-data/chem/cesm"
```

### Known problem on dahu: downloads are blocked on the compute nodes

The download step does not currently work on dahu, for a network reason. The NCAR files are served through the OSDF/Pelican federation in two steps: the director (`osdf-director.osg-htc.org`, standard HTTPS) answers every request with a redirect (HTTP 307) to a data cache, and **all the caches listen on a non-standard HTTPS port**. The dahu compute nodes' network silently drops outgoing connections to a non-standard HTTPS port: the director answers from the compute nodes, but connections to the caches time out (measured on 2026-11-16; the same caches answer normally from other networks). Downloads therefore cannot run in OAR jobs on dahu until one of these is available:

- GRICAD opens outgoing connections to a non-standard HTTPS port on the compute network (a request to GRICAD support), or
- an alternative endpoint on a standard port is found for the d313008 collection.

Two further dahu notes:

- The container has no `wget`; the download script runs on the host, not in the container.
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
ncks -M time /scratch/$USER/cesm/2022-01-CESM.nc
ncks -v time -H /scratch/$USER/cesm/2022-01-CESM.nc
```

The downloaded files use the original NCAR filename prefix and `-21600.nc` suffix. `ncrcat` concatenates time records; it does **not** calculate monthly averages. Actual availability of files depends on the NCAR server.
