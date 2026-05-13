"""
isimip3b_anomalies.py -- Main processing script
===============================================
Computes yearly global-mean temperature anomalies (relative to 1850-1900)
for all ISIMIP3b bias-adjusted models and scenarios.

Creator : Dr. Andre Nakhavali, IIASA (nakhavali@iiasa.ac.at)
Created : 2026

Usage:
  python isimip3b_anomalies.py              # process all models & scenarios
  python isimip3b_anomalies.py --dry-run   # list files only, no computation
  python isimip3b_anomalies.py --test      # quick 10-year test (1 model/scenario)

Output (in output/):
  isimip3b_tas_anomalies_yearly.csv   all models x scenarios, long format
  isimip3b_tas_mmm_yearly.csv         multi-model mean per scenario per year
  by_model/<model>_<scenario>_anomalies.csv
"""

import argparse
import io
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

import config
import utils

# ── Logging Setup ──────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

def setup_logging(output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    _stdout_handler = logging.StreamHandler(
        io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    )
    _file_handler = logging.FileHandler(
        os.path.join(output_dir, "processing.log"), mode="w", encoding="utf-8"
    )
    # Remove any existing handlers so we don't duplicate logs if called multiple times
    logging.getLogger().handlers = []
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[_stdout_handler, _file_handler],
    )



# ── Per-combination processor ──────────────────────────────────────────────────

def process_ssp(model_dir: str, model_name: str, scenario: str,
                dry_run: bool = False,
                test_years: tuple[int, int] | None = None,
                pattern_template: str = "*_{variable}_global_daily_*.nc",
                workers: int = 4) -> pd.DataFrame | None:
    """Process one model x SSP scenario. Returns DataFrame or None on failure."""
    logger.info("[>>] %s / %s", model_dir, scenario)

    hist_files = utils.find_files(config.INPUT_ROOT, "historical", model_dir, pattern_template, config.VARIABLE)
    scen_files = utils.find_files(config.INPUT_ROOT, scenario,     model_dir, pattern_template, config.VARIABLE)

    if not hist_files:
        logger.warning("  No historical files -- skipping")
        return None
    if not scen_files:
        logger.warning("  No %s files -- skipping", scenario)
        return None

    logger.info("  %d historical + %d %s files", len(hist_files), len(scen_files), scenario)
    if test_years:
        logger.info("  TEST MODE: limiting to years %d-%d", *test_years)
    if dry_run:
        return None

    try:
        logger.info("  Reading files and computing global mean ...")
        annual = utils.load_hist_plus_scenario(
            hist_files, scen_files,
            variable=config.VARIABLE,
            test_years=test_years,
            n_workers=workers
        )

        if annual.empty:
            logger.warning("  No data loaded -- skipping")
            return None

        logger.info("  Computing anomaly (ref: %d-%d) ...", config.REF_START, config.REF_END)
        anomaly = utils.compute_anomaly(annual, config.REF_START, config.REF_END)

        df = utils.to_dataframe(anomaly, model_name, scenario, hist_end=config.HIST_END)
        logger.info("  Done: %d years (%d-%d)", len(df), df.year.min(), df.year.max())
        return df

    except Exception as exc:
        logger.error("  Failed: %s", exc, exc_info=True)
        return None


