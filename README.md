# ISIMIP3b Temperature Anomalies

Yearly global-mean surface temperature anomalies for ISIMIP3b bias-adjusted climate models, adapted from [cmip_temperatures](https://github.com/mathause/cmip_temperatures) (Hauser, 2021).

## Models

| Model | Ensemble |
|---|---|
| GFDL-ESM4 | r1i1p1f1 |
| IPSL-CM6A-LR | r1i1p1f1 |
| MPI-ESM1-2-HR | r1i1p1f1 |
| MRI-ESM2-0 | r1i1p1f1 |
| UKESM1-0-LL | r1i1p1f2 |

## Scenarios

`historical` (1850–2014) + `ssp126`, `ssp245`, `ssp370`, `ssp585` (2015–2100), and `piControl`.

## Method

Follows the approach of Hauser (2021) for each model × scenario:

1. **Load** all daily `tas` NetCDF files — historical (1850–2014) concatenated with the SSP scenario (2015–2100)
2. **Area-weighted global mean** — cos(latitude) weights (ISIMIP3b does not provide `areacella`)
3. **Annual mean** — all days within a year weighted equally
4. **Subtract 1850–1900 mean** — IPCC pre-industrial reference baseline
5. **Output** — one row per year: `model, scenario, year, tas_anomaly_K`

For **piControl**, the anomaly is relative to the piControl's own full-period mean (drift assessment only).

## Input data

```
//pdrive/.../bias-adjusted/
  {scenario}/
    {MODEL}/
      {model}_{ens}_w5e5_{scenario}_tas_global_daily_{start}_{end}.nc
```

## Output

```
output/
  isimip3b_tas_anomalies_yearly.csv     # all models × scenarios, long format
  isimip3b_tas_mmm_yearly.csv           # multi-model mean + std per scenario/year
  by_model/
    gfdl-esm4_ssp126_anomalies.csv
    ...
  isimip3b_tas_anomalies_4panel.png     # 4-panel SSP figure
  isimip3b_tas_anomalies_overlay.png    # all SSPs on one panel
  isimip3b_picontrol_drift.png          # piControl drift check
```

### Output columns

| Column | Description |
|---|---|
| `model` | Model name (lowercase, e.g. `gfdl-esm4`) |
| `scenario` | Scenario (e.g. `ssp126`, `piControl`) |
| `year` | Calendar year (integer) |
| `tas_anomaly_K` | Annual global-mean temperature anomaly [K] vs 1850–1900 |

## Usage

```bash
# 1. Create environment
conda env create -f environment.yml
conda activate isimip3b_temps

# 2. Dry run (discover files, no computation)
python isimip3b_anomalies.py --dry-run

# 3. Full run
python isimip3b_anomalies.py

# 4. Generate plots
python plot_anomalies.py
```

## Reference

Hauser, M. (2021). *Global mean temperature anomalies for CMIP5 and CMIP6*.  
Zenodo. https://doi.org/10.5281/zenodo.5532894

ISIMIP3b protocol: https://www.isimip.org/protocol/3b/
