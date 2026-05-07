"""
isimip3b_anomalies.py — Main processing script
===============================================
Computes yearly global-mean temperature anomalies (relative to 1850-1900)
for all ISIMIP3b bias-adjusted models and SSP scenarios.

Follows the method from cmip_temperatures (Hauser 2021):
  https://github.com/mathause/cmip_temperatures

Usage:
  python isimip3b_anomalies.py              # process all models & scenarios
  python isimip3b_anomalies.py --dry-run   # list files only, no computation

Output (in output/):
  isimip3b_tas_anomalies_yearly.csv   all models × scenarios, long format
  isimip3b_tas_mmm_yearly.csv         multi-model mean per scenario per year
  by_model/<model>_<scenario>_anomalies.csv
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

import config
import utils

# ── Logging ───────────────────────────────────────────────────────────────────
Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
import io
_stdout_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))
_file_handler  = logging.FileHandler(os.path.join(config.OUTPUT_DIR, "processing.log"),
                                     mode="w", encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_stdout_handler, _file_handler],
)
logger = logging.getLogger(__name__)


# ── Per-combination processor ─────────────────────────────────────────────────

def process_ssp(model_dir: str, model_name: str, scenario: str,
                dry_run: bool = False) -> pd.DataFrame | None:
    """Process one model × SSP scenario. Returns DataFrame or None on failure."""
    logger.info("[>>] %s / %s", model_dir, scenario)

    hist_files = utils.find_files(config.INPUT_ROOT, "historical", model_dir, config.VARIABLE)
    scen_files = utils.find_files(config.INPUT_ROOT, scenario,     model_dir, config.VARIABLE)

    if not hist_files:
        logger.warning("  ✗ No historical files — skipping")
        return None
    if not scen_files:
        logger.warning("  ✗ No %s files — skipping", scenario)
        return None

    logger.info("  %d historical + %d %s files", len(hist_files), len(scen_files), scenario)
    if dry_run:
        return None

    try:
        da = utils.load_hist_plus_scenario(hist_files, scen_files,
                                           config.VARIABLE, config.CHUNK_DAYS)
        logger.info("  Computing area-weighted global mean ...")
        da_gm = utils.area_weighted_global_mean(da)

        logger.info("  Resampling to annual means ...")
        da_ann = utils.annual_mean(da_gm)

        da_anom = utils.compute_anomaly(da_ann, config.REF_START, config.REF_END)
        logger.info("  Triggering dask computation ...")
        da_anom = da_anom.compute()

        df = utils.to_dataframe(da_anom, model_name, scenario)
        logger.info("  ✓ %d years (%d–%d)", len(df), df.year.min(), df.year.max())
        return df

    except Exception as exc:
        logger.error("  ✗ Failed: %s", exc, exc_info=True)
        return None


def process_picontrol(model_dir: str, model_name: str,
                      dry_run: bool = False) -> pd.DataFrame | None:
    """
    Process piControl run.
    Anomaly is relative to the piControl's own full-period mean — this
    quantifies model drift and should be near-zero for a stable control run.
    """
    logger.info("[>>] %s / piControl", model_dir)

    files = utils.find_files(config.INPUT_ROOT, "piControl", model_dir, config.VARIABLE)
    if not files:
        logger.warning("  ✗ No piControl files — skipping")
        return None

    logger.info("  %d piControl files", len(files))
    if dry_run:
        return None

    try:
        da = utils.load_scenario_only(files, config.VARIABLE, config.CHUNK_DAYS)
        da_gm  = utils.area_weighted_global_mean(da)
        da_ann = utils.annual_mean(da_gm)

        # Anomaly relative to piControl own mean (drift check)
        pic_mean = da_ann.mean("year")
        da_anom  = (da_ann - pic_mean).compute()
        da_anom.attrs.update({
            "units": "K",
            "reference_period": "piControl_full_period_mean",
            "long_name": "Annual global-mean temperature anomaly (drift check)"
        })

        df = utils.to_dataframe(da_anom, model_name, "piControl")
        logger.info("  ✓ %d years", len(df))
        return df

    except Exception as exc:
        logger.error("  ✗ Failed: %s", exc, exc_info=True)
        return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False):
    Path(config.OUTPUT_BY_MODEL).mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("ISIMIP3b Temperature Anomalies")
    logger.info("Reference period : %d–%d", config.REF_START, config.REF_END)
    logger.info("Models           : %s", list(config.MODELS.keys()))
    logger.info("Scenarios        : %s", config.SCENARIOS)
    logger.info("piControl        : %s", config.INCLUDE_PICONTROL)
    logger.info("Dry run          : %s", dry_run)
    logger.info("=" * 60)

    all_dfs = []

    # SSP scenarios (historical + future concatenated)
    combos = [(md, mn, sc)
              for md, mn in config.MODELS.items()
              for sc in config.SCENARIOS]

    for model_dir, model_name, scenario in tqdm(combos, desc="SSP combinations"):
        df = process_ssp(model_dir, model_name, scenario, dry_run)
        if df is not None:
            all_dfs.append(df)
            out = os.path.join(config.OUTPUT_BY_MODEL,
                               f"{model_name}_{scenario}_anomalies.csv")
            df.to_csv(out, index=False)
            logger.info("  → Saved %s", out)

    # piControl (optional, drift assessment)
    if config.INCLUDE_PICONTROL:
        for model_dir, model_name in tqdm(config.MODELS.items(), desc="piControl"):
            df = process_picontrol(model_dir, model_name, dry_run)
            if df is not None:
                all_dfs.append(df)
                out = os.path.join(config.OUTPUT_BY_MODEL,
                                   f"{model_name}_piControl_anomalies.csv")
                df.to_csv(out, index=False)

    if dry_run:
        logger.info("Dry-run complete — no output written.")
        return

    if not all_dfs:
        logger.error("No results produced. Check INPUT_ROOT and model/scenario names.")
        sys.exit(1)

    # Combined CSV (all models × scenarios)
    combined = pd.concat(all_dfs, ignore_index=True)
    out_all = os.path.join(config.OUTPUT_DIR, "isimip3b_tas_anomalies_yearly.csv")
    combined.to_csv(out_all, index=False)
    logger.info("Saved combined CSV → %s", out_all)

    # Multi-model mean per scenario per year (SSP scenarios only)
    ssp_data = combined[combined.scenario.isin(config.SCENARIOS)]
    mmm = (
        ssp_data
        .groupby(["scenario", "year"])["tas_anomaly_K"]
        .agg(n_models="count", mmm_K="mean", std_K="std")
        .reset_index()
    )
    out_mmm = os.path.join(config.OUTPUT_DIR, "isimip3b_tas_mmm_yearly.csv")
    mmm.to_csv(out_mmm, index=False)
    logger.info("Saved multi-model mean CSV → %s", out_mmm)

    logger.info("✓ All done!")
    return combined, mmm


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute ISIMIP3b yearly temperature anomalies")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discover files and report counts, but skip computation")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
