#!/usr/bin/env python3
"""Generate the archived RQ2 figures solely from the exported result CSV tables."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

_CACHE_ROOT = Path(os.environ.get("RQ2_PLOT_CACHE", "/tmp/rq2_plot_cache"))
_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_ROOT / "xdg"))

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager

# The runner does not ship Microsoft's proprietary font files.  Nimbus Roman is
# the installed Times New Roman-compatible face; register all four faces
# explicitly so normal, bold and italic text never falls back to DejaVu Sans.
_TIMES_FONT_DIR = Path("/usr/share/fonts/opentype/urw-base35")
_TIMES_FONT_FILES = (
    "NimbusRoman-Regular.otf",
    "NimbusRoman-Bold.otf",
    "NimbusRoman-Italic.otf",
    "NimbusRoman-BoldItalic.otf",
)
if all((_TIMES_FONT_DIR / name).exists() for name in _TIMES_FONT_FILES):
    for _font_file in _TIMES_FONT_FILES:
        font_manager.fontManager.addfont(str(_TIMES_FONT_DIR / _font_file))
    _TIMES_FAMILY = font_manager.FontProperties(
        fname=str(_TIMES_FONT_DIR / "NimbusRoman-Regular.otf")
    ).get_name()
else:
    # On machines that have the Microsoft font installed, Matplotlib resolves
    # the requested family directly.
    _TIMES_FAMILY = "Times New Roman"
matplotlib.rcParams.update({
    "font.family": _TIMES_FAMILY,
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 14,
    "legend.fontsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DATASET_ORDER = ["GitHub-C", "GitHub-Java", "CSN-JavaScript", "CSN-Java"]
METHOD_ORDER = ["SrcMarker", "CodeMark"]
CHANNEL_ORDER = ["id", "expr", "block", "all"]
COLORS = {"SrcMarker": "#3569B7", "CodeMark": "#D36B34"}
BAR_COLORS = [COLORS["SrcMarker"], COLORS["CodeMark"], "#5B8E55"]
BAR_STYLE = {"edgecolor": "black", "linewidth": 0.55, "alpha": 0.9}
SINGLE_PANEL_SIZE = (8.8, 4.2)
SINGLE_PANEL_LAYOUT = {
    "left": 0.095,
    "right": 0.995,
    "bottom": 0.13,
    "top": 0.86,
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-dir", default="deliverables/03_tables_figures/tables")
    parser.add_argument("--output-dir", default="deliverables/03_tables_figures/figures")
    parser.add_argument("--dpi", type=int, default=240)
    return parser.parse_args()


def save(
    fig, output_dir: Path, stem: str, dpi: int,
    tight: bool = True, crop: bool = True,
):
    if tight:
        fig.tight_layout()
    save_options = {"bbox_inches": "tight"} if crop else {}
    fig.savefig(output_dir / f"{stem}.png", dpi=dpi, **save_options)
    fig.savefig(output_dir / f"{stem}.pdf", **save_options)
    plt.close(fig)


def style_single_panel_bar(axis, legend_columns: int):
    """Apply the shared visual language used by both single-panel bar charts."""
    axis.set_axisbelow(True)
    axis.grid(axis="y", color="#B8B8B8", linewidth=0.7, alpha=0.45)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(
        frameon=False,
        ncol=legend_columns,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.01),
        borderaxespad=0,
        handlelength=1.6,
        columnspacing=1.4,
    )


def method_attack_comparison(rule, llm, output_dir, dpi):
    rule_all = rule[rule["channel"] == "all"].copy()
    rule_all["attack"] = "Rule-ALL"
    llm = llm.copy()
    llm["attack"] = "LLM-RAG"
    combined = pd.concat([rule_all, llm], ignore_index=True)
    x = np.arange(len(DATASET_ORDER), dtype=float)
    width = 0.19
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.6), sharex=True)
    for axis, metric, label in zip(
        axes, ["attack_BAR", "attack_MAR"], ["Attacked BAR", "Attacked MAR"]
    ):
        offset_index = 0
        for attack in ["Rule-ALL", "LLM-RAG"]:
            for method in METHOD_ORDER:
                values = []
                for dataset in DATASET_ORDER:
                    cell = combined[
                        (combined["attack"] == attack)
                        & (combined["method"] == method)
                        & (combined["dataset"] == dataset)
                    ]
                    values.append(float(cell.iloc[0][metric]))
                offset = (offset_index - 1.5) * width
                hatch = "" if attack == "Rule-ALL" else "//"
                axis.bar(
                    x + offset, values, width, color=COLORS[method], alpha=0.9,
                    edgecolor="black", linewidth=0.45, hatch=hatch,
                    label=f"{method} / {attack}",
                )
                offset_index += 1
        axis.axhline(0.5 if metric == "attack_BAR" else 0.0625,
                     color="#555555", linestyle="--", linewidth=1, label="Chance")
        axis.set_ylabel(label)
        axis.set_ylim(0, 1.04)
        axis.set_xticks(x, DATASET_ORDER, rotation=0, ha="center")
        axis.grid(axis="y", alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.995),
               ncol=5, frameon=False, fontsize=12.5, handlelength=1.7,
               columnspacing=1.0)
    fig.subplots_adjust(top=0.84, bottom=0.19, left=0.07, right=0.99, wspace=0.13)
    save(fig, output_dir, "rq2_attack_bar_mar", dpi, tight=False)


def delta_heatmap(rule, output_dir, dpi):
    fig = plt.figure(figsize=(10.8, 4.6))
    grid = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.045], wspace=0.32)
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])]
    color_axis = fig.add_subplot(grid[0, 2])
    for axis, method in zip(axes, METHOD_ORDER):
        subset = rule[rule["method"] == method]
        matrix = np.asarray([
            [
                float(subset[(subset["dataset"] == dataset) & (subset["channel"] == channel)].iloc[0]["DeltaBAR"])
                for channel in CHANNEL_ORDER
            ]
            for dataset in DATASET_ORDER
        ])
        image = axis.imshow(matrix, cmap="YlOrRd", vmin=-0.01, vmax=max(0.55, matrix.max()))
        axis.set_title(method, fontweight="bold")
        axis.set_xticks(np.arange(len(CHANNEL_ORDER)), [value.upper() for value in CHANNEL_ORDER])
        axis.set_yticks(np.arange(len(DATASET_ORDER)), DATASET_ORDER)
        for row in range(matrix.shape[0]):
            for column in range(matrix.shape[1]):
                axis.text(column, row, f"{matrix[row, column]:.3f}", ha="center", va="center",
                          fontsize=10, color="white" if matrix[row, column] > 0.3 else "black")
    axes[1].tick_params(labelleft=False)
    fig.colorbar(image, cax=color_axis, label="ΔBAR")
    fig.subplots_adjust(left=0.12, right=0.94, top=0.88, bottom=0.12)
    save(fig, output_dir, "rq2_rule_delta_bar_heatmap", dpi, tight=False)


def epr_figure(epr, output_dir, dpi):
    x = np.arange(len(CHANNEL_ORDER), dtype=float)
    width = 0.24
    fig, axis = plt.subplots(figsize=SINGLE_PANEL_SIZE)
    containers = []
    for dataset_index, dataset in enumerate(["MBCPP", "MBJP", "MBJSP"]):
        values = [
            float(epr[(epr["dataset_label"] == dataset) & (epr["channel"] == channel)].iloc[0]["EPR"])
            for channel in CHANNEL_ORDER
        ]
        containers.append(axis.bar(
            x + (dataset_index - 1) * width,
            values,
            width,
            label=dataset,
            color=BAR_COLORS[dataset_index],
            **BAR_STYLE,
        ))
    axis.set_xticks(x, [value.upper() for value in CHANNEL_ORDER])
    axis.set_ylabel("Execution Preservation Rate")
    axis.set_ylim(0.94, 1.006)
    style_single_panel_bar(axis, legend_columns=3)
    for container in containers:
        axis.bar_label(
            container,
            labels=[f"{bar.get_height():.3f}" for bar in container],
            padding=3,
            fontsize=9,
        )
    fig.subplots_adjust(**SINGLE_PANEL_LAYOUT)
    save(fig, output_dir, "rq2_rule_epr", dpi, tight=False, crop=False)


def llm_validity_figure(llm, output_dir, dpi):
    x = np.arange(len(DATASET_ORDER), dtype=float)
    width = 0.35
    fig, axis = plt.subplots(figsize=SINGLE_PANEL_SIZE)
    containers = []
    for method_index, method in enumerate(METHOD_ORDER):
        values = [
            float(llm[(llm["method"] == method) & (llm["dataset"] == dataset)].iloc[0]["paired_coverage"])
            for dataset in DATASET_ORDER
        ]
        containers.append(axis.bar(
            x + (method_index - 0.5) * width,
            values,
            width,
            label=method,
            color=BAR_COLORS[method_index],
            **BAR_STYLE,
        ))
    axis.set_xticks(x, DATASET_ORDER, rotation=0, ha="center")
    axis.set_ylabel("Valid attacked-pair coverage")
    axis.set_ylim(0.90, 1.006)
    style_single_panel_bar(axis, legend_columns=2)
    for container in containers:
        axis.bar_label(container, labels=[f"{bar.get_height():.3f}" for bar in container],
                       padding=3, fontsize=9)
    fig.subplots_adjust(**SINGLE_PANEL_LAYOUT)
    save(fig, output_dir, "rq2_llm_validity_coverage", dpi, tight=False, crop=False)


def main():
    args = parse_args()
    table_dir = Path(args.table_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rule = pd.read_csv(table_dir / "rq2_rule_robustness.csv")
    llm = pd.read_csv(table_dir / "rq2_llm_robustness.csv")
    epr = pd.read_csv(table_dir / "rq2_rule_epr.csv")
    method_attack_comparison(rule, llm, output_dir, args.dpi)
    delta_heatmap(rule, output_dir, args.dpi)
    epr_figure(epr, output_dir, args.dpi)
    llm_validity_figure(llm, output_dir, args.dpi)
    print(f"generated 4 figures as PNG+PDF under {output_dir}")


if __name__ == "__main__":
    main()
