from __future__ import annotations

"""Final reference-style PDF renderer refinement.

This module keeps the proven project-reference PDF layout from
``reporting_pdf_ref`` and changes only the normalized Qtn-Fr trace rendering.
The data and engineering calculations are untouched.
"""

import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

import reporting_pdf_ref as _base
from reporting_pro import SBTN_COLORS, sbtn_background


TRACE_COLORS = {
    1: "#d1495b",
    2: "#7b2f8e",
    3: "#a00078",
    4: "#b45f73",
    5: "#c86f7c",
    6: "#f05a28",
    7: "#ff5a1f",
    8: "#777777",
    9: "#666666",
}


def point_sbtn_zones(fr, qtn):
    """Return the 1-9 chart region occupied by every valid Qtn-Fr point."""
    F = np.asarray(fr, dtype=float)
    Q = np.asarray(qtn, dtype=float)
    ic = np.sqrt((3.47 - np.log10(Q)) ** 2 + (np.log10(F) + 1.22) ** 2)

    zone = np.full_like(ic, 7, dtype=int)
    zone[ic >= 1.31] = 6
    zone[ic >= 2.05] = 5
    zone[ic >= 2.60] = 4
    zone[ic >= 2.95] = 3
    zone[ic >= 3.60] = 2
    zone[Q < 12.0 * np.exp(-1.4 * F)] = 1

    denom = 0.005 * (F - 1.0) - 0.0003 * (F - 1.0) ** 2 - 0.002
    stiff = (denom > 0) & (Q > 1.0 / denom)
    zone[stiff & (F <= 4.5)] = 8
    zone[stiff & (F > 4.5)] = 9
    return zone


def _plot_runs(ax, x, y, zones, zone_id, color):
    idx = np.flatnonzero(zones == zone_id)
    if not len(idx):
        return
    split_at = np.flatnonzero(np.diff(idx) > 1) + 1
    for run in np.split(idx, split_at):
        if len(run) >= 2:
            ax.plot(
                x[run], y[run], color=color, lw=0.72, alpha=0.96,
                solid_capstyle="round", zorder=4,
            )


def draw_reference_sbtn(ax, a):
    """Render the normalized CPT chart in the visual language of the source PDF."""
    _fr, _q, F, Q, _ic, background_zone = sbtn_background(420)
    cmap = ListedColormap(SBTN_COLORS)
    norm = BoundaryNorm(np.arange(0.5, 10.5, 1), cmap.N)

    ax.pcolormesh(
        F, Q, background_zone, cmap=cmap, norm=norm,
        shading="auto", rasterized=True,
    )
    ax.contour(
        F, Q, background_zone,
        levels=np.arange(1.5, 9.5, 1),
        colors="black", linewidths=0.76,
    )

    for num, x, y in [
        (1, .30, 3.5), (2, 7.0, 1.8), (3, 3.0, 7.0),
        (4, 1.30, 15), (5, .60, 30), (6, .28, 90),
        (7, .18, 430), (8, 3.0, 450), (9, 6.0, 220),
    ]:
        ax.text(x, y, str(num), ha="center", va="center", fontsize=9, zorder=2)

    valid = (
        np.isfinite(a.fr) & np.isfinite(a.qtn) &
        (np.asarray(a.fr, dtype=float) > 0) &
        (np.asarray(a.qtn, dtype=float) > 0)
    )
    fx = np.asarray(a.fr, dtype=float)[valid]
    qy = np.asarray(a.qtn, dtype=float)[valid]

    if len(fx):
        zones = point_sbtn_zones(fx, qy)

        # Preserve the sounding sequence with a very light neutral backbone.
        ax.plot(fx, qy, color="#777777", lw=0.26, alpha=0.45, zorder=3)

        # Coloured connected runs reproduce the orange/rose/magenta traces in
        # the supplied Terra Firma chart while remaining tied to the actual
        # Qtn-Fr soil-behaviour region occupied by each measurement.
        for z in range(1, 10):
            _plot_runs(ax, fx, qy, zones, z, TRACE_COLORS[z])

        # The source uses very small square measurement marks.
        for z in range(1, 10):
            m = zones == z
            if np.any(m):
                ax.scatter(
                    fx[m], qy[m], s=4.0, marker="s", linewidths=0,
                    color=TRACE_COLORS[z], alpha=0.97, zorder=5,
                )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.1, 10)
    ax.set_ylim(1, 1000)
    ax.set_xticks([0.1, 1, 10])
    ax.set_xticklabels(["0.1", "1", "10"])
    ax.set_yticks([1, 10, 100, 1000])
    ax.set_yticklabels(["1", "10", "100", "1000"])
    ax.set_xlabel("Normalized Friction Ratio, Fr, %", fontsize=6)
    ax.set_ylabel("Normalized Cone Resistance Qtn", fontsize=6)
    ax.tick_params(labelsize=5.5, length=2.5, width=0.7)
    ax.grid(False)
    try:
        ax.set_box_aspect(1.0)
    except Exception:
        pass
    for sp in ax.spines.values():
        sp.set_linewidth(0.8)
        sp.set_color("black")


# report_page() in the base module resolves this symbol at runtime, so replacing
# it updates only the point plot and leaves the rest of the PDF unchanged.
_base.draw_reference_sbtn = draw_reference_sbtn

report_page = _base.report_page
from engineering_pdf_summary import engineering_analysis_page
_base.analysis_page = engineering_analysis_page
analysis_page = engineering_analysis_page


def generate_pdf(*args, **kwargs):
    return _base.generate_pdf(*args, **kwargs)
