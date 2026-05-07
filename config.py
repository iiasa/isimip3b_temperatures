"""
config.py — Central configuration for isimip3b_temperatures
============================================================
All paths, model names, scenarios, and processing parameters live here.
Edit this file to adapt to a different data location or to add new models.
"""

import os

# ── Input data ────────────────────────────────────────────────────────────────
INPUT_ROOT_GLOBAL = r"//pdrive/share/link/nakhavali.pdrv/watxene/ISIMIP/ISIMIP3b/InputData/climate_updated/bias-adjusted"
INPUT_ROOT_EU     = r"P:\bnr\02_Data\ISIMIP3b_monthly"

# ── Output ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_DIR is now determined dynamically in the main script based on the region.

# ── Models ────────────────────────────────────────────────────────────────────
# Keys   = directory names on pdrive (case-sensitive)
# Values = canonical model names used in output files
MODELS = {
    "GFDL-ESM4":     "gfdl-esm4",
    "IPSL-CM6A-LR":  "ipsl-cm6a-lr",
    "MPI-ESM1-2-HR": "mpi-esm1-2-hr",
    "MRI-ESM2-0":    "mri-esm2-0",
    "UKESM1-0-LL":   "ukesm1-0-ll",
}

# ── Scenarios ─────────────────────────────────────────────────────────────────
# Main SSP scenarios processed as historical + SSP concatenation
SCENARIOS = ["ssp126", "ssp245", "ssp370", "ssp585"]

# Include piControl (drift assessment, anomaly vs. piControl own mean)
INCLUDE_PICONTROL = True

# ── Variable ──────────────────────────────────────────────────────────────────
VARIABLE = "tas"   # Near-surface air temperature

# ── Time periods ──────────────────────────────────────────────────────────────
HIST_START = 1850   # First year of historical period
HIST_END   = 2014   # Last  year of historical period
SCEN_START = 2015   # First year of scenario period
SCEN_END   = 2100   # Last  year of scenario period

# Reference period for anomaly calculation (IPCC pre-industrial baseline)
REF_START = 1850
REF_END   = 1900

# ── Dask chunk size (days) ────────────────────────────────────────────────────
# ~10 years of daily data per chunk — tune if RAM is limited
CHUNK_DAYS = 3650
