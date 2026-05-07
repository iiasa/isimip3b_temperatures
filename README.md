# ISIMIP3b Temperature Anomalies

**Creator:** Dr. Andre Nakhavali, IIASA (nakhavali@iiasa.ac.at)  
**Institution:** International Institute for Applied Systems Analysis (IIASA)  
**Created:** 2026

Yearly temperature anomalies (relative to 1850–1900) for ISIMIP3b bias-adjusted climate models. Supports both **Global** and **EU** processing modes.

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

## Processing Modes

| Mode | Region | Speed |
|---|---|---|
| **EU** (Default for EU work) | Europe  | Extremely Fast (minutes) |
| **Global** | Global | High Performance (hours) |

## Method

1. **Concatenation**: Automatically joins historical (1850–2014) and future scenario (2015–2100) files.
2. **Spatial Average**: Area-weighted mean using cos(latitude).
3. **Temporal Average**: Yearly mean from daily/monthly values.
4. **Baseline Subtraction**: Subtracts the 1850–1900 mean (IPCC pre-industrial reference).
5. **Categorization**: Adds an `experiment_part` column to distinguish historical vs future data.

## Output Structure

Results are stored in `output/{region}/`:

```
output/
  EU/                      # European scale results
  global/                  # Global scale results
    by_model/              # Individual model x scenario CSVs
    isimip3b_tas_anomalies_yearly.csv
    isimip3b_tas_mmm_yearly.csv
```

### Output Columns

| Column | Description |
|---|---|
| `model` | Model name (lowercase, e.g. `gfdl-esm4`) |
| `scenario` | Scenario (e.g. `ssp126`, `piControl`) |
| `year` | Calendar year (1850–2100) |
| `experiment_part` | `historical` (<=2014), `future` (>2014), or `piControl` |
| `tas_anomaly_K` | Annual temperature anomaly [K] vs 1850–1900 |

## Usage

```bash
# 1. EU Scale (Monthly Data) - Fast
python isimip3b_anomalies.py --region eu

# 2. Global Scale (Daily Data)
python isimip3b_anomalies.py --region global

# 3. Quick Test (1 model, 1 scenario, limited years)
python isimip3b_anomalies.py --region eu --test

# 4. Generate plots
python plot_anomalies.py
```

## Reference

ISIMIP3b protocol: https://www.isimip.org/protocol/3b/
