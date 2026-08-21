# Copyright (c) 2026 LATMOS (France, UMR 8190) and IGE (France, UMR 5001).
#
# License: BSD 3-clause "new" or "revised" license (BSD-3-Clause).

"""Contains functions for WRF data analysis steps required in the HLdust pre-processing workflow

References:
 - The WPS code can be found at:
   https://github.com/wrf-model/WPS
   (More persistent link: https://archive.softwareheritage.org/swh:1:dir:ef689d58a7182286302a369f8f41908ffe609910)

"""

from netCDF4 import Dataset
import numpy as np
import math


class WRFProjection:
    def __init__(
        self,
        map_proj,
        imax,
        jmax,
        kmax,
        dx,
        dy,
        moad_cen_lat,
        truelat1,
        truelat2,
        stdlon,
        ref_lat,
        ref_lon,
        ref_i,
        ref_j,
        pole_lat,
        pole_lon,
        hemi,
        mminlu,
        eta_u,
        p_top,
    ):
        self.map_proj = map_proj
        self.imax = imax
        self.jmax = jmax
        self.kmax = kmax
        self.dx = dx
        self.dy = dy
        self.moad_cen_lat = moad_cen_lat
        self.truelat1 = truelat1
        self.truelat2 = truelat2
        self.stdlon = stdlon
        self.ref_lat = ref_lat
        self.ref_lon = ref_lon
        self.ref_i = ref_i
        self.ref_j = ref_j
        self.pole_lat = pole_lat
        self.pole_lon = pole_lon
        self.hemi = hemi
        self.mminlu = mminlu
        self.eta_u = eta_u
        self.p_top = p_top


def get_wrf_proj(wrf_filename):
    """Return WRF grid projection info for a given WRF file.

    Parameters
    ----------
    wrf_filename: str
        Name of WRF output file to read projection from

    """

    # Open NetCDF and get WRF projection attribute values
    with Dataset(wrf_filename) as ncfile:
        map_proj = ncfile.MAP_PROJ
        imax = getattr(ncfile, "WEST-EAST_GRID_DIMENSION") - 1
        jmax = getattr(ncfile, "SOUTH-NORTH_GRID_DIMENSION") - 1
        kmax = getattr(ncfile, "BOTTOM-TOP_GRID_DIMENSION") - 1
        dx = ncfile.DX / 1000
        dy = ncfile.DY / 1000
        moad_cen_lat = ncfile.MOAD_CEN_LAT
        truelat1 = ncfile.TRUELAT1
        truelat2 = ncfile.TRUELAT2
        stdlon = ncfile.STAND_LON
        ref_lat = ncfile.CEN_LAT
        ref_lon = ncfile.CEN_LON
        pole_lat = ncfile.POLE_LAT
        pole_lon = ncfile.POLE_LON
        mminlu = ncfile.MMINLU
        try:
            var = ncfile.variables["ZNU"]
        except KeyError:
            eta_u = ""
            print("Warning: get_wrf_proj: could not find ZNU")
        else:
            eta_u = var[0].data.tolist()
        try:
            var = ncfile.variables["P_TOP"]
        except KeyError:
            p_top = ""
            print("Warning: get_wrf_proj: could not find P_TOP")
        else:
            p_top = var[0]
    ref_i = float((imax + 1.0) / 2.0)
    ref_j = float((jmax + 1.0) / 2.0)
    hemi = 1 if truelat1 > 0 else -1
    # Create WRFProjection instance wrf_proj
    wrf_proj = WRFProjection(
        map_proj,
        imax,
        jmax,
        kmax,
        dx,
        dy,
        moad_cen_lat,
        truelat1,
        truelat2,
        stdlon,
        ref_lat,
        ref_lon,
        ref_i,
        ref_j,
        pole_lat,
        pole_lon,
        hemi,
        mminlu,
        eta_u,
        p_top,
    )
    # Return wrf_proj
    return wrf_proj


# -----------------------------------------------------------------------------


