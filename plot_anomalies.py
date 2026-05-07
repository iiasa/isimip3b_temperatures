"""
plot_anomalies.py -- Diagnostic visualisation of yearly anomalies
=================================================================
Creator : Dr. Andre Nakhavali, IIASA (nakhavali@iiasa.ac.at)
Created : 2026

Reads the CSVs produced by isimip3b_anomalies.py and generates:
  1. Per-scenario spaghetti plot (one line per model) + multi-model mean
  2. Combined 4-panel figure (one panel per SSP)
  3. Boxplot comparison with model labels (Time Horizons: 2030, 2050, 2100)
"""

import os
import sys
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

# ── Style ─────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":      "sans-serif",
    "font.size":        11,
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "figure.dpi":       150,
})

SCENARIO_COLORS = {
    "ssp126": "#2c7bb6",
    "ssp245": "#abd9e9",
    "ssp370": "#fdae61",
    "ssp585": "#d7191c",
    "piControl": "#9ecae1",
}

SCENARIO_LABELS = {
    "ssp126": "SSP1-2.6",
    "ssp245": "SSP2-4.5",
    "ssp370": "SSP3-7.0",
    "ssp585": "SSP5-8.5",
}

def load_data():
    path = os.path.join(config.OUTPUT_DIR, "isimip3b_tas_anomalies_yearly.csv")
    mmm_path = os.path.join(config.OUTPUT_DIR, "isimip3b_tas_mmm_yearly.csv")
    if not os.path.exists(path):
        sys.exit(f"Output file not found: {path}\nRun isimip3b_anomalies.py first.")
    df = pd.read_csv(path)
    mmm = pd.read_csv(mmm_path) if os.path.exists(mmm_path) else None
    return df, mmm

def plot_scenario_panel(ax, df, mmm, scenario, region_label=""):
    """Draw spaghetti lines + shaded MMM ± 1σ for one scenario."""
    color = SCENARIO_COLORS.get(scenario, "gray")
    label = SCENARIO_LABELS.get(scenario, scenario)

    # Individual models
    for model, grp in df[df.scenario == scenario].groupby("model"):
        ax.plot(grp.year, grp.tas_anomaly_K, lw=0.8, alpha=0.45,
                color=color, zorder=2)

    # Multi-model mean ± 1 std
    if mmm is not None:
        sc = mmm[mmm.scenario == scenario]
        ax.plot(sc.year, sc.mmm_K, lw=2.2, color=color, label=label, zorder=3)
        if "std_K" in sc.columns:
            ax.fill_between(sc.year,
                            sc.mmm_K - sc.std_K,
                            sc.mmm_K + sc.std_K,
                            alpha=0.18, color=color, zorder=1)

    ax.axhline(0, color="0.5", lw=0.8, ls="--")
    ax.axvline(1900, color="0.7", lw=0.7, ls=":")
    ax.set_ylabel(f"ΔT (K) {region_label}", fontsize=10)
    ax.set_xlabel("Year", fontsize=10)
    ax.set_title(label, fontweight="bold", color=color)

def plot_combined(df, mmm, region_name):
    """4-panel figure, one panel per SSP scenario."""
    scenarios = [s for s in config.SCENARIOS if s in df.scenario.unique()]
    if not scenarios: return
    
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True, sharey=True)
    axes = axes.flatten()

    region_label = f"({region_name.upper()})"
    for i, sc in enumerate(scenarios):
        if i < len(axes):
            plot_scenario_panel(axes[i], df, mmm, sc, region_label)

    fig.suptitle(
        f"ISIMIP3b {region_name.upper()} — Yearly Temperature Anomalies\n"
        f"(relative to {config.REF_START}–{config.REF_END}; shading = ±1σ across models)",
        fontsize=13, fontweight="bold", y=1.01,
    )
    fig.tight_layout()
    out = os.path.join(config.OUTPUT_DIR, f"isimip3b_tas_anomalies_4panel_{region_name}.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved -> {out}")
    plt.close(fig)

