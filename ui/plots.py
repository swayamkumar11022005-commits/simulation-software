"""Dark-themed matplotlib figures for each analysis result (no pyplot / plt.show)."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

BG = "#0a0e1a"
PANEL = "#0f1526"
GRID = "#1e2a47"
TEXT = "#c7d2e8"
PALETTE = ["#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#fbbf24", "#fb7185", "#60a5fa", "#fb923c"]


def _style(ax, title, xlabel, ylabel):
    ax.set_facecolor(PANEL)
    ax.set_title(title, color="#ffffff", fontsize=13, fontweight="bold", loc="left", pad=12)
    ax.set_xlabel(xlabel, color=TEXT)
    ax.set_ylabel(ylabel, color=TEXT)
    ax.tick_params(colors=TEXT, labelsize=9)
    ax.grid(True, color=GRID, linestyle="--", linewidth=0.7, which="both")
    for s in ax.spines.values():
        s.set_color(GRID)


def _legend(ax):
    if ax.get_legend_handles_labels()[0]:
        leg = ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=9, framealpha=0.95)
        leg.get_frame().set_linewidth(0.8)


def _line(ax, x, y, i, label, **kw):
    c = PALETTE[i % len(PALETTE)]
    ax.plot(x, y, color=c, linewidth=2.2, label=label, **kw)
    ax.fill_between(x, y, 0, color=c, alpha=0.06) if kw.get("fill") else None


def plot_result(res: dict, nodes: list[str]) -> Figure:
    kind = res["kind"]
    if kind == "transient":
        fig = Figure(figsize=(9, 4.6), facecolor=BG)
        ax = fig.subplots()
        t = res["times"] * 1000.0
        for i, n in enumerate(nodes):
            if f"V({n})" in res["node_voltages"]:
                ax.plot(t, res["node_voltages"][f"V({n})"], color=PALETTE[i % 8], linewidth=2.2, label=f"V({n})")
        _style(ax, "Transient response", "Time (ms)", "Voltage (V)")
        ax.axhline(0, color="#3a4b73", linewidth=1)
        _legend(ax)
    elif kind == "ac_sweep":
        fig = Figure(figsize=(9, 6), facecolor=BG)
        a1, a2 = fig.subplots(2, 1, sharex=True)
        f = res["frequencies"]
        for i, n in enumerate(nodes):
            k = f"V({n})"
            if k in res["magnitude_db"]:
                a1.semilogx(f, res["magnitude_db"][k], color=PALETTE[i % 8], linewidth=2.2, label=k)
                a2.semilogx(f, res["phase_deg"][k], color=PALETTE[i % 8], linewidth=2.2, label=k)
        _style(a1, "Bode plot", "", "Magnitude (dB)")
        _style(a2, "", "Frequency (Hz)", "Phase (deg)")
        _legend(a1)
        fig.tight_layout()
        return fig
    elif kind == "dc_sweep":
        fig = Figure(figsize=(9, 4.6), facecolor=BG)
        ax = fig.subplots()
        x = res["sweep"]
        for i, n in enumerate(nodes):
            if f"V({n})" in res["node_voltages"]:
                ax.plot(x, res["node_voltages"][f"V({n})"], color=PALETTE[i % 8], linewidth=2.2, label=f"V({n})")
        _style(ax, f"DC sweep of {res['source']}", f"{res['source']} (V)", "Node voltage (V)")
        ax.axhline(0, color="#3a4b73", linewidth=1)
        ax.axvline(0, color="#3a4b73", linewidth=1)
        _legend(ax)
    else:
        raise ValueError(f"No plot for analysis kind {kind!r}")
    fig.tight_layout()
    return fig


def plot_iv(res: dict) -> Figure:
    """Source current vs swept voltage - the I-V characteristic of everything the source drives."""
    fig = Figure(figsize=(9, 4.2), facecolor=BG)
    ax = fig.subplots()
    x, y = res["sweep"], res["source_current"]
    ax.plot(x, y * 1000.0, color="#fbbf24", linewidth=2.4, label=f"I({res['source']})")
    ax.fill_between(x, y * 1000.0, 0, color="#fbbf24", alpha=0.08)
    _style(ax, f"I-V characteristic seen by {res['source']}", f"{res['source']} (V)", "Current (mA)")
    ax.axhline(0, color="#3a4b73", linewidth=1)
    ax.axvline(0, color="#3a4b73", linewidth=1)
    _legend(ax)
    fig.tight_layout()
    return fig


def plot_dc_op(res: dict) -> Figure:
    """Bar chart of node voltages."""
    fig = Figure(figsize=(9, 3.8), facecolor=BG)
    ax = fig.subplots()
    names = list(res["node_voltages"].keys())
    vals = [res["node_voltages"][n] for n in names]
    colors = [PALETTE[i % 8] for i in range(len(names))]
    bars = ax.bar(names, vals, color=colors, width=0.55)
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:.4g} V", (b.get_x() + b.get_width() / 2, v), ha="center",
                    va="bottom" if v >= 0 else "top", color="#ffffff", fontsize=9,
                    xytext=(0, 4 if v >= 0 else -4), textcoords="offset points")
    _style(ax, "DC operating point", "", "Voltage (V)")
    ax.axhline(0, color="#3a4b73", linewidth=1)
    ax.margins(y=0.2)
    fig.tight_layout()
    return fig
