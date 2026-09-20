#!/usr/bin/env python3
import argparse
import csv
import os
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D


PROJECTS = ("brick_breaker", "caro", "flappy_bird", "snake", "tank_battle")
PROJECT_LABELS = {
    "brick_breaker": "Brick Breaker",
    "caro": "Caro",
    "flappy_bird": "Flappy Bird",
    "snake": "Snake",
    "tank_battle": "Tank Battle",
}
LANGUAGES = {"cpp": "C++", "java": "Java", "python": "Python"}
METHOD_LABELS = {
    "codeip": "CodeIP",
    "ewd": "EWD",
    "stone": "STONE",
    "sweet": "SWEET",
    "waterfall": "Waterfall",
    "wllm": "WLLM",
}
STYLES = {
    "Pass": {"marker": "o", "color": "#2A9D8F", "label": "Pass"},
    "BE": {"marker": "^", "color": "#D36B5F", "label": "BE (Build Error)"},
    "TE": {"marker": "x", "color": "#6F7782", "label": "TE (Test Error)"},
    "RE": {"marker": "s", "color": "#8C78B8", "label": "RE (Runtime Error)"},
    "Unknown": {"marker": "D", "color": "#333333", "label": "Unknown"},
}
AVERAGE_COLOR = "#1F5F57"


def configure_typography():
    """Use Times New Roman for all figure text, with a metric-compatible fallback.

    Times New Roman is preferred whenever it is installed in the rendering
    environment. Tinos is used only as a metric-compatible fallback so the
    script remains reproducible on Linux systems without the proprietary font.
    """
    available = {font.name for font in font_manager.fontManager.ttflist}
    font_name = "Times New Roman" if "Times New Roman" in available else "Tinos"
    if font_name not in available:
        font_name = "DejaVu Serif"

    plt.rcParams.update({
        "font.family": font_name,
        "font.size": 11.5,
        "axes.titlesize": 16.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 12.5,
        "axes.labelweight": "normal",
        "xtick.labelsize": 10.5,
        "ytick.labelsize": 10.5,
        "legend.fontsize": 10.0,
        "legend.title_fontsize": 10.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.unicode_minus": False,
    })
    return font_name


def main():
    package_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Plot one result figure per watermark method and language.")
    parser.add_argument("--input", type=Path, default=package_root / "data" / "watermark_points.csv")
    parser.add_argument("--output", type=Path, default=Path.cwd() / "derived" / "figures")
    parser.add_argument("--format", choices=("png", "pdf"), default="png")
    args = parser.parse_args()

    configure_typography()

    with args.input.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grouped = defaultdict(list)
    for row in rows:
        row["strength"] = float(row["strength"])
        grouped[(row["watermark_method"], row["language"])].append(row)

    args.output.mkdir(parents=True, exist_ok=True)
    methods = sorted({row["watermark_method"] for row in rows})
    for method in methods:
        for language in LANGUAGES:
            method_rows = grouped[(method, language)]
            plot_method_language(method, language, method_rows, args.output, args.format)