def plot_boxplots(df, region_name):
    """Boxplot comparison across models and scenarios for key years."""
    horizons = [2030, 2050, 2100]
    scenarios = [s for s in config.SCENARIOS if s in df.scenario.unique()]
    if not scenarios: return

    fig, axes = plt.subplots(1, len(horizons), figsize=(16, 7), sharey=True)
    if len(horizons) == 1: axes = [axes]

    for i, year in enumerate(horizons):
        ax = axes[i]
        year_df = df[df.year == year].copy()
        
        # Prepare data for boxplot
        data_to_plot = []
        for sc in scenarios:
            vals = year_df[year_df.scenario == sc].tas_anomaly_K.values
            data_to_plot.append(vals if len(vals) > 0 else [np.nan])
        
        # Draw boxes
        box = ax.boxplot(data_to_plot, patch_artist=True, widths=0.6, showfliers=False)
        
        # Style boxes
        for j, (patch, sc) in enumerate(zip(box['boxes'], scenarios)):
            color = SCENARIO_COLORS.get(sc, "gray")
            patch.set_facecolor(color)
            patch.set_alpha(0.3)
            patch.set_edgecolor(color)
            
            # Overlay model names and points
            sc_df = year_df[year_df.scenario == sc]
            x = j + 1
            for _, row in sc_df.iterrows():
                y = row.tas_anomaly_K
                ax.scatter(x, y, color=color, s=20, zorder=5)
                # Shorten model name for display
                short_name = row.model.split('-')[0].upper()
                ax.text(x + 0.1, y, short_name, fontsize=7, verticalalignment='center')

        ax.set_title(f"Horizon: {year}", fontweight="bold", fontsize=12)
        ax.set_xticks(range(1, len(scenarios) + 1))
        ax.set_xticklabels([SCENARIO_LABELS.get(s, s) for s in scenarios], rotation=15)
        ax.grid(axis='y', alpha=0.3)
        if i == 0:
            ax.set_ylabel(f"Temperature Anomaly (K) {region_name.upper()}")

    fig.suptitle(f"ISIMIP3b Model Uncertainty Comparison — {region_name.upper()}", fontsize=14, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    out = os.path.join(config.OUTPUT_DIR, f"isimip3b_tas_comparison_boxplots_{region_name}.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved -> {out}")
    plt.close(fig)

def plot_picontrol(df, region_name):
    """Model drift check."""
    pic = df[df.scenario == "piControl"]
    if pic.empty: return

    fig, ax = plt.subplots(figsize=(10, 5))
    for model, grp in pic.groupby("model"):
        ax.plot(grp.year, grp.tas_anomaly_K, lw=1.5, label=model)

    ax.axhline(0, color="0.4", lw=0.8, ls="--")
    ax.set_xlabel("Year")
    ax.set_ylabel(f"ΔT (K) {region_name.upper()}")
    ax.set_title(f"piControl Drift Check — {region_name.upper()}", fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc='upper left', bbox_to_anchor=(1, 1))
    fig.tight_layout()
    out = os.path.join(config.OUTPUT_DIR, f"isimip3b_picontrol_drift_{region_name}.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved → {out}")
    plt.close(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", choices=["global", "eu"], default="global")
    args = parser.parse_args()
    
    # Set config output paths based on region
    if args.region == "eu":
        config.OUTPUT_DIR = os.path.join(config.PROJECT_ROOT, "output", "EU")
    else:
        config.OUTPUT_DIR = os.path.join(config.PROJECT_ROOT, "output", "global")

    df, mmm = load_data()
    plot_combined(df, mmm, args.region)
    plot_boxplots(df, args.region)
    plot_picontrol(df, args.region)
    print(f"OK: All {args.region.upper()} plots saved to {config.OUTPUT_DIR}")
