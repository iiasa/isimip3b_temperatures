"""
utils.py -- Helper functions for ISIMIP3b temperature anomaly calculations
==========================================================================
Creator : Dr. Andre Nakhavali, IIASA (nakhavali@iiasa.ac.at)
Created : 2026

Optimized for high-performance processing of ISIMIP3b NetCDF files over 
network drives using raw netCDF4 and multiprocessing.
"""

import glob
import logging
import os
import concurrent.futures
import numpy as np
import pandas as pd
import netCDF4 as nc

logger = logging.getLogger(__name__)

def find_files(input_root, scenario, model_dir, pattern_template="*_{variable}_global_daily_*.nc", variable="tas"):
    pattern = os.path.join(input_root, scenario, model_dir, pattern_template.format(variable=variable))
    return sorted(glob.glob(pattern))

def _process_single_file_raw(fpath, variable, weights):
    """Worker function to process one file using netCDF4."""
    with nc.Dataset(fpath, "r") as ds:
        var_obj = ds.variables[variable]
        n_lon = var_obj.shape[2]
        
        # Read full data (faster for 10yr files if network allows)
        data = var_obj[:]
        
        # Area-weighted mean
        gm = np.einsum("tlf,l->t", data, weights) / n_lon
        
        # Time conversion
        time_var = ds.variables["time"]
        times = nc.num2date(time_var[:], units=time_var.units, calendar=time_var.calendar)
        
    return pd.Series(gm, index=pd.DatetimeIndex([str(t) for t in times]))

def _files_to_annual_gmean(files, variable, test_years=None, n_workers=4):
    if test_years:
        files = _filter_files_by_years(files, *test_years)
        if not files: return pd.Series(dtype=float)

    # Get weights
    with nc.Dataset(files[0], "r") as ds0:
        lat = ds0.variables["lat"][:]
        weights = np.cos(np.deg2rad(lat))
        weights = weights / weights.sum()

    all_series = []
    logger.info(f"  Processing {len(files)} files in parallel ({n_workers} workers, raw netCDF4 mode)...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(_process_single_file_raw, f, variable, weights): f for f in files}
        
        count = 0
        for future in concurrent.futures.as_completed(futures):
            count += 1
            fpath = futures[future]
            try:
                res = future.result()
                all_series.append(res)
                logger.info(f"    [{count}/{len(files)}] Finished {os.path.basename(fpath)}")
            except Exception as e:
                logger.error(f"    [{count}/{len(files)}] Error in {os.path.basename(fpath)}: {e}")

    if not all_series: return pd.Series(dtype=float)
    
    daily = pd.concat(all_series).sort_index()
    
    if test_years:
        daily = daily[(daily.index.year >= test_years[0]) & (daily.index.year <= test_years[1])]

    annual = daily.resample("YE").mean()
    annual.index = annual.index.year
    return annual

def _filter_files_by_years(files, y_start, y_end):
    kept = []
    for f in files:
        base = os.path.basename(f)
        parts = base.replace(".nc4", "").replace(".nc", "").split("_")
        try:
            f_end, f_start = int(parts[-1]), int(parts[-2])
            if f_end >= y_start and f_start <= y_end: kept.append(f)
        except: kept.append(f)
    return kept

def load_hist_plus_scenario(hist_files, scen_files, variable, test_years=None, n_workers=4, **kwargs):
    return _files_to_annual_gmean(hist_files + scen_files, variable, test_years, n_workers=n_workers)

def load_scenario_only(files, variable, test_years=None, n_workers=4, **kwargs):
    return _files_to_annual_gmean(files, variable, test_years, n_workers=n_workers)

def compute_anomaly(annual, ref_start, ref_end):
    ref_mask = (annual.index >= ref_start) & (annual.index <= ref_end)
    if not any(ref_mask):
        raise ValueError(f"No data for reference period {ref_start}-{ref_end}")
    ref_mean = annual[ref_mask].mean()
    return annual - ref_mean

def to_dataframe(anomaly, model, scenario, hist_end=2014):
    df = anomaly.reset_index()
    df.columns = ["year", "tas_anomaly_K"]
    df.insert(0, "model", model)
    df.insert(1, "scenario", scenario)
    
    if scenario == "piControl":
        df.insert(2, "experiment_part", "piControl")
    else:
        df.insert(2, "experiment_part", df["year"].apply(lambda y: "historical" if y <= hist_end else "future"))
        
    return df