def wrf_llij(lat, lon, wrf_proj):
    """Convert lat and lon into i and j indices for a WRF grid.

    Parameters
    ----------
    lat, lon: scalars
        The values of latitude and longitude
    wrf_proj: WRFProjection instance
        The projection of the WRF grid

    """

    wrfi = []
    wrfj = []
    rad_per_deg = math.pi / 180.0
    # Earth radius in kilometers divided by dx
    rebydx = 6370.0 / wrf_proj.dx

    # Convert lists to numpy arrays
    lat = np.asarray(lat)
    lon = np.asarray(lon)

    if wrf_proj.map_proj == 1:
        # -------- Lambert conformal projection --------
        # Subroutines set_lc, lc_cone and llij_lc from WPS: geogrid/src/module_map_utils.f90

        # Copied from subroutine lc_cone in geogrid/src/module_map_utils.f90:

        # First, see if this is a secant or tangent projection.  For tangent
        # projections, wrf_proj.truelat1 = wrf_proj.truelat2 and the cone is tangent to the
        # Earth's surface at this latitude.  For secant projections, the cone
        # intersects the Earth's surface at each of the distinctly different
        # latitudes
        if np.abs(wrf_proj.truelat1 - wrf_proj.truelat2) > 0.1:
            cone = np.log10(
                np.cos(wrf_proj.truelat1 * rad_per_deg)
            ) - np.log10(np.cos(wrf_proj.truelat2 * rad_per_deg))
            cone = cone / (
                np.log10(
                    np.tan(
                        (45.0 - np.abs(wrf_proj.truelat1) / 2.0) * rad_per_deg
                    )
                )
                - np.log10(
                    np.tan(
                        (45.0 - np.abs(wrf_proj.truelat2) / 2.0) * rad_per_deg
                    )
                )
            )
        else:
            cone = np.sin(np.abs(wrf_proj.truelat1) * rad_per_deg)

        # ---- Initialize the remaining items in the proj structure for a
        # ---- lambert conformal grid.

        # Copied from subroutine set_lc in geogrid/src/module_map_utils.f90:

        # Compute longitude differences and ensure we stay out of the
        # forbidden "cut zone"
        deltalon1 = wrf_proj.ref_lon - wrf_proj.stdlon
        if deltalon1 > +180.0:
            deltalon1 = deltalon1 - 360.0
        if deltalon1 < -180.0:
            deltalon1 = deltalon1 + 360.0

        # Convert wrf_proj.truelat1 to radian and compute COS for later use
        tl1r = wrf_proj.truelat1 * rad_per_deg
        ctl1r = np.cos(tl1r)

        # Compute the radius to our known lower-left (sw) corner
        rsw = (
            rebydx
            * ctl1r
            / cone
            * (
                np.tan(
                    (90.0 * wrf_proj.hemi - wrf_proj.ref_lat)
                    * rad_per_deg
                    / 2.0
                )
                / np.tan(
                    (90.0 * wrf_proj.hemi - wrf_proj.truelat1)
                    * rad_per_deg
                    / 2.0
                )
            )
            ** cone
        )

        # Find pole point
        arg = cone * (deltalon1 * rad_per_deg)
        polei = wrf_proj.hemi * wrf_proj.ref_i - wrf_proj.hemi * rsw * np.sin(
            arg
        )
        polej = wrf_proj.hemi * wrf_proj.ref_j + rsw * np.cos(arg)

        # Copied from subroutine llij_lc in geogrid/src/module_map_utils.f90:

        # ---- Compute deltalon between known longitude and standard lon and ensure
        # it is not in the cut zone
        deltalon = np.asarray(lon - wrf_proj.stdlon)
        if np.any(deltalon > 180.0):
            deltalon[deltalon > 180.0] = deltalon[deltalon > 180.0] - 360.0
        if np.any(deltalon < -180.0):
            deltalon[deltalon < -180.0] = deltalon[deltalon < -180.0] + 360.0

        # Convert wrf_proj.truelat1 to radian and compute COS for later use
        tl1r = wrf_proj.truelat1 * rad_per_deg
        ctl1r = np.cos(tl1r)

        # Radius to desired point
        rm = (
            rebydx
            * ctl1r
            / cone
            * (
                np.tan((90.0 * wrf_proj.hemi - lat) * rad_per_deg / 2.0)
                / np.tan(
                    (90.0 * wrf_proj.hemi - wrf_proj.truelat1)
                    * rad_per_deg
                    / 2.0
                )
            )
            ** cone
        )

        arg = cone * (deltalon * rad_per_deg)
        wrfi = polei + wrf_proj.hemi * rm * np.sin(arg)
        wrfj = polej - rm * np.cos(arg)

        # Finally, if we are in the southern hemisphere, flip the i/j
        # values to a coordinate system where (1,1) is the SW corner
        # (what we assume) which is different than the original NCEP
        # algorithms which used the NE corner as the origin in the
        # southern hemisphere (left-hand vs. right-hand coordinate?)
        wrfi = wrf_proj.hemi * wrfi
        wrfj = wrf_proj.hemi * wrfj

    elif wrf_proj.map_proj == 2:
        # -------- Polar stereographic projection --------
        # Subroutines set_ps and llij_ps from WPS: geogrid/src/module_map_utils.f90

        # Copied from subroutine set_ps in geogrid/src/module_map_utils.f90:

        # Compute the reference longitude by rotating 90 degrees to the east
        # to find the longitude line parallel to the positive x-axis.
        reflon = wrf_proj.stdlon + 90.0
        # Compute numerator term of map scale factor
        scale_top = 1.0 + wrf_proj.hemi * np.sin(
            wrf_proj.truelat1 * rad_per_deg
        )
        # Compute radius to lower-left (SW) corner
        ala1 = wrf_proj.ref_lat * rad_per_deg
        rsw = (
            rebydx
            * np.cos(ala1)
            * scale_top
            / (1.0 + wrf_proj.hemi * np.sin(ala1))
        )
        # Find the pole point
        alo1 = (wrf_proj.ref_lon - reflon) * rad_per_deg
        polei = wrf_proj.ref_i - rsw * np.cos(alo1)
        polej = wrf_proj.ref_j - wrf_proj.hemi * rsw * np.sin(alo1)

        # Copied from subroutine llij_ps in geogrid/src/module_map_utils.f90:

        # Find radius to desired point
        ala = lat * rad_per_deg
        rm = (
            rebydx
            * np.cos(ala)
            * scale_top
            / (1.0 + wrf_proj.hemi * np.sin(ala))
        )
        alo = (lon - reflon) * rad_per_deg
        wrfi = polei + rm * np.cos(alo)
        wrfj = polej + wrf_proj.hemi * rm * np.sin(alo)

    else:
        raise ValueError(
            "wrf_proj.map_proj={} invalid".format(wrf_proj.map_proj)
        )

    return wrfi, wrfj


