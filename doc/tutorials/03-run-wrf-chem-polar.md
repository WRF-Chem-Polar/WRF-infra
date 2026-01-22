# How to run the model

This tutorial explains the steps to run an example simulation of WRF-Chem-Polar using the scripts in this repository. It is assumed that users are working on Spirit, where all the input data to run the default test case have already been downloaded. Users can use their own WRF-Chem-Polar+WPS installation or use the shared installation that is readily available on Spirit.

## Clone this repository

```
git clone git@github.com:WRF-Chem-Polar/WRF-infra.git
cd WRF-infra
```

## (optional) Edit the casename, domain, simulation dates, and namelist options

The default test case is a one-week simulation over a single 86 x 86 Arctic domain with 100 km grid resolution. You can change these settings in the following ways, noting that if you change the simulation dates you will need to ensure that you still have all the external input data required. Note also that changing the namelist settings can be somewhat complicated because all options need to be mutually compatible. Of course, the list of examples of options to change here is non-exhaustive. Finally, be aware that if you increase the domain size or simulation length, you may need to adjust the requested compute time or memory at the top of the jobscripts.

- PATHS TO WHERE WRF and WPS are installed: `dir_wrf` and `dir_wps` in `run/simulation.conf` (by default they point to shared installations that should work "as is").
- PATHS TO WHERE OUTPUTS WILL BE STORED: `dir_outputs` in `run/simulation.conf`.
- DATES: change `yys`, `mms`, `dds`, `hhs`, `yye`, `mme`, `dde`, and `hhe` in each of `run/WPS/jobscript_wps.sh`, `run/real/jobscript_real.sh` and `run/WRF-Chem/jobscript_wrfchem.sh`, ensuring that the dates are consistent for WPS, real and WRF.
- NUMBER OF GRID BOXES: in `run/WPS/namelist.wps.YYYY` and `run/real/namelist.input.YYYY`, `e_we` controls the number of grid boxes in the west-east direction and `e_sn` for the south-north direction. Be sure that the two namelist files are consistent.
- HORIZONTAL RESOLUTION: in `run/WPS/namelist.wps.YYYY` and `run/real/namelist.input.YYYY`, `dx` and `dy` control the horizontal resolution in units of metres - again, both files need to have the same values.
- DOMAIN LOCATION: if using `projection=polar` in `run/WPS/namelist.wps.YYYY`, `ref_lat` and `ref_lon` control the co-ordinates of the centre of the domain.

## Run WPS

From the root of WRF-infra:

```
cd run/WPS/
sbatch jobscript_wps.sh
```

Once your job has completed, check your slurm output log file (`run/WPS/slurm_<job ID>.out`) to see if the job was successful. You should see text like this:

```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!  Successful completion of geogrid.        !
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

for geogrid, ungrib and metgrid if it was successful. You can also check the output directory, where you should now be able to find `met_em` files for the dates of your simulation.

## Run real

From the root of WRF-infra:

```
cd run/real/
sbatch jobscript_real.sh
```

Once the job has completed, view the slurm log file. The expected output is somewhat case dependent, but for the example in this repo, there should be output related to the following, without error messages:
- real.exe
- megan_bio_emiss (creates biogenic emissions)
- real.exe (2nd time)
- mozbc (creates aerosol boundary conditions)
- wesely and exo_coldens
- fire_emiss (creates fire emissions)
- emissions script (for pre-processing anthropogenic emission data)
- initialising snow on sea ice
- transferring the output data of real

Also, if your job completed successfully, you should now have these sets of files in the output directory for real:
- `exo_coldens`
- `wrfbdy`
- `wrfbiochemi`
- `wrfchemi`
- `wrffdda`
- `wrffirechemi`
- `wrfinput`
- `wrflowinp`
- `wrf_season_wes_usgs_d01`

## Run WRF-Chem

From the root of WRF-infra:

```
cd run/WRF-Chem/
sbatch jobscript_wrfchem.sh
```

If the job is successful, you should have this line near the end of the output log file:

```
d01 2012-03-08_00:00:00 wrf: SUCCESS COMPLETE WRF
```

where the date corresponds to the final time step of the simulation. You should also have `wrfout` and `wrfrst` files in your WRF-Chem output directory. If so, congratulations! You just ran WRF-Chem-Polar.

## What now?

### Save your scripts

Along with the model version you've run, your namelists and jobscripts contain everything needed to reproduce your simulation by others, or by you in the future. Use [this checklist](../wrfchem-repro-file-checklist.md) to check you've saved everything you need.

### Do science

The `wrfout` files containing the model output are [netCDF](https://www.unidata.ucar.edu/software/netcdf/) format. Commons tools to visualise and manipulate netCDF data are [NCO](https://github.com/nco/nco), [CDO](https://code.mpimet.mpg.de/projects/cdo/wiki), and the python package [xarray](https://docs.xarray.dev/en/stable/index.html).

More detailed tools and tutorials to examine WRF-Chem-Polar output will be added to this repository in the future. 