def plot_method_language(method, language, method_rows, output_dir, output_format):
    figure, axis = plt.subplots(figsize=(10.8, 6.2))
    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")
    axis.set_axisbelow(True)

    used_categories = set()
    averages_x = []
    averages_y = []
    project_labels = []

    for project_index, project in enumerate(PROJECTS):
        if project_index % 2 == 0:
            axis.axvspan(project_index - 0.5, project_index + 0.5, color="#F7F7F7", zorder=-5)

        project_rows = [
            row for row in method_rows
            if row["project"] == project and row["category"] in STYLES
        ]
        run_keys = sorted({(row["seed_group"], row["method_config"]) for row in project_rows})
        if len(run_keys) <= 1:
            offsets = [0.0] * len(run_keys)
        else:
            offsets = [-0.28 + index * 0.56 / (len(run_keys) - 1) for index in range(len(run_keys))]
        run_offsets = dict(zip(run_keys, offsets))
        trajectory_word = "trajectory" if len(run_keys) == 1 else "trajectories"
        project_labels.append(
            f"{PROJECT_LABELS.get(project, project)}\n({len(run_keys)} {trajectory_word})"
        )

        for offset in offsets:
            axis.axvline(
                project_index + offset,
                color="#D5D5D5",
                linewidth=0.45,
                alpha=0.70,
                zorder=-1,
            )

        for category, style in STYLES.items():
            category_rows = [row for row in project_rows if row["category"] == category]
            if not category_rows:
                continue
            values = [row["strength"] for row in category_rows]
            positions = [
                project_index + run_offsets[(row["seed_group"], row["method_config"])]
                for row in category_rows
            ]
            scatter_options = {
                "marker": style["marker"],
                "color": style["color"],
                "s": 28 if style["marker"] != "x" else 24,
                "linewidths": 0.65,
                "alpha": 0.82,
                "label": style["label"] if category not in used_categories else None,
                "zorder": 3,
            }
            if style["marker"] != "x":
                scatter_options["edgecolors"] = "#4D4D4D"
            axis.scatter(positions, values, **scatter_options)
            used_categories.add(category)

        pass_values = [row["strength"] for row in project_rows if row["category"] == "Pass"]
        if pass_values:
            averages_x.append(project_index)
            averages_y.append(sum(pass_values) / len(pass_values))

    if averages_x:
        axis.plot(
            averages_x,
            averages_y,
            color=AVERAGE_COLOR,
            linewidth=2.15,
            marker="D",
            markersize=5.5,
            markerfacecolor="white",
            markeredgewidth=1.25,
            label="Avg Pass strength",
            zorder=5,
        )

    method_label = METHOD_LABELS.get(method, method.upper())
    language_label = LANGUAGES.get(language, language.upper())
    axis.set_title(
        f"{method_label} Results for {language_label} - Pooled Across Evaluated Trajectories",
        fontsize=16.5,
        fontweight="bold",
        pad=14,
    )
    axis.set_xlabel("Project (evaluated trajectories separated horizontally)", labelpad=10)
    axis.set_ylabel("Watermark Strength (δ)", labelpad=9)
    axis.set_xticks(range(len(PROJECTS)), project_labels, rotation=17, ha="right", rotation_mode="anchor")
    axis.set_xlim(-0.5, len(PROJECTS) - 0.5)
    axis.set_ylim(bottom=0)
    axis.margins(y=0.05)

    axis.grid(axis="y", linestyle="--", linewidth=0.65, color="#A9A9A9", alpha=0.35)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_color("#666666")
    axis.spines["bottom"].set_color("#666666")
    axis.spines["left"].set_linewidth(0.8)
    axis.spines["bottom"].set_linewidth(0.8)
    axis.tick_params(axis="both", colors="#333333", width=0.7)

    legend_handles = []
    for category, style in STYLES.items():
        if category not in used_categories:
            continue
        marker_face = "none" if style["marker"] == "x" else style["color"]
        legend_handles.append(Line2D(
            [0], [0],
            linestyle="none",
            marker=style["marker"],
            markersize=6.5,
            markerfacecolor=marker_face,
            markeredgecolor="#4D4D4D" if style["marker"] != "x" else style["color"],
            color=style["color"],
            label=style["label"],
        ))
    if averages_x:
        legend_handles.append(Line2D(
            [0], [0],
            color=AVERAGE_COLOR,
            linewidth=2.0,
            marker="D",
            markersize=5.5,
            markerfacecolor="white",
            markeredgewidth=1.2,
            label="Avg Pass strength",
        ))

    legend = axis.legend(
        handles=legend_handles,
        title="Test Results",
        bbox_to_anchor=(1.015, 1.0),
        loc="upper left",
        borderaxespad=0,
        frameon=True,
        fancybox=False,
        framealpha=0.96,
        edgecolor="#CCCCCC",
        facecolor="white",
        borderpad=0.7,
        labelspacing=0.45,
        handletextpad=0.6,
    )
    legend.get_title().set_fontweight("bold")

    figure.tight_layout(rect=(0.02, 0.02, 0.83, 0.98))
    save_kwargs = {
        "dpi": 300,
        "bbox_inches": "tight",
        "pad_inches": 0.08,
        "facecolor": "white",
    }
    if output_format == "pdf":
        source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
        release_time = (
            datetime.fromtimestamp(int(source_date_epoch), timezone.utc)
            if source_date_epoch
            else datetime.fromtimestamp(Path(__file__).stat().st_mtime, timezone.utc)
        )
        save_kwargs["metadata"] = {
            "Title": f"{method_label} results for {language_label}",
            "Creator": "Applicability/scripts/plot_results.py",
            "CreationDate": release_time,
            "ModDate": release_time,
        }
    figure.savefig(output_dir / f"{method}_{language}_results.{output_format}", **save_kwargs)
    plt.close(figure)


if __name__ == "__main__":
    main()