# -----------------------------------------------------------------------------


def wrf_ijll(wrfi, wrfj, wrf_proj):
    """Convert i and j indices for a WRF grid into lat and lon

    Parameters
    ----------
    wrfi, wrfj: scalars
        The indices to extract
    wrf_proj: WRFProjection instance
        The projection of the WRF grid

    """

    if np.shape(wrfi) != np.shape(wrfj):
        msg = "Shapes of input arrays wrfi and wrfj mismatch."
        raise ValueError(msg)

    # Convert lists to numpy arrays
    wrfi = np.array(wrfi)
    wrfj = np.array(wrfj)
    wrflat = np.full(np.shape(wrfi), np.nan)
    wrflon = np.full(np.shape(wrfj), np.nan)

    # Earth radius in kilometers divided by dx
    rebydx = 6370.0 / wrf_proj.dx
    deg_per_rad = 180.0 / math.pi
    rad_per_deg = math.pi / 180.0

    # To know what each map_proj corresponds to, check in WPS code
    # geogrid/src/misc_definitions_module.f90
    if wrf_proj.map_proj == 1:
        # -------- Lambert conformal projection --------
        # Subroutines from WPS: geogrid/src/module_map_utils.f90

        # ---- Compute the cone factor of a Lambert Conformal projection
        # Copied from subroutine lc_cone in geogrid/src/module_map_utils.f90:

        # First, see if this is a secant or tangent projection.  For tangent
        # projections, wrf_proj.truelat1 = wrf_proj.truelat2 and the cone is tangent to the
        # Earth's surface at this latitude.  For secant projections, the cone
        # intersects the Earth's surface at each of the distinctly different
        # latitudes
        if np.abs(wrf_proj.truelat1 - wrf_proj.truelat2) > 0.1:
            cone = np.log10(
                np.cos(wrf_proj.truelat1 * rad_per_deg)
            ) - np.log10(np.cos(wrf_proj.truelat2 * rad_per_deg))
            cone = cone / (
                np.log10(
                    np.tan(
                        (45.0 - np.abs(wrf_proj.truelat1) / 2.0) * rad_per_deg
                    )
                )
                - np.log10(
                    np.tan(
                        (45.0 - np.abs(wrf_proj.truelat2) / 2.0) * rad_per_deg
                    )
                )
            )
        else:
            cone = np.sin(np.abs(wrf_proj.truelat1) * rad_per_deg)

        # ---- Initialize the remaining items in the proj structure for a
        # lambert conformal grid
        # Copied from subroutine set_lc in geogrid/src/module_map_utils.f90:

        # Compute longitude differences and ensure we stay out of the
        # forbidden "cut zone"
        deltalon1 = wrf_proj.ref_lon - wrf_proj.stdlon
        if deltalon1 > +180.0:
            deltalon1 = deltalon1 - 360.0
        if deltalon1 < -180.0:
            deltalon1 = deltalon1 + 360.0

        # Convert wrf_proj.truelat1 to radian and compute COS for later use
        tl1r = wrf_proj.truelat1 * rad_per_deg
        ctl1r = np.cos(tl1r)

        # Compute the radius to our known lower-left (sw) corner
        rsw = (
            rebydx
            * ctl1r
            / cone
            * (
                np.tan(
                    (90.0 * wrf_proj.hemi - wrf_proj.ref_lat)
                    * rad_per_deg
                    / 2.0
                )
                / (
                    np.tan(
                        (90.0 * wrf_proj.hemi - wrf_proj.truelat1)
                        * rad_per_deg
                        / 2.0
                    )
                )
            )
            ** cone
        )

        # Find pole point
        arg = cone * (deltalon1 * rad_per_deg)
        polei = wrf_proj.hemi * wrf_proj.ref_i - wrf_proj.hemi * rsw * np.sin(
            arg
        )
        polej = wrf_proj.hemi * wrf_proj.ref_j + rsw * np.cos(arg)

        # ---- Begin Lambert Code
        # Copied from subroutine ijll_lc in geogrid/src/module_map_utils.f90:
        chi1 = (90.0 - wrf_proj.hemi * wrf_proj.truelat1) * rad_per_deg
        chi2 = (90.0 - wrf_proj.hemi * wrf_proj.truelat2) * rad_per_deg

        # See if we are in the southern hemispere and flip the indices if we are.
        inew = wrf_proj.hemi * wrfi
        jnew = wrf_proj.hemi * wrfj

        # Compute radius**2 to i/j location
        xx = inew - polei
        yy = polej - jnew
        r2 = xx * xx + yy * yy
        r = np.sqrt(r2) / rebydx

        # Convert to lat/lon
        wrflat[r2 == 0.0] = wrf_proj.hemi * 90.0
        wrflon[r2 == 0.0] = wrf_proj.stdlon

        wrflon[r2 != 0.0] = (
            wrf_proj.stdlon
            + deg_per_rad
            * np.arctan2(wrf_proj.hemi * xx[r2 != 0.0], yy[r2 != 0.0])
            / cone
        )
        wrflon[r2 != 0.0] = np.mod(wrflon[r2 != 0.0] + 360.0, 360.0)

        chi = np.empty((np.shape(wrfi)))
        chi[:] = np.nan
        if chi1 == chi2:
            chi[r2 != 0.0] = 2.0 * np.arctan(
                (r[r2 != 0.0] / np.tan(chi1)) ** (1.0 / cone)
                * np.tan(chi1 * 0.5)
            )
        else:
            chi[r2 != 0.0] = 2.0 * np.arctan(
                (r[r2 != 0.0] * cone / np.sin(chi1)) ** (1.0 / cone)
                * np.tan(chi1 * 0.5)
            )

        wrflat[r2 != 0.0] = (
            90.0 - chi[r2 != 0.0] * deg_per_rad
        ) * wrf_proj.hemi
        wrflon[wrflon > 180.0] = wrflon[wrflon > 180.0] - 360.0
        wrflon[wrflon < -180.0] = wrflon[wrflon < -180.0] + 360.0

    elif wrf_proj.map_proj == 2:
        # -------- Polar stereographic projection --------

        # Copied from subroutine set_ps in geogrid/src/module_map_utils.f90:

        # Compute the reference longitude by rotating 90 degrees to the east
        # to find the longitude line parallel to the positive x-axis.
        reflon = wrf_proj.stdlon + 90.0
        # Compute numerator term of map scale factor
        scale_top = 1.0 + wrf_proj.hemi * np.sin(
            wrf_proj.truelat1 * rad_per_deg
        )
        # Calculate pole i and j
        # Compute radius to lower-left (SW) corner
        ala1 = wrf_proj.ref_lat * rad_per_deg
        rsw = (
            rebydx
            * np.cos(ala1)
            * scale_top
            / (1.0 + wrf_proj.hemi * np.sin(ala1))
        )
        # Find the pole point
        alo1 = (wrf_proj.ref_lon - reflon) * rad_per_deg
        polei = wrf_proj.ref_i - rsw * np.cos(alo1)
        polej = wrf_proj.ref_j - wrf_proj.hemi * rsw * np.sin(alo1)

        # Copied from subroutine ijll_ps in geogrid/src/module_map_utils.f90:

        # Compute radius to point of interest
        xx = wrfi - polei
        yy = (wrfj - polej) * wrf_proj.hemi
        r2 = xx**2.0 + yy**2.0
        # Now the magic code
        wrflat[r2 == 0] = wrf_proj.hemi * 90.0
        wrflon[r2 == 0] = reflon
        gi2 = (rebydx * scale_top) ** 2.0
        wrflat[r2 != 0] = (
            deg_per_rad
            * wrf_proj.hemi
            * np.arcsin((gi2 - r2[r2 != 0]) / (gi2 + r2[r2 != 0]))
        )
        arccos = np.arccos(xx / np.sqrt(r2))
        if np.any(np.logical_and(r2 != 0.0, yy > 0.0)):
            wrflon[np.logical_and(r2 != 0.0, yy > 0.0)] = (
                reflon
                + deg_per_rad * arccos[np.logical_and(r2 != 0.0, yy > 0.0)]
            )
        if np.any(np.logical_and(r2 != 0.0, yy <= 0.0)):
            wrflon[np.logical_and(r2 != 0.0, yy <= 0.0)] = (
                reflon
                - deg_per_rad * arccos[np.logical_and(r2 != 0.0, yy <= 0.0)]
            )
    elif wrf_proj.map_proj == 3:
        # -------- Mercator projection --------
        # Copied from subroutine set_merc in geogrid/src/module_map_utils.f90:

        clain = np.cos(rad_per_deg * wrf_proj.truelat1)
        dlon = 1.0 / (rebydx * clain)
        # Compute distance from equator to origin
        rsw = 0.0
        if wrf_proj.ref_lat != 0.0:
            rsw = (
                np.log(np.tan(0.5 * ((wrf_proj.ref_lat + 90.0) * rad_per_deg)))
            ) / dlon

        # Copied from subroutine ijll_merc in geogrid/src/module_map_utils.f90:

        wrflat = (
            2.0
            * np.arctan(np.exp(dlon * (rsw + wrfj - wrf_proj.ref_j)))
            * deg_per_rad
            - 90.0
        )
        wrflon = (
            wrfi - wrf_proj.ref_i
        ) * dlon * deg_per_rad + wrf_proj.ref_lon

    else:
        msg = f"wrf_proj.map_proj={wrf_proj.map_proj} invalid."
        raise ValueError(msg)

    # Convert to a -180 -> 180 East convention
    if np.any(wrflon > 180.0):
        wrflon[wrflon > 180.0] = wrflon[wrflon > 180.0] - 360.0
    if np.any(wrflon > 180.0):
        wrflon[wrflon < -180.0] = wrflon[wrflon < -180.0] + 360.0

    return wrflat, wrflon


# -----------------------------------------------------------------------------


def calc_wrf_grid_edges(wrf_proj):
    """Calculate the latitude and longitude of the grid cell edges of a WRF grid

    Parameters
    ----------
    wrf_proj: WRFProjection instance
        The projection of the WRF grid

    """

    wrf_i_edge = np.linspace(0.5, wrf_proj.imax + 0.5, wrf_proj.imax + 1)
    wrf_j_edge = np.linspace(0.5, wrf_proj.jmax + 0.5, wrf_proj.jmax + 1)
    wrf_lat_edge = np.empty((wrf_proj.jmax + 1, wrf_proj.imax + 1))
    wrf_lon_edge = np.empty((wrf_proj.jmax + 1, wrf_proj.imax + 1))
    for ii in range(0, wrf_proj.imax + 1):
        wrf_lat_edge[:, ii], wrf_lon_edge[:, ii] = wrf_ijll(
            wrf_i_edge[ii] * np.ones((np.shape(wrf_j_edge))),
            wrf_j_edge,
            wrf_proj,
        )
    return wrf_lat_edge, wrf_lon_edge

