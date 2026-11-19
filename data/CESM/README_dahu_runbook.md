# CESM downloads on dahu: a manual OAR runbook

Step-by-step instructions for running the CESM download scripts on the
**dahu** cluster (GRICAD) by hand: plain SSH from your laptop, OAR jobs
on the cluster, no other tooling. Everything dahu-specific — routing
the downloads through **cargo**, the GRICAD data transfer host, and
merging inside the WRF-Chem-Polar runtime container — is automatic.

What the scripts do, their requirements, and the output-file naming
are described in [`README_download_cesm.md`](README_download_cesm.md).
This page is only about driving them on dahu with OAR.

## What a run looks like

One OAR job does everything, in this order:

1. for every day of the requested period, download the daily file —
   on dahu this runs on cargo, over SSH, transparently;
2. for every complete month, merge the daily files into one monthly
   NetCDF file with `ncrcat` — on dahu this runs inside the runtime
   container, again automatically;
3. clean up after itself (raw daily files, lock file, obsolete
   partial-month files).

You submit the job, you watch it, you check the result. If anything
failed, you resubmit the same command and the run picks up where it
stopped. That is the whole workflow.

## One-time setup

### A working clone on dahu

On dahu, clone this repository (or update the one you have):

```bash
ssh <dahu>
git clone https://github.com/WRF-Chem-Polar/WRF-infra.git ~/WRF-infra   # once
cd ~/WRF-infra && git pull                                             # to update
```

The scripts live in `data/CESM/`. If your clone does not have them,
switch to the branch that does (until the scripts are merged into
`main`).

### SSH to cargo, from the compute nodes

The downloads run on cargo, launched over SSH by the script itself.
For that to work, once per user:

1. You need an SSH key without a passphrase (the script uses
   non-interactive SSH). Check with `ls ~/.ssh/id_*`; if you have none:

   ```bash
   ssh-keygen -N "" -f ~/.ssh/id_ed25519
   ```

2. Your public key must be listed in `~/.ssh/authorized_keys` — the
   home directory is shared between dahu and cargo, so one file
   serves both. Check, and add yourself if needed:

   ```bash
   cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys   # only if missing
   ```

3. cargo's host key must be in `~/.ssh/known_hosts`. Do this and the
   test below inside a small OAR job (the SSH test needs to run from a
   node of the cluster):

   ```bash
   oarsub --project pr-regionalchem -l /core=1,walltime=0:10:00 \
       "ssh-keyscan cargo >> ~/.ssh/known_hosts \
        && ssh -o BatchMode=yes cargo true && echo SSH-TO-CARGO-OK"
   ```

   The job output must end with `SSH-TO-CARGO-OK` (after the
   usual keyscan noise).

### Your OAR project

OAR jobs on dahu are submitted with the project allocation
`pr-regionalchem` — every `oarsub` in this runbook carries
`--project pr-regionalchem`. Use your own project if you work
under a different allocation (in that case also use a different
output directory).

## Submit the download job

Log in to dahu, `cd` into your clone (OAR writes its log files in
the directory you submit from), and submit:

```bash
cd ~/WRF-infra
oarsub --project pr-regionalchem -l /core=1,walltime=24:00:00 \
    "bash $HOME/WRF-infra/data/CESM/download_cesm.sh 2022-01-01 2022-03-31 \
     /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/input-data/chem/cesm"
```

Notes:

- Replace the two dates with your period (inclusive; the data set
  covers 2001-01-01 to 2022-12-31).
- The example output directory is the project's shared one; use
  another writable directory to keep the data to yourself.
- One core is enough; the run is network-bound, not CPU-bound.
- **Walltime**: a measured quarter-year run (one month already on
  disk) took about 16 h; download pace varies roughly from 6
  minutes/day in the evening up to 25 minutes/day at night. Keep
  24 h walltime for quarter-year chunks and scale up for longer
  ranges.
- Disk: about 2.4 GB per day, ~75-80 GB per full month, and up to
  twice that transiently during processing.
- Note the job id that `oarsub` prints; below it is `<id>`.

Do **not** submit a second job for the same output directory while
one is still running: a lock file makes the second run refuse to
start.

## Monitor the job

```bash
oarstat                 # list your jobs and their state
oarstat -j <id> -f      # everything about one job
```

States you will see: `Waiting` (queued), `Running`, then
`Terminated` (or `Error`) when done. The detailed view also shows
the `launching_directory` and the `stdout`/`stderr` file names.

The job writes `OAR.<id>.stdout` and `OAR.<id>.stderr` in the
directory you submitted from (here: `~/WRF-infra`). Useful things to
watch in the stdout while the run goes:

- `Downloading 2022-01-05` / `-21600.nc saved` — the daily grind;
- `Already complete: 2022-01-CESM.nc` — a month skipped because its
  output file already exists;
- `Merging 2022-01 ...` — a month being concatenated;
- lines about retrying missing days — normal: the NCAR caches are
  flaky and the script makes up to 5 passes over each month.

