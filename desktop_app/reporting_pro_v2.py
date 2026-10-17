from __future__ import annotations

"""Final reporting compatibility layer.

Keeps the professional reporting/Excel engine from reporting_pro, but replaces
only the normalized Qtn-Fr point rendering so the generated CPT PDF follows the
Terra Firma reference style more closely: numbered 1-9 background zones,
continuous sounding trace, very small square points, and soil-behaviour based
trace colours rather than arbitrary depth thirds.
"""

import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

import reporting_pro as _base

# Re-export the production API used by the desktop app.
analysis_record = _base.analysis_record
export_excel = _base.export_excel
sbtn_background = _base.sbtn_background

SBTN_COLORS = _base.SBTN_COLORS


def _zones_for_points(fr: np.ndarray, qtn: np.ndarray) -> np.ndarray:
    """Apply the same zone rules as the plotted 1-9 SBTn background."""
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


# Point/trace colours chosen to match the supplied Terra Firma chart visually.
# The colours are deliberately different from the filled zone colours because
# the reference report overlays a warm-to-magenta measurement trace.
_TRACE_COLORS = {
    1: "#d1495b",  # very soft/organic tail
    2: "#7b2f8e",
    3: "#a00078",  # purple/magenta lower-right trace
    4: "#b45f73",  # muted rose central cloud
    5: "#c86f7c",
    6: "#f05a28",  # orange-red sand trace
    7: "#ff5a1f",
    8: "#777777",
    9: "#666666",
}


def _plot_contiguous_zone_runs(ax, x, y, zones, zone_id, color):
    idx = np.flatnonzero(zones == zone_id)
    if not len(idx):
        return
    splits = np.flatnonzero(np.diff(idx) > 1) + 1
    for run in np.split(idx, splits):
        if len(run) >= 2:
            ax.plot(x[run], y[run], color=color, lw=0.75, alpha=0.95,
                    solid_capstyle="round", zorder=4)


def draw_sbtn(ax, a):
    fr, q, F, Q, _, background_zone = _base.sbtn_background()
    cmap = ListedColormap(SBTN_COLORS)
    norm = BoundaryNorm(np.arange(0.5, 10.5, 1), cmap.N)

    ax.pcolormesh(F, Q, background_zone, cmap=cmap, norm=norm,
                  shading="auto", rasterized=True)
    ax.contour(F, Q, background_zone, levels=np.arange(1.5, 9.5, 1),
               colors="black", linewidths=0.78)

    # Number placement follows the supplied project chart.
    for num, x, y in [
        (1, .30, 3.5), (2, 7.0, 1.8), (3, 3.0, 7.0),
        (4, 1.30, 15), (5, .60, 30), (6, .28, 90),
        (7, .18, 430), (8, 3.0, 450), (9, 6.0, 220),
    ]:
        ax.text(x, y, str(num), ha="center", va="center", fontsize=9,
                color="black", zorder=2)

    valid = (
        np.isfinite(a.fr) & np.isfinite(a.qtn) &
        (np.asarray(a.fr) > 0) & (np.asarray(a.qtn) > 0)
    )
    fx = np.asarray(a.fr, dtype=float)[valid]
    qy = np.asarray(a.qtn, dtype=float)[valid]

    if len(fx):
        zones = _zones_for_points(fx, qy)

        # Very thin neutral under-trace prevents visual gaps while preserving
        # the original sounding order.
        ax.plot(fx, qy, color="#666666", lw=0.28, alpha=0.50, zorder=3)

        # Overlay continuous sections in the reference trace colours.
        for z in range(1, 10):
            _plot_contiguous_zone_runs(ax, fx, qy, zones, z, _TRACE_COLORS[z])

        # Terra Firma-style small square measurements.  The points are coloured
        # by the actual SBTn region they occupy, not by arbitrary depth thirds.
        for z in range(1, 10):
            m = zones == z
            if np.any(m):
                ax.scatter(
                    fx[m], qy[m],
                    s=4.0, marker="s", linewidths=0,
                    color=_TRACE_COLORS[z], alpha=0.96, zorder=5,
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


# Patch only the renderer used by the existing professional report page.  This
# preserves all project metadata, PDF layout, Excel sheets and calculations.
_base.draw_sbtn = draw_sbtn


def generate_pdf(*args, **kwargs):
    return _base.generate_pdf(*args, **kwargs)


# Additional exports used by tests or advanced callers.
report_page = _base.report_page
analysis_page = getattr(_base, "analysis_page", None)
