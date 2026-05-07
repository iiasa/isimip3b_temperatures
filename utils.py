"""
utils.py -- Helper functions for ISIMIP3b temperature anomaly calculations
==========================================================================
Creator : Dr. Andre Nakhavali, IIASA (nakhavali@iiasa.ac.at)
Created : 2026

Method per model x scenario:
  1. Discover tas NetCDF files (historical + scenario)
  2. Open with xarray + dask (lazy loading)
  3. Cos-latitude area-weighted global mean
  4. Annual resampling (all days weighted equally)
  5. Subtract 1850-1900 reference mean -> anomaly [K]
"""

import glob
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

logger = logging.getLogger(__name__)


# ── File discovery ─────────────────────────────────────────────────────────────

def find_files(input_root: str, scenario: str, model_dir: str,
               variable: str = "tas") -> list[str]:
    """Return sorted list of NetCDF files matching a model/scenario/variable."""
    pattern = os.path.join(
        input_root, scenario, model_dir,
        f"*_{variable}_global_daily_*.nc"
    )
    files = sorted(glob.glob(pattern))
    if not files:
        logger.warning("No files found: %s", pattern)
    else:
        logger.debug("Found %d files for %s/%s/%s", len(files), model_dir, scenario, variable)
    return files


# ── Data loading ───────────────────────────────────────────────────────────────

def _open_mf(files: list[str], variable: str, chunk_days: int) -> xr.DataArray:
    """Open and concatenate multiple NetCDF files into one DataArray."""
    ds = xr.open_mfdataset(
        files,
        combine="by_coords",
        chunks={"time": chunk_days},
        engine="netcdf4",
        data_vars="minimal",
        coords="minimal",
        compat="override",
    )
    return ds[variable]


def load_hist_plus_scenario(hist_files: list[str], scen_files: list[str],
                             variable: str = "tas",
                             chunk_days: int = 3650) -> xr.DataArray:
    """Load historical + scenario files concatenated along time."""
    return _open_mf(hist_files + scen_files, variable, chunk_days)


def load_scenario_only(files: list[str], variable: str = "tas",
                       chunk_days: int = 3650) -> xr.DataArray:
    """Load a standalone scenario (e.g. piControl) without historical concat."""
    return _open_mf(files, variable, chunk_days)


# ── Spatial aggregation ────────────────────────────────────────────────────────

def _lat_name(da: xr.DataArray) -> str:
    for c in ["lat", "latitude", "nav_lat"]:
        if c in da.dims or c in da.coords:
            return c
    raise ValueError(f"Latitude coordinate not found in: {list(da.dims)}")


def _lon_name(da: xr.DataArray) -> str:
    for c in ["lon", "longitude", "nav_lon"]:
        if c in da.dims or c in da.coords:
            return c
    raise ValueError(f"Longitude coordinate not found in: {list(da.dims)}")


def area_weighted_global_mean(da: xr.DataArray) -> xr.DataArray:
    """
    Compute cos(latitude)-weighted global mean.
    ISIMIP3b bias-adjusted files do not include areacella, so cos(lat)
    is used as the area proxy — identical to the cmip_temperatures fallback.
    """
    lat = _lat_name(da)
    lon = _lon_name(da)
    weights = np.cos(np.deg2rad(da[lat]))
    weights.name = "weights"
    return da.weighted(weights).mean([lat, lon])


# ── Temporal aggregation ───────────────────────────────────────────────────────

def annual_mean(da: xr.DataArray) -> xr.DataArray:
    """
    Resample daily global-mean to annual means (calendar year).
    All days within a year are weighted equally, consistent with
    the cmip_temperatures methodology.
    Returns a DataArray with integer 'year' coordinate.
    """
    da_ann = da.resample(time="YE").mean()
    da_ann["time"] = da_ann["time"].dt.year
    return da_ann.rename({"time": "year"})


# ── Anomaly calculation ────────────────────────────────────────────────────────

def compute_anomaly(da_annual: xr.DataArray,
                    ref_start: int, ref_end: int) -> xr.DataArray:
    """
    Subtract the mean over [ref_start, ref_end] from each annual value.
    Returns anomaly in Kelvin (same unit as tas).
    """
    ref_mean = da_annual.sel(year=slice(ref_start, ref_end)).mean("year")
    anomaly = da_annual - ref_mean
    anomaly.attrs.update({"units": "K",
                          "reference_period": f"{ref_start}-{ref_end}",
                          "long_name": "Annual global-mean temperature anomaly"})
    return anomaly


# ── Output formatting ──────────────────────────────────────────────────────────

def to_dataframe(da_anomaly: xr.DataArray,
                 model: str, scenario: str) -> pd.DataFrame:
    """Convert annual anomaly DataArray to a tidy long-format DataFrame."""
    df = da_anomaly.to_dataframe(name="tas_anomaly_K").reset_index()
    df.insert(0, "model", model)
    df.insert(1, "scenario", scenario)
    return df[["model", "scenario", "year", "tas_anomaly_K"]]
