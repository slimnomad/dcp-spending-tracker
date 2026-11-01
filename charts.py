import os
from datetime import timedelta
from pathlib import Path

from tracker import ROOT, category_summary, day_type_summary, weekly_summary, DB_FILE

cache_folder = ROOT / ".cache"
cache_folder.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(cache_folder / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(cache_folder))

import matplotlib
matplotlib.use("Agg")  # Save PNG files without requiring a desktop window.
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

def generate_charts(frame, folder=None, db_file=DB_FILE):
    if frame.empty:
        raise ValueError("There are no spending records to plot.")
    folder = Path(folder) if folder else ROOT / "images"
    folder.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.titlesize": 15, "axes.titleweight": "bold",
                         "axes.spines.top": False, "axes.spines.right": False})
    sources = ", ".join(sorted(frame["data_source"].unique()))
    note = "Data source: " + sources + ". Simulated means invented example data."
    files = []

    def save(figure, name):
        figure.text(0.08, 0.025, note, fontsize=8, color="#475569")
        figure.tight_layout(rect=(0.02, 0.07, 0.98, 0.98))
        path = folder / name
        figure.savefig(path, dpi=170, facecolor="white")
        plt.close(figure)
        files.append(path)

    figure, axis = plt.subplots(figsize=(9, 4.6))
    axis.plot(frame["date"], frame["total_eur"], color="#2563EB", marker="o", markersize=4, linewidth=2)
    axis.set(title="Daily spending", xlabel="Date", ylabel="Spending (EUR)")
    axis.set_ylim(bottom=0)
    if len(frame) == 1:
        day = frame["date"].iloc[0]
        axis.set_xlim(day - timedelta(days=1), day + timedelta(days=1))
        axis.set_xticks([day])
    else:
        axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=8))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axis.grid(axis="y", alpha=0.2)
    save(figure, "daily_spending.png")

    categories = category_summary(frame)
    figure, axis = plt.subplots(figsize=(9, 4.6))
    bars = axis.bar(categories["category"], categories["total_eur"],
                    color=["#2563EB", "#0F766E", "#D97706"], width=0.55)
    axis.bar_label(bars, labels=[f"EUR {value:.2f}" for value in categories["total_eur"]], padding=5)
    axis.set(title="Spending by category", ylabel="Total spending (EUR)")
    axis.set_ylim(0, max(float(categories["total_eur"].max()) * 1.2, 1))
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    save(figure, "category_spending.png")

    comparison = day_type_summary(db_file)
    figure, axis = plt.subplots(figsize=(9, 4.6))
    labels = [f"{row.day_type}\n{row.recorded_days} recorded days" for row in comparison.itertuples()]
    bars = axis.bar(labels, comparison["average_eur"], color="#0F766E", width=0.45)
    axis.bar_label(bars, labels=[f"EUR {value:.2f}" for value in comparison["average_eur"]], padding=5)
    axis.set(title="Average spending on weekdays and weekends", ylabel="Average per recorded day (EUR)")
    axis.set_ylim(0, max(float(comparison["average_eur"].max()) * 1.25, 1))
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    save(figure, "weekday_weekend.png")

    weekly = weekly_summary(frame)
    figure, axis = plt.subplots(figsize=(9, 4.6))
    labels = weekly["week_start"].dt.strftime("%d %b")
    colors = ["#2563EB" if complete else "#94A3B8" for complete in weekly["complete_week"]]
    bars = axis.bar(labels, weekly["total_eur"], color=colors, width=0.6)
    axis.bar_label(bars, labels=[f"EUR {row.total_eur:.2f}\n{row.recorded_days} days" for row in weekly.itertuples()], padding=5, fontsize=9)
    axis.set(title="Weekly spending and coverage", xlabel="Week starting Monday", ylabel="Total spending (EUR)")
    axis.set_ylim(0, max(float(weekly["total_eur"].max()) * 1.3, 1))
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    axis.text(0.99, 0.98, "Grey bars are incomplete calendar weeks", transform=axis.transAxes,
              ha="right", va="top", fontsize=8, color="#475569")
    save(figure, "weekly_spending.png")
    return files