def process_picontrol(model_dir: str, model_name: str,
                      dry_run: bool = False,
                      test_years: tuple[int, int] | None = None,
                      pattern_template: str = "*_{variable}_global_daily_*.nc",
                      workers: int = 4) -> pd.DataFrame | None:
    """Process piControl. Anomaly vs. piControl own mean (drift check)."""
    logger.info("[>>] %s / piControl", model_dir)

    files = utils.find_files(config.INPUT_ROOT, "piControl", model_dir, pattern_template, config.VARIABLE)
    if not files:
        logger.warning("  No piControl files -- skipping")
        return None

    logger.info("  %d piControl files", len(files))
    if dry_run:
        return None

    try:
        annual = utils.load_scenario_only(
            files, variable=config.VARIABLE, test_years=test_years, n_workers=workers
        )
        if annual.empty:
            return None

        # Anomaly vs. full-period mean (drift check)
        pic_mean = annual.mean()
        anomaly  = annual - pic_mean

        df = utils.to_dataframe(anomaly, model_name, "piControl", hist_end=config.HIST_END)
        logger.info("  Done: %d years", len(df))
        return df

    except Exception as exc:
        logger.error("  Failed: %s", exc, exc_info=True)
        return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, test: bool = False, region: str = "global", scenario_name: str = None, model_name_filter: str = None, model_name_exclude: str = None, workers: int = 4):
    
    if region == "eu":
        config.INPUT_ROOT = config.INPUT_ROOT_EU
        config.OUTPUT_DIR = os.path.join(config.PROJECT_ROOT, "output", "EU")
        pattern_template  = "*_{variable}_europe_monthly_mean.nc"
    else:
        config.INPUT_ROOT = config.INPUT_ROOT_GLOBAL
        config.OUTPUT_DIR = os.path.join(config.PROJECT_ROOT, "output", "global")
        pattern_template  = "*_{variable}_global_daily_*.nc"

    config.OUTPUT_BY_MODEL = os.path.join(config.OUTPUT_DIR, "by_model")
    
    setup_logging(config.OUTPUT_DIR)
    Path(config.OUTPUT_BY_MODEL).mkdir(parents=True, exist_ok=True)

    # Mode selection
    test_years = (1850, 1910) if test else None
    
    if test:
        models = dict(list(config.MODELS.items())[:1])
    elif model_name_filter:
        # Support comma-separated lists
        filter_list = [m.strip().lower() for m in model_name_filter.split(",")]
        models = {k: v for k, v in config.MODELS.items() 
                  if v.lower() in filter_list or k.lower() in filter_list}
    else:
        models = config.MODELS
        
    if model_name_exclude:
        exclude_list = [m.strip().lower() for m in model_name_exclude.split(",")]
        models = {k: v for k, v in models.items() 
                  if v.lower() not in exclude_list and k.lower() not in exclude_list}
    
    if scenario_name:
        # Support comma-separated lists
        scenarios = [s.strip() for s in scenario_name.split(",")]
    else:
        scenarios = [config.SCENARIOS[0]] if test else config.SCENARIOS

    logger.info("=" * 60)
    logger.info("ISIMIP3b Temperature Anomalies")
    logger.info("Region           : %s", region.upper())
    logger.info("Input Root       : %s", config.INPUT_ROOT)
    logger.info("Output Dir       : %s", config.OUTPUT_DIR)
    logger.info("Reference period : %d-%d", config.REF_START, config.REF_END)
    logger.info("Models           : %s", list(models.keys()))
    logger.info("Scenarios        : %s", scenarios)
    logger.info("piControl        : %s", config.INCLUDE_PICONTROL and not test)
    logger.info("Test mode        : %s%s",
                test, f"  (years {test_years[0]}-{test_years[1]})" if test else "")
    logger.info("Dry run          : %s", dry_run)
    logger.info("=" * 60)

    all_dfs = []

    combos = [(md, mn, sc)
              for md, mn in models.items()
              for sc in scenarios]

    for model_dir, model_name, scenario in tqdm(combos, desc="SSP combinations"):
        df = process_ssp(model_dir, model_name, scenario,
                         dry_run=dry_run, test_years=test_years, 
                         pattern_template=pattern_template, workers=workers)
        if df is not None:
            all_dfs.append(df)
            out = os.path.join(config.OUTPUT_BY_MODEL,
                               f"{model_name}_{scenario}_anomalies.csv")
            df.to_csv(out, index=False)
            logger.info("  Saved -> %s", out)

    # piControl (skip in test mode for speed)
    if config.INCLUDE_PICONTROL and not test:
        for model_dir, model_name in tqdm(models.items(), desc="piControl"):
            df = process_picontrol(model_dir, model_name,
                                   dry_run=dry_run, test_years=test_years, 
                                   pattern_template=pattern_template, workers=workers)
            if df is not None:
                all_dfs.append(df)
                out = os.path.join(config.OUTPUT_BY_MODEL,
                                   f"{model_name}_piControl_anomalies.csv")
                df.to_csv(out, index=False)

    if dry_run:
        logger.info("Dry-run complete -- no output written.")
        return

    if not all_dfs:
        logger.error("No results produced. Check INPUT_ROOT and model/scenario names.")
        sys.exit(1)

    # Combined CSV
    combined = pd.concat(all_dfs, ignore_index=True)
    suffix   = "_TEST" if test else ""
    out_all  = os.path.join(config.OUTPUT_DIR,
                             f"isimip3b_tas_anomalies_yearly{suffix}.csv")
    combined.to_csv(out_all, index=False)
    logger.info("Saved combined CSV -> %s", out_all)

    # Multi-model mean (SSP scenarios only, not needed for single-model test)
    ssp_data = combined[combined.scenario.isin(config.SCENARIOS)]
    if not ssp_data.empty:
        mmm = (
            ssp_data
            .groupby(["scenario", "year"])["tas_anomaly_K"]
            .agg(n_models="count", mmm_K="mean", std_K="std")
            .reset_index()
        )
        out_mmm = os.path.join(config.OUTPUT_DIR,
                               f"isimip3b_tas_mmm_yearly{suffix}.csv")
        mmm.to_csv(out_mmm, index=False)
        logger.info("Saved MMM CSV -> %s", out_mmm)

    # Sanity print in test mode
    if test:
        logger.info("\n--- TEST RESULTS ---")
        logger.info("\n%s", combined.to_string(index=False))
        logger.info("\nMean anomaly over test period: %.4f K",
                    combined["tas_anomaly_K"].mean())
        logger.info("(Expected: values near ~0.2-0.4 K for 1960-1969 vs 1850-1900)")

    logger.info("All done!")
    return combined


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute ISIMIP3b yearly temperature anomalies"
    )
    parser.add_argument("--region", choices=["global", "eu"], default="global",
                        help="Region to process: 'global' (daily data) or 'eu' (monthly data)")
    parser.add_argument("--scenario", type=str, default=None,
                        help="Scenario(s) to process (e.g. ssp126,ssp585).")
    parser.add_argument("--model", type=str, default=None,
                        help="Model(s) to process (e.g. gfdl-esm4,ukesm1-0-ll).")
    parser.add_argument("--exclude-model", type=str, default=None,
                        help="Model(s) to skip.")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel workers (reduce if running out of memory).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discover files only, no computation")
    parser.add_argument("--test", action="store_true",
                        help="Quick test: 1 model, 1 scenario, 10 years")
    args = parser.parse_args()
    main(dry_run=args.dry_run, test=args.test, region=args.region, 
         scenario_name=args.scenario, model_name_filter=args.model, 
         model_name_exclude=args.exclude_model, workers=args.workers)
