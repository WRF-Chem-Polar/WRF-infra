# Input data download et pre-processing

This directory contains scripts to download and pre-process input data for our WRF-Chem-Polar runs.

## ERA5 meteorological hourly data

Prerequisites:

 - Create an account on the [Copernicus climate data store (CDS)](https://cds.climate.copernicus.eu/).
 - Set your CDS API credentials in the file `~/.cdsapirc` following [these instructions](https://cds.climate.copernicus.eu/how-to-api).
 - Install the `csdapi` Python package from [PyPi](https://pypi.org/) with `pip` or from [conda-forge](https://conda-forge.org/) with `conda`.

We use ERA5 meteorological hourly data for initial and boundary conditions for our WRF-Chem-Polar runs. We download two types of hourly meteorological data:

 - data on pressure levels.
 - single-level data (eg. 2-m temperature).

These are downloaded from the Copernicus climate data store by the same script. The only two mandatory parameters are the first and last days of the period of interest, for example for the month of January 2015:

```sh
python get-era5-data-from-copernicus.py --start-date=2015-01-01 --end-date=2015-01-31
```

By default, the script downloads data for the entire globe. Use `--box` to select a specific region, for example for the southern hemisphere:

```sh
python get-era5-data-from-copernicus.py ... --box -180 180 -90 0
```

For more documentation and a list of all available options:


```sh
python get-era5-data-from-copernicus.py --help
```

## Oceanic surface-level concentration of chlorophyll

Prerequisites:

 - Create an account on the [Copernicus Marine service website](https://marine.copernicus.eu/).
 - Install the `copernicusmarine` Python package from [PyPi](https://pypi.org/) with `pip` or from [conda-forge](https://conda-forge.org/) with `conda`.

We use these data in the WPS step to add oceanic surface-level concentrations of chlorophyll to the met_em* files (this step is optional).

These data are downloaded from the Copernicus Marine service. Only one parameter is required: the year of interest (the script downloads one year of data at a time). For example, to download data for the year 2015:

```sh
python get-chlorophyll-data-from-copernicus-marine.py --year=2015
```

For more documentation and a list of all available options:

```sh
python get-chlorophyll-data-from-copernicus-marine.py --help
```
