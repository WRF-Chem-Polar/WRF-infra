# Code Review of WRF-infra

- **Date of review:** 13 November 2026
- **Repository reviewed:** [WRF-Chem-Polar/WRF-infra](https://github.com/WRF-Chem-Polar/WRF-infra)
- **Commit reviewed:** `adeda4b9` ("Make namelist.py add newline at end when writing namelists")
- **Scope:** every file in the repository — the Python library (`pymodules/`), the compile
  scripts (`compile/`), the run scripts (`run/`), the data scripts (`data/`), the testing
  tools (`testing/`), the environment definitions (`env/`), the documentation (`doc/`),
  and the continuous integration set-up (`.github/workflows/`).

This review is written to be read by humans, in plain language. Every finding points to
the file (and, where useful, the line) it refers to, explains *why* it matters, and, where
a fix is obvious, shows what the fix could look like. Code snippets in this document follow
the same rule: they are written to be read by humans, with comments explaining each step.

---

## 1. Executive summary

WRF-infra is the "everything around the model" repository for WRF-Chem-Polar: it compiles
WPS, WRF and WRF-Chem-Polar, downloads and prepares input data, orchestrates the
WPS → real → WRF-Chem chain on HPC schedulers, and plots the results.

**Overall, this is a well-above-average research software repository.** The core Python
library is clean, documented and tested; the Bash commons are unusually careful (explicit
timezone enforcement, path validation, documented return codes); and reproducibility has
clearly been a design goal, not an afterthought (compile options are recorded with the
exact Git commit, patches are versioned in-tree, and there is a written checklist for
reproducing a simulation).

The main weaknesses are:

1. a handful of small, confirmed bugs (silent no-op error checks, a broken link,
   an error message that prints a placeholder instead of a path);
2. a fragile, undocumented import mechanism based on Git symlinks, and a
   `pyproject.toml` that cannot actually be installed;
3. documentation drift in a few places (the tutorials no longer match the scripts);
4. a large gap between the polished core (`pymodules/`, `commons.bash`) and the rougher
   research scripts (`add_chloroa_wps.py`, `add_dmsocean_wps.py`, parts of the jobscripts);
5. and, most importantly for users, **several manual steps that could be automated** —
   the building blocks for automation already exist inside the repository but are not yet
   connected together.

---

## 2. What the repository does (quick orientation)

| Directory | Purpose |
|---|---|
| `pymodules/wrfinfra/` | Shared Python library: host detection, subprocess helpers, namelist reader/writer, compilation logic |
| `compile/` | Scripts to clone, patch, configure and compile WPS, WRF-Chem-Polar and the WRF-Chem preprocessing tools |
| `run/` | Jobscripts for the three stages of a simulation (WPS, real, WRF-Chem) plus shared Bash resources and the simulation configuration |
| `data/` | Download / pre-processing scripts for external input data (ERA5, CAMS, chlorophyll-a) |
| `testing/` | Test-case orchestration and plotting of results |
| `env/` | One configuration file per supported machine (Spirit, Jean Zay, dahu, jed) + the hostname map |
| `doc/` | Tutorials and a reproducibility checklist |

---

## 3. What is well coded

### 3.1 The core Python library is genuinely good

`pymodules/wrfinfra/generic.py` and `compilation.py` are a pleasure to review:

- **Every function has a NumPy-style docstring** with parameters, returns and raised
  exceptions. Error messages are complete sentences that say *what* failed and *why*
  (e.g. `"Unknown host platform: <name>."` rather than a bare traceback).
- **Subprocess calls go through wrappers** (`generic.run`, `generic.run_stdout`) that
  check the return code and raise a clear error on failure. Many repositories call
  `subprocess.run` directly and ignore failures; this one does not.
- **Host detection is data-driven**: `env/hosts` maps hostname patterns to friendly names,
  and the mapping file itself is documented, including the precedence rule when several
  patterns match. Adding a new machine means adding one line to a data file, not editing
  Python.
- **The scheduler is abstracted** via `job-header-prefix` / `job-header-separator` /
  `job-header-option-*` keys in the per-machine config files. The compile scripts can
  generate correct Slurm headers *without knowing it is Slurm* — a clean design that
  would also work for PBS or LoadLeveler.

### 3.2 The namelist tool and its tests

`pymodules/wrfinfra/namelist.py` is a small, focused, well-designed tool:

- It parses WRF namelists into a structure, and writes them back out **column-aligned**
  (it computes the width of the longest key and the widest value and pads accordingly).
  Round-tripping a real namelist produces byte-identical output — and there is an
  integration test that proves it (`test_namelist.py`, `TestIntegrationNamelist`).
- It distinguishes quoted from unquoted values, which matters because WRF treats
  `'2018-03-15'` and `2018-03-15` differently. Many quick-and-dirty namelist parsers
  get this wrong; this one has 15 unit tests for value processing alone.
- It works both as an importable module and as a command-line tool
  (`python namelist.py --namelist ... --read domains/dx-0`), which is exactly how the
  jobscripts use it.
- Known parsing limitations are *documented in the code* with a pointer to the tracking
  issue (`#192`) rather than left as surprises.

### 3.3 The Bash commons are unusually careful

`run/commons.bash` deserves specific praise:

- **Explicit timezone enforcement.** `check_dates` rejects any date without an explicit
  timezone, using a clever trick: it parses the date twice — once as `Australia/Sydney`
  and once forced to UTC — and rejects it if the two disagree. For a polar climate model,
  where a one-hour offset silently corrupts boundary conditions, this is real
  correctness work, not ceremony. The `utc()` wrapper then guarantees every downstream
  `date` call runs in UTC.
- **Path validation.** `check_paths` rejects empty paths, paths with spaces, and paths
  containing `@` (because `@` is used as a sed separator elsewhere). The reasoning is
  documented in the function.
- **Documented return codes** for every function, and a unit-test suite
  (`run/test_commons.bash`) that runs in CI.
- `get_git_root_dir` has a fallback implementation for machines where Git is missing or
  too old — defensive engineering for old HPC login nodes.

### 3.4 Reproducibility is a design goal, not an afterthought

- `compilation.write_options` writes a `compile.json` next to the installation,
  recording **every** compile option plus the exact commit hash resolved after checkout
  (`git rev-parse HEAD`). Re-running a compile from that file is therefore possible.
- Patches are versioned in-tree under `compile/patches/` with their own READMEs, and are
  applied by path-mirroring the target tree — so a patch for `phys/Makefile` lives at
  `patches/WRF/phys/Makefile.patch`. Simple and predictable.
- The jobscripts copy themselves (`cp "$0" "$OUTDIR/..."`) and the final namelists into
  the output directory, and `doc/wrfchem-repro-file-checklist.md` tells users exactly
  what to archive. This is exemplary practice for scientific software.
- `install_env.py` **refuses to overwrite an existing environment** (fail-fast instead of
  silent corruption) and reads its dependency list from `pyproject.toml` — one single
  source of truth for dependencies.

### 3.5 Continuous integration, style and licensing

- Ruff runs in CI for both lint and **format** (`--diff`), with a 79-column limit and
  import sorting. The `# noqa: UP011` in `generic.py` shows the rules are engaged with
  deliberately, not cargo-culted.
- The Bash commons have their own CI workflow — Bash unit tests in CI are rare even in
  professional projects.
- Every file carries a copyright and license header, and the `LICENSES/` directory
  contains the full texts (BSD-3-Clause, Apache-2.0, CC-BY-SA-3.0 for the ASCII art,
  which is properly credited to the original photographers). The `AUTHORS` file exists.
  This is more rigorous than most academic software.

### 3.6 Documentation

The tutorials in `doc/tutorials/` are task-oriented, show expected success output
(`SUCCESS COMPLETE WRF`, the geogrid completion banner), and explain *why* steps are
ordered as they are ("WPS must be installed **after** WRF"). `env/README.md` fully
documents the config-file schema. `run/simulation.conf` is self-documenting, as its own
header demands.

---

## 4. What needs updating

Findings are grouped by severity. "Confirmed" means the behaviour was verified by running
or inspecting the code during this review, not just suspected.

### 4.1 Bugs

| # | Finding | Location | Status |
|---|---|---|---|
| B1 | Two error checks build a message but never `raise` it | `data/concat-cams-emissions-files.py` ~line 129 and ~line 205 | Confirmed |
| B2 | `__all__` contains module objects instead of strings; `from wrfinfra import *` raises `TypeError` | `pymodules/wrfinfra/__init__.py` line 9 | Confirmed (reproduced) |
| B3 | Error message missing its `f` prefix, so it prints the literal text `{dir_data}` | `data/get-era5-data-from-copernicus.py` line 180 | Confirmed |
| B4 | README links to `./LICENSE`, which does not exist (the files live in `LICENSES/`) | `README.md` line 9 | Confirmed |
| B5 | Spatial-mapping cache is keyed only by domain number, so a grid change silently reuses a stale mapping | `run/real/cams2wrfchem.py` line 684 | Confirmed (hazard) |
| B6 | Example JSON in the compile README is invalid (trailing comma) and points to an outdated repository URL | `compile/README.md` lines 93 and 113–114 | Confirmed |
| B7 | Tutorial tells users to edit date variables (`yys`, `mms`, …) that no longer exist in the jobscripts | `doc/tutorials/03-run-wrf-chem-polar.md` line 25 | Confirmed |
| B8 | Test file imports `from namelist import ...` (top-level) while living inside a package, so test discovery depends on how/where pytest is launched | `pymodules/wrfinfra/test_namelist.py` line 8 | Confirmed |

**B1 — errors that are checked but not raised.** In `concat-cams-emissions-files.py`,
the code detects inconsistent dimensions between input files and helpfully prepares the
message `f"Inconsistent dimensions for variable {varname}."` — but then falls through
without raising it. The same pattern occurs for `msg = f"Unknown dimensions: ..."`.
The consequence is that malformed input files are *accepted* instead of rejected, which
for an emissions pre-processor means silently wrong science output. The fix is one word
per location:

```python
# If the dimensions of this variable do not match what we already wrote
# to the output file, stop immediately with a clear message.
if var_in.dimensions != var_out.dimensions:
    msg = f"Inconsistent dimensions for variable {varname}."
    raise ValueError(msg)  # <-- this line was missing
```

**B2 — `__all__` misuse.** `__init__.py` currently reads:

```python
from . import compilation, generic

__all__ = [generic, compilation]  # Wrong: these are modules, not names
```

`__all__` must be a list of *strings*. As written, `from wrfinfra import *` fails with
`TypeError: Item in wrfinfra.__all__ must be str, not module` (reproduced during this
review). The fix:

```python
# Names exported by "from wrfinfra import *".
# These are module names as strings, which is what __all__ requires.
__all__ = ["compilation", "generic"]
```

Note also that `namelist` is not exported from the package at all, even though the
jobscripts depend on it — see finding B8 and section 5.1.

**B5 — stale mapping cache (the most scientifically dangerous finding).**
`cams2wrfchem.py` caches its expensive spatial mapping to disk, which is a good idea —
but the cache filename is built from the **domain number only**:

```python
filepath = __file__[:-3] + "_mapping_d" + domain + ".json"
```

If a user runs a domain numbered `01` with one grid (e.g. 86 × 86 at 100 km), then later
runs a *different* grid also numbered `01` (e.g. 60 × 60 at 50 km), the script silently
loads the old mapping and reprojects emissions onto the wrong cells. No error, no
warning — just wrong numbers. Recommended fix: derive the cache name from the grid
geometry (or store the geometry inside the JSON and verify it on load):

```python
# Build a short, readable "fingerprint" of the grid so that a cached
# mapping is only reused when the grid is exactly the same. This prevents
# a stale mapping from being silently applied to a new domain geometry.
fingerprint = f"{x_wrf.shape[0]}x{x_wrf.shape[1]}_{int(dx_wrf)}m"
filepath = __file__[:-3] + "_mapping_d" + domain + "_" + fingerprint + ".json"
```

**B6 / B7 — documentation drift.** The JSON example in `compile/README.md` ends with a
trailing comma (making it invalid JSON for anyone who copies it into `--optfile`), and
its `repository` URL points to the old `Regional-Modeling-LATMOS-IGE` organisation while
`generic.py` now uses `WRF-Chem-Polar`. The run tutorial instructs users to edit `yys`,
`mms`, `dds`… in the jobscripts, but those variables were moved to
`run/simulation.conf` (`date_start` / `date_end`) some time ago — following the tutorial
as written is impossible. Tutorials are the front door of a repository; these should be
fixed first.

**B8 — fragile test imports.** `test_namelist.py` lives inside the `wrfinfra` package but
imports its subject as a top-level module (`from namelist import ...`). Because the
package has an `__init__.py`, pytest resolves the test as `wrfinfra.test_namelist`, and
the top-level import only succeeds when the working directory happens to be on
`sys.path` (e.g. when running `python -m pytest` from inside the package directory).
Running plain `pytest` from the repository root fails. The fix is to import through the
package, which also enables the missing CI job (section 5.7):

```python
# Import through the package so the tests work no matter where
# pytest is started from.
from wrfinfra.namelist import (
    Namelist,
    Value,
    _name_is_valid,
    _parse_key_values,
    _process_value,
)
```

### 4.2 Robustness and correctness risks

- **Silent sed placeholders.** The jobscripts inject dates and grid values into namelist
  templates with `sed -e "s/<start_year>/.../g"`. If a template is missing a placeholder
  (or a placeholder is misspelled), `sed` succeeds silently and the model later fails in
  a confusing way, far from the cause. The repository already contains the right tool
  for this job — `namelist.py` validates section and key names and raises clear errors.
  See section 5.5.
- **Unchecked subprocess calls in the WPS post-processing scripts.**
  `run/WPS/add_chloroa_wps.py` and `add_dmsocean_wps.py` call `subprocess.run([...])`
  about twenty times each **without `check=True`**, and use `os.system('mv ...')` for
  others. If `ncrename` or `cdo` fails (a very common failure mode on HPC nodes with
  mismatched module versions), the scripts march on and produce corrupt `met_em` files.
- **Comment/branch mismatch in `jobscript_wps.sh`.** Line 157 comments "ERA-interim
  input" directly above the `INPUT_DATA_SELECT==0` branch, which is ERA5. Small, but it
  is exactly the kind of comment that misleads during debugging. The neighbouring
  ERA-interim branch is itself acknowledged to be broken ("these lines will fail").
- **Integer division for spectral nudging.** Both `jobscript_real.sh` and
  `jobscript_wrfchem.sh` compute `xwavenum=$(( (wrf_dx * wrf_e_we) / nudging_scale ))`.
  For a small or coarse domain this can evaluate to `0`, which WRF may reject late in a
  run. A minimum-value check with a clear message would fail fast.
- **`ls` parsing for input discovery.** `jobscript_real.sh` finds the MOZART/FINN input
  files with `ls -1 ... | xargs -n 1 basename | tail -n1`. If nothing matches, `ls`
  writes to stderr and the pipeline yields an empty string; the script then reports
  "could not find mozbc file" without saying *what* it looked for or *where*.
- **Silent config failures in `commons.bash`.** `get_host_config_value` runs a generated
  Python one-liner with `2> /dev/null` and returns an empty string on *any* error — a
  typo in a section name becomes an invisible `eval ""` instead of a loud failure.
- **Variable shadowing.** `concat-cams-emissions-files.py` reuses the name `args`
  (`args, kwargs = [varname, dtype, ...], {}`) while `args` is also the parsed
  command-line namespace — luck, not design, prevents a crash today.
- **Known debt is at least tracked in place**: `megan_bio_emiss` is wrapped in
  `set +e` with the comment "Temporary until we fix the seg fault", and the `ncks`
  XLONG workaround is commented. Good practice would be to also reference a tracking
  issue so "temporary" has an owner.

### 4.3 Portability

- **The run scripts are Linux-only.** `date -d` (GNU date), `sed -i` without a suffix,
  and the NCO/CDO toolchain are assumed throughout. On macOS (BSD userland) every
  jobscript fails immediately. This is a legitimate choice for an HPC project, but it
  is nowhere stated; a one-line note in the README ("Linux required; on macOS use a
  Linux container") would save users an hour of confusion.
- **The import mechanism rests on Git symlinks, and is undocumented.** Scripts import
  `wrfinfra` because `compile/wrfinfra -> ../pymodules/wrfinfra` and
  `testing/wrfinfra -> ../pymodules/wrfinfra` exist as symlinks, and Python puts the
  script's own directory on `sys.path`. This is clever, but: it is invisible in normal
  file listings; it is not mentioned in any README or tutorial; it breaks on Windows
  checkouts where Git materialises symlinks as text files containing the path; and it
  explains an otherwise baffling `ModuleNotFoundError` if a user moves a script.
  Additionally, `jobscript_wrfchem.sh` reaches into the package with a relative path
  (`cp $submit_dir/../../pymodules/wrfinfra/namelist.py "$SCRATCH/"`) and then runs the
  module as a standalone script. Making the package properly installable (section 5.1)
  removes all of this at once.
- **Hardcoded machine paths outside the config system.** The `env/` abstraction is
  good, but several scripts bypass it: `jobscript_real.sh` line 43 prepends
  `/proju/wrf-chem/software/wrf-installs/WRF-Chem-Preprocessing-Tools/bin` to `PATH`
  directly; `add_chloroa_wps.py`, `add_dmsocean_wps.py` and
  `hldust_regrid_wrfinput_erod.py` hardcode `/proju/wrf-chem/input-data/...`; the
  default `--dir-em-in` of `cams2wrfchem.py` does the same. On any machine other than
  Spirit, these scripts fail even though the project otherwise supports four machines.

### 4.4 Packaging and dependency management

- **`pyproject.toml` cannot be installed.** It declares `requires-python` and optional
  dependencies, but has no `[build-system]`, no `name`, no `version`, and no package
  discovery configuration (the package lives in the non-standard `pymodules/` directory).
  `pip install .` does nothing useful, which is the root cause of the symlink trick
  above and of the "copy `namelist.py` into the scratch directory" pattern.
- **The `dev` extra installs "emacs" and "vim" from PyPI.** The comment explains the
  intent ("auto format with ruff on save"), but the PyPI packages with those names are
  not the editors, so the mechanism cannot deliver the intent and can only cause
  confusion. Editor configuration is better placed in a documented editor setup file
  (e.g. `.dir-locals.el` or `.vimrc` examples in `doc/`).
- **`wrfpp` is installed unpinned** (`wrfpp[all]@git+https://github.com/...wrfpp.git`,
  in `install_env.py`), so two environments created a month apart may contain different
  code. The same is true of conda dependencies, which are resolved at creation time with
  no lock file. For a project that clearly values reproducibility, pinning (or at least
  recording) these versions is an easy win.
- **Dead version check.** `namelist.py` refuses Python < 3.7 at import time, while
  `pyproject.toml` requires ≥ 3.13. The check is unreachable and can be removed.

### 4.5 Documentation gaps (beyond the drift in 4.1)

- `doc/tutorials/02-download-external-input-data.md` is an honest placeholder — it lists
  the required data categories but the download instructions are "under construction",
  even though three download scripts already exist in `data/` and are documented in
  `data/README.md`. Cross-linking what exists would already help.
- Typos in the tutorials: "recommand" and "make you environment is clean"
  (`01-install-wrf-chem-polar.md`), "autmatically" in `jobscript_real.sh` comments.
- `compile/README.md` still documents WPS patches as applied by default, but commit
  `a808c92e` removed that behaviour; the README has not caught up.

### 4.6 Continuous integration gaps

- **The pytest suite never runs in CI.** `test_namelist.py` is the most valuable test
  asset in the repository (243 lines, covering the trickiest parsing logic) and there is
  no workflow that executes it. Only Ruff and the Bash commons tests run.
- Ruff only triggers on pull requests, so direct pushes to `main` are not linted.
- There is no `shellcheck` job for the ~800 lines of Bash in `run/` and `testing/`,
  despite Bash being where most user-facing failures will occur.
- The compile scripts have an excellent `--dry yes` mode that stops right before
  submitting the compile job — a perfect, cheap smoke test for CI that is currently
  unused.

---

## 5. How to make this more automated for users

The through-line of this section: **most of the automation already exists as building
blocks inside the repository** — a validated namelist tool, a dry-run mode, a
scheduler abstraction, a test-case orchestrator that already chains Slurm jobs. The
recommendations below are largely about *connecting* those blocks.

### 5.1 Make `wrfinfra` a real installable package (unlocks everything else)

This is the single highest-leverage change. With a proper package, the symlink trick,
the `PYTHONPATH` fragility, the `cp ../../pymodules/wrfinfra/namelist.py` hack and the
broken `import *` all disappear, and every later recommendation gets easier.

```toml
# pyproject.toml (additions, in plain words):
#  - [build-system] tells pip which tool builds the package.
#  - [project] gives the package a name and a version, so it can be
#    installed and cited.
#  - [tool.setuptools.packages.find] tells setuptools that the code
#    lives in the "pymodules" folder instead of the usual "src".
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "wrfinfra"
version = "0.1.0"

[tool.setuptools.packages.find]
where = ["pymodules"]
```

Then one line installs it into the environment that `install_env.py` already creates:

```python
# In install_env.py, after the conda environment is created, install the
# WRF-infra Python library into it so that "from wrfinfra import ..." works
# for every script, everywhere, with no symlinks or PYTHONPATH tricks.
cmd = [
    os.path.expanduser(args.conda),
    "run",
    "--root-prefix", args.env_root_prefix,
    "--name", args.env_name,
    "python", "-m", "pip", "install",
    # "-e" installs from the local repository in editable mode, so the
    # scripts always reflect the checked-out revision of WRF-infra.
    "-e", generic.path_of_repo(),
]
generic.run(cmd)
```

### 5.2 One entry point instead of eleven scripts

Users currently need to know *which* script in *which* directory to run, in which order.
A single command with subcommands hides all of that:

```text
wrfinfra compile WRF --destination ~/WRF        # wraps compile/compile_WRF.py
wrfinfra compile WPS --wrfdir ~/WRF            # wraps compile/compile_WPS.py
wrfinfra check                                 # preflight, see 5.3
wrfinfra run                                   # submits the full chain, see 5.6
wrfinfra download --from run/simulation.conf   # fetches all input data, see 5.9
wrfinfra plot --wrfouts ...                    # wraps testing/plot-*.py
```

Each subcommand is a thin wrapper around code that already exists — this is a
repackaging, not a rewrite. `argparse` subparsers (or a tiny Typer/Click front end)
are enough; no framework required.

### 5.3 Preflight checks: fail before the queue, not inside it

The jobscripts fail *inside* scheduled jobs, where the turnaround cost is hours. A
`wrfinfra check` command could run on the login node in seconds and verify:

- every path in `simulation.conf` exists and is readable;
- every expected input file for the requested dates is present (met_em, mozbc, FINN,
  wrfchemi prerequisites, MEGAN, erodibility, photolysis tables);
- the namelists are mutually consistent (`namelist.wps` vs `namelist.input`: same
  `e_we`, `e_sn`, `dx`, `dy` — the tutorial warns about this by hand today);
- the host is known and its config file parses.

The repository already contains every ingredient for this: `check_paths`,
`check_period`, and the `Namelist` reader. It is a matter of composition.

### 5.4 Move the last hardcoded knobs into the configuration

The config system is well designed but incomplete. These values currently require
*editing scripts* instead of editing configuration:

| Value | Currently hardcoded in | Belongs in |
|---|---|---|
| `INPUT_DATA_SELECT` (ERA5 / ERA-I / FNL) | `jobscript_wps.sh` line 38 | `simulation.conf` (the script's own comment agrees: "will eventually be moved") |
| `USE_CHLA_DMS_WPS` | `jobscript_wps.sh` line 43 | `simulation.conf` |
| `nudging_scale` | `jobscript_real.sh` + `jobscript_wrfchem.sh` (duplicated) | `simulation.conf` (once, not twice) |
| Preprocessing-tools `PATH` | `jobscript_real.sh` line 43 | `env/<host>.config` under `run.*` |
| Chlorophyll / DMS / erodibility data paths | `add_chloroa_wps.py`, `add_dmsocean_wps.py`, `hldust_regrid_wrfinput_erod.py` | `simulation.conf` (they already receive `dir_shared_data`'s siblings) |
| SBATCH resource requests | headers of all three jobscripts | `env/<host>.config`, which already has `job-header-option-*` support |

### 5.5 Replace sed placeholders with the namelist tool (kill silent failures)

The jobscripts already copy `namelist.py` into the scratch directory and use it to *read*
values — then use raw `sed` to *write* others. Using the same tool for writes makes
failures loud and immediate:

```bash
# Instead of:
#   sed -i -e "s/<start_year>/2026/g" -e "s/<start_month>/03/g" ... namelist.input
# which silently succeeds even if the template has no <start_year> placeholder,
# set the values through the validated namelist tool. If the section or key
# name is wrong, the tool fails immediately with a precise message.
year=$(utc -d "${date_start}" +%Y)
month=$(utc -d "${date_start}" +%m)
${cmd_python} -u namelist.py --namelist namelist.input \
              --update "time_control/start_year=${year}, ${year}, ${year}" \
              --update "time_control/start_month=${month}, ${month}, ${month}"
```

(The exact multi-value syntax should follow what `namelist.py` supports; the point is
that the write path becomes validated rather than best-effort.)

### 5.6 Submit the whole chain as one command

Today the user runs `sbatch` three times, in three directories, checking three logs
between stages. `testing/test-case-multi-wrf.py` already demonstrates the missing
piece — it chains jobs with `sbatch -d afterok:<id>`. Generalising that pattern into
`wrfinfra run` gives users a single command:

```text
wrfinfra run
  └─ submits WPS job
     └─ afterok → submits real job
        └─ afterok → submits WRF-Chem job
           └─ afterok → optional: runs result verification (see 5.3) and
              greps the log for "SUCCESS COMPLETE WRF", failing the job
              if the success line is absent.
```

Success verification deserves emphasis: the tutorials currently ask users to eyeball
logs for success banners. A five-line grep at the end of each jobscript turns "hope it
worked" into "the scheduler tells you it worked".

### 5.7 Close the CI gaps

Concretely, three additions to `.github/workflows/`, all cheap:

1. **Run the pytest suite** — `pip install pytest` then `pytest pymodules` (after the
   B8 import fix and the 5.1 packaging fix, this becomes trivial).
2. **Run `shellcheck`** on `run/*.sh`, `run/*.bash`, `testing/*.bash` with the existing
   `continue-on-error: true` at first, to surface the highest-confidence warnings
   without breaking the team's flow.
3. **Smoke-test the compile scripts** with their own `--dry yes` mode on
   `ubuntu-latest`; it exercises host detection, argument parsing, clone, patch
   discovery and script generation without needing a scheduler.

Also consider triggering Ruff on pushes to `main`, not only on pull requests.

### 5.8 A container for portability (and for macOS/Windows users)

All run-time dependencies (GNU coreutils, NCO, CDO, Python environment) are conda-able
already — `install_env.py` proves it. Publishing a Dockerfile (and/or an Apptainer/
Singularity definition file, which HPC centres prefer) would give users on unsupported
machines a working environment in one command, and would remove the "Linux-only"
surprise from section 4.3.

### 5.9 One command for input data, with a manifest

`data/` already automates ERA5 and chlorophyll downloads. What is missing is an
orchestrator that reads `simulation.conf` and fetches *everything* the configured
period and domain needs, plus a **manifest**: a small file listing each required
dataset, its expected files and a checksum. The manifest then doubles as the
data-integrity check for `wrfinfra check` (5.3) — a job that fails because a FINN file
is truncated should say so *before* `fire_emis` crashes at 2 a.m.

### 5.10 Pin the moving parts

- Pin the `wrfpp` install in `install_env.py` to a tag or commit hash.
- Export a conda lock file (e.g. `conda env export` or `conda-lock`) alongside
  `pyproject.toml`, and have `install_env.py` optionally install from the lock.
- The date-stamped environment names (`WRF-Chem-Polar_YYYY-MM-DD`) are a good start;
  recording the WRF-infra commit inside the environment directory would complete the
  provenance chain.

### 5.11 Make adding a new machine self-service

`identify_host_platform` currently raises `NotImplementedError` for unknown hosts,
which is correct but unhelpful. Two small improvements:

```python
# When the host is unknown, tell the user exactly what to do next,
# instead of just refusing. This turns a dead end into a 5-minute task.
msg = (
    f"Unknown host platform: {nodename}.\n"
    "To support this machine, add a line to the 'env/hosts' file:\n"
    "    <hostname-pattern>    <short-name>\n"
    "and create the file env/<short-name>.config "
    "(see env/README.md for the expected format)."
)
raise NotImplementedError(msg)
```

…plus a `wrfinfra add-host` subcommand that generates a config skeleton from a template.
Note also that `compile_*.py` scripts call `identify_host_platform()` *before* argument
parsing, so even `--help` fails on an unknown machine — parsing arguments first would
make the tools at least self-documenting everywhere.

### 5.12 A bigger, optional step: a workflow engine

If the project continues to grow stages (data download → WPS → real → WRF → plots,
with restarts and reruns), a workflow engine such as Snakemake would provide, for free:
resumption after partial failure, automatic re-run on configuration change, per-stage
logs, and provenance records. The current scripts map naturally onto rules. This is a
larger cultural change and should only follow the smaller steps above — but it is the
natural end-state of the automation path this repository is already on.

---

## 6. Suggested priority order

| Priority | Item | Effort | Impact |
|---|---|---|---|
| 1 | Fix B1–B8 (bugs and doc drift) | Small | Immediate; prevents wrong science output (B1, B5) |
| 2 | Make `wrfinfra` installable; drop symlinks and file-copying (5.1) | Small–medium | Removes a whole class of setup failures |
| 3 | Run pytest + shellcheck + dry-run smoke in CI (5.7) | Small | Keeps 1 and 2 from regressing |
| 4 | Preflight checks + success verification (5.3, 5.6) | Medium | Turns hours of queue-waiting into seconds of clear errors |
| 5 | Finish the config system: move hardcoded knobs (5.4) and switch writes to the namelist tool (5.5) | Medium | Makes new machines and new experiments config-only |
| 6 | Single CLI entry point (5.2) and one-command chain submission (5.6) | Medium | The "user types one command" experience |
| 7 | Data manifest + download orchestrator (5.9); pin dependencies (5.10) | Medium | Reproducibility from data to results |
| 8 | Container images (5.8); host onboarding (5.11) | Medium | Broadens the user base beyond Spirit/Jean Zay |
| 9 | Consider a workflow engine (5.12) | Large | Only after 1–6; compounding returns |

---

## 7. Closing remarks

This repository is in a good place: the difficult, invisible engineering decisions —
timezone correctness, host abstraction, reproducible compilation — have already been
made and made well. The gap that remains is mostly one of *consistency and connection*:
bringing the research scripts up to the standard of the core library, making the
package formally installable, and wiring the existing pieces into a single automated
path from "clone the repository" to "here is your plot". None of the findings above
question the scientific design; they are all about making a solid design harder to
misuse and easier to adopt.