Cancelling a job you no longer want: `oardel <id>`. Nothing needs
cleaning up; a later rerun resumes from what is on disk.

## When the job has finished

### Read the exit status

```bash
oarstat -j <id> -f | grep exit_status_code
```

- `exit_status_code = 0`: every requested month was downloaded and
  merged. Done.
- Nonzero: at least one month is still incomplete. The `ERROR` lines
  in the stderr (and stdout) name the days that are missing.

### Rerun if days are missing

Cache failures that survive the script's own retries are recovered
by simply **resubmitting exactly the same command** — a rerun skips
everything that is already on disk (complete months, complete days,
even half-downloaded days resume), so it costs only the gaps:

```bash
cd ~/WRF-infra
oarsub --project pr-regionalchem -l /core=1,walltime=24:00:00 \
    "bash $HOME/WRF-infra/data/CESM/download_cesm.sh 2022-01-01 2022-03-31 \
     /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/input-data/chem/cesm"
```

Scale the walltime to the length of the remaining gap (a few gaps
are filled in minutes; a whole missing month needs hours).

Also resubmit the same way if the job was killed by the walltime or
by a storage hiccup: nothing is corrupted, the pre-flight check
aborts cleanly before writing if the output directory is not
writable, and the rerun picks up from what is on disk.

### Check the result files

```bash
ls -lh <output-dir>          # one YYYY-MM-CESM.nc (~75-80 GB) per full month
ls <output-dir>/.cesm_raw_tmp 2>/dev/null   # should not exist after success
```

A partial month is merged too, as `YYYY-MM-CESM-DD-DD.nc`, and is
deleted automatically once the full month is available.

### Verify a monthly file (optional but recommended)

`ncrcat` and `ncks` are not installed on the dahu host; they are in
the project runtime container. Apptainer only works on the compute
nodes, so the check is a small throwaway job (the `@` inside the
container activates the project environment):

```bash
oarsub --project pr-regionalchem -l /core=1,walltime=0:10:00 \
    "apptainer exec -B /bettik \
     /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/containers/runtime.sif \
     @ ncks -M <output-dir>/2022-03-CESM.nc | head -40"
```

For a structurally sound monthly file the header contains a line
like `time = UNLIMITED ; // (124 currently)` — 124 records for a
31-day month, 112 for a 28-day February (4 six-hourly records per
day).

## Clean up the OAR logs

Once you have checked the job's result, delete its log files:

```bash
rm OAR.<id>.stdout OAR.<id>.stderr
```

Keep them only while a job still needs investigating.

## Good to know

- All work happens in OAR jobs: the downloads (on cargo), the merges
  (container), and even the `ncks` check. Nothing heavy runs on the
  login nodes — apptainer does not even start there (user namespaces
  are disabled on the login nodes).
- You never log in to cargo manually; the script reaches it over SSH
  because the compute nodes cannot reach the NCAR caches directly
  while cargo can.
- `/bettik` is shared between dahu's nodes and cargo, so the files
  written on cargo land directly in the output directory.
- The script's own retries (up to 5 passes per month, with pauses)
  absorb most of the sporadic NCAR cache errors. What is still
  missing afterwards is filled by one rerun of the same command.
- Time bounds of the data: each daily file holds the records from
  06:00 to 24:00 UTC of its day, so a merged month runs from the
  1st 06:00 to the 1st of the next month 00:00. The 00:00 and 06:00
  records of the 1st live in the previous month's file. Keep this in
  mind when a WRF run needs exact month-boundary times.
- The complete-restart behaviour is documented, with the file
  naming rules, in [`README_download_cesm.md`](README_download_cesm.md).

## Cheat sheet

```bash
# one-time: cargo SSH works?
oarsub --project pr-regionalchem -l /core=1,walltime=0:10:00 \
    "ssh-keyscan cargo >> ~/.ssh/known_hosts \
     && ssh -o BatchMode=yes cargo true && echo SSH-TO-CARGO-OK"

# the download job
cd ~/WRF-infra && git pull
oarsub --project pr-regionalchem -l /core=1,walltime=24:00:00 \
    "bash $HOME/WRF-infra/data/CESM/download_cesm.sh 2022-01-01 2022-03-31 \
     /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/input-data/chem/cesm"

# watch
oarstat -j <id> -f
tail -f OAR.<id>.stdout

# verdict (0 = complete; nonzero = rerun the same command)
oarstat -j <id> -f | grep exit_status_code

# verify one merged month
oarsub --project pr-regionalchem -l /core=1,walltime=0:10:00 \
    "apptainer exec -B /bettik \
     /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/containers/runtime.sif \
     @ ncks -M /bettik/PROJECTS/pr-regionalchem/COMMON/WRF-Chem-Polar/input-data/chem/cesm/2022-03-CESM.nc | head -40"

# tidy up once checked
rm OAR.<id>.stdout OAR.<id>.stderr
```
