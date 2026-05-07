"""
plot_anomalies.py -- Diagnostic visualisation of yearly anomalies
=================================================================
Creator : Dr. Andre Nakhavali, IIASA (nakhavali@iiasa.ac.at)
Created : 2026

Reads the CSVs produced by isimip3b_anomalies.py and generates:
  1. Per-scenario spaghetti plot (one line per model) + multi-model mean
  2. Combined 4-panel figure (one panel per SSP)
  3. piControl drift check plot (if available)

Usage:
  python plot_anomalies.py
"""

import os
import sys

import matplotlib.pyplot as plt
import matplotlib.cm as cm
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
    "ssp126": "#1a9641",
    "ssp245": "#a6d96a",
    "ssp370": "#fd8d3c",
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


def plot_scenario_panel(ax, df, mmm, scenario):
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
    ax.set_ylabel("ΔT (K) vs 1850–1900", fontsize=10)
    ax.set_xlabel("Year", fontsize=10)
    ax.set_title(label, fontweight="bold", color=color)


def plot_combined(df, mmm):
    """4-panel figure, one panel per SSP scenario."""
    scenarios = config.SCENARIOS
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True, sharey=True)
    axes = axes.flatten()

    for ax, sc in zip(axes, scenarios):
        plot_scenario_panel(ax, df, mmm, sc)

    fig.suptitle(
        "ISIMIP3b — Yearly Global-Mean Temperature Anomalies\n"
        f"(relative to {config.REF_START}–{config.REF_END}; shading = ±1σ across models)",
        fontsize=13, fontweight="bold", y=1.01,
    )
    fig.tight_layout()
    out = os.path.join(config.OUTPUT_DIR, "isimip3b_tas_anomalies_4panel.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved → {out}")
    plt.close(fig)


def plot_all_scenarios_overlay(df, mmm):
    """Single-panel overlay of all SSP multi-model means."""
    fig, ax = plt.subplots(figsize=(10, 6))
    for sc in config.SCENARIOS:
        plot_scenario_panel(ax, df, mmm, sc)

    handles = [
        plt.Line2D([0], [0], color=SCENARIO_COLORS[sc], lw=2.5,
                   label=SCENARIO_LABELS[sc])
        for sc in config.SCENARIOS
    ]
    ax.legend(handles=handles, frameon=False)
    ax.set_title(
        f"ISIMIP3b Yearly ΔT vs {config.REF_START}–{config.REF_END} "
        "(MMM ± 1σ, spaghetti)",
        fontsize=12, fontweight="bold"
    )
    fig.tight_layout()
    out = os.path.join(config.OUTPUT_DIR, "isimip3b_tas_anomalies_overlay.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved → {out}")
    plt.close(fig)


def plot_picontrol(df):
    """Model drift check: piControl anomaly vs. piControl own mean."""
    pic = df[df.scenario == "piControl"]
    if pic.empty:
        print("No piControl data — skipping drift plot.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    for model, grp in pic.groupby("model"):
        ax.plot(grp.year, grp.tas_anomaly_K, lw=1.5, label=model)

    ax.axhline(0, color="0.4", lw=0.8, ls="--")
    ax.set_xlabel("Year")
    ax.set_ylabel("ΔT (K) vs piControl mean")
    ax.set_title("ISIMIP3b piControl drift check", fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    out = os.path.join(config.OUTPUT_DIR, "isimip3b_picontrol_drift.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved → {out}")
    plt.close(fig)


if __name__ == "__main__":
    df, mmm = load_data()
    plot_combined(df, mmm)
    plot_all_scenarios_overlay(df, mmm)
    plot_picontrol(df)
    print("✓ All plots saved.")
