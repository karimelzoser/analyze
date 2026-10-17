from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xlsxwriter

from cpt_core import CPTAnalysis

ZONE_BOUNDS = [0.0, 1.31, 2.05, 2.60, 2.95, 3.60, 5.00]
ZONE_NAMES = [
    "Gravelly sand to dense sand",
    "Clean to silty sand",
    "Silty sand to sandy silt",
    "Clayey silt to silty clay",
    "Silty clay to clay",
    "Organic soil - clay",
]
ZONE_COLORS = ["#ffd65a", "#f7b267", "#a8dadc", "#75c9c8", "#4f86c6", "#789262"]


def _finite_xy(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    return np.asarray(x)[m], np.asarray(y)[m]


def generate_pdf(analysis: CPTAnalysis, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(8.5, 11), constrained_layout=False)
    gs = fig.add_gridspec(
        nrows=20, ncols=12,
        left=0.065, right=0.97, top=0.955, bottom=0.05,
        hspace=1.1, wspace=1.0,
    )

    fig.text(0.065, 0.975, "CPT ANALYSIS REPORT", fontsize=14, weight="bold", va="top")
    fig.text(0.97, 0.975, analysis.reference, fontsize=11, weight="bold", ha="right", va="top")
    client = str(analysis.metadata.get("client") or "")
    project = str(analysis.metadata.get("project_name") or analysis.metadata.get("project_id") or "")
    fig.text(0.065, 0.953, f"Client: {client}", fontsize=8.5, va="top")
    fig.text(0.50, 0.953, f"Project: {project}", fontsize=8.5, va="top")

    ax_qc = fig.add_subplot(gs[1:11, 0:3])
    ax_fs = fig.add_subplot(gs[1:11, 3:6])
    ax_u2 = fig.add_subplot(gs[1:11, 6:8])
    ax_ic = fig.add_subplot(gs[1:11, 8:12])

    depth = analysis.depth
    ground_elev = analysis.metadata.get("ground_elevation")
    if isinstance(ground_elev, (int, float)):
        vertical = float(ground_elev) - depth
        vertical_label = "Level, m"
        top_level = max(10.0, math.ceil(float(ground_elev)))
        bottom_level = min(-10.0, math.floor(float(np.nanmin(vertical))))
    else:
        vertical = depth
        vertical_label = "Depth below ground (m)"
        top_level = 0.0
        bottom_level = max(1.0, math.ceil(float(np.nanmax(depth)) * 2) / 2)

    ax_qc.plot(analysis.qc, vertical, color="black", lw=1.0)
    ax_qc.set_title("Cone resistance, qc (MPa)", fontsize=8)
    ax_qc.set_xlabel("MPa", fontsize=7)
    ax_qc.set_ylabel(vertical_label, fontsize=7)

    ax_fs.plot(analysis.fs, vertical, color="#7b2cbf", lw=1.0)
    ax_fs.set_title("Sleeve friction, fs (MPa)", fontsize=8)
    ax_fs.set_xlabel("MPa", fontsize=7)

    ax_u2.plot(analysis.u2, vertical, color="#2a9d8f", lw=1.0)
    ax_u2.set_title("Pore pressure, u2 (MPa)", fontsize=8)
    ax_u2.set_xlabel("MPa", fontsize=7)

    for i, (lo, hi) in enumerate(zip(ZONE_BOUNDS[:-1], ZONE_BOUNDS[1:])):
        ax_ic.axvspan(lo, hi, color=ZONE_COLORS[i], alpha=0.88, lw=0)
    ic_plot = np.where((analysis.ic >= 0.0) & (analysis.ic <= 5.0), analysis.ic, np.nan)
    ax_ic.plot(ic_plot, vertical, color="black", lw=1.0, zorder=4)
    ax_ic.axvline(2.60, color="black", lw=0.8, ls="--", alpha=0.8)
    ax_ic.set_xlim(0.0, 5.0)
    ax_ic.set_title("Soil Behaviour Type Index, Ic", fontsize=8)
    ax_ic.set_xlabel("Ic", fontsize=7)

    for ax in (ax_qc, ax_fs, ax_u2, ax_ic):
        if isinstance(ground_elev, (int, float)):
            ax.set_ylim(bottom_level, top_level)
        else:
            ax.set_ylim(bottom_level, top_level)
            ax.invert_yaxis()
        ax.grid(True, which="major", lw=0.35, color="#d9d9d9")
        ax.tick_params(labelsize=6)

    if analysis.final_interval is not None:
        for ax in (ax_qc, ax_fs, ax_u2, ax_ic):
            if isinstance(ground_elev, (int, float)):
                y1 = float(ground_elev) - analysis.final_interval.start_raw
                y2 = float(ground_elev) - analysis.final_interval.end_raw
            else:
                y1 = analysis.final_interval.start_raw
                y2 = analysis.final_interval.end_raw
            ax.axhspan(
                min(y1, y2),
                max(y1, y2),
                color="#e63946", alpha=0.12, zorder=0,
            )
        text_y = (float(ground_elev) - analysis.final_interval.start_raw) if isinstance(ground_elev, (int, float)) else analysis.final_interval.start_raw
        ax_ic.text(
            4.9, text_y,
            f"Silt start {analysis.final_interval.start:.2f} m",
            ha="right", va="bottom", fontsize=6.5, weight="bold",
        )

    ax_sbt = fig.add_subplot(gs[12:18, 0:7])
    fx, qy = _finite_xy(analysis.fr, analysis.qtn)
    ic_f = analysis.ic[np.isfinite(analysis.fr) & np.isfinite(analysis.qtn)]
    bins = np.digitize(ic_f, ZONE_BOUNDS[1:-1], right=False)
    for i in range(6):
        m = bins == i
        if np.any(m):
            ax_sbt.scatter(fx[m], qy[m], s=6, alpha=0.65, color=ZONE_COLORS[i], label=ZONE_NAMES[i])
    ax_sbt.set_xscale("log")
    ax_sbt.set_yscale("log")
    ax_sbt.set_xlim(0.1, max(10, float(np.nanpercentile(fx, 99)) * 1.3 if len(fx) else 10))
    ax_sbt.set_ylim(1, max(1000, float(np.nanpercentile(qy, 99)) * 1.3 if len(qy) else 1000))
    ax_sbt.set_xlabel("Normalized Friction Ratio, Fr (%)", fontsize=7)
    ax_sbt.set_ylabel("Normalized Cone Resistance, Qtn", fontsize=7)
    ax_sbt.set_title("Normalized CPT Soil Behaviour", fontsize=8)
    ax_sbt.grid(True, which="both", lw=0.35, color="#dddddd")
    ax_sbt.tick_params(labelsize=6)
    ax_sbt.legend(fontsize=5.2, loc="best", frameon=True, ncol=2)

    ax_meta = fig.add_subplot(gs[12:18, 7:12])
    ax_meta.axis("off")
    md = analysis.metadata
    raw_date = str(md.get("file_date") or "")
    try:
        yy, mm, dd = [int(x.strip()) for x in raw_date.split(",")[:3]]
        import datetime as _dt
        date_display = _dt.date(yy, mm, dd).strftime("%d-%b-%Y")
    except Exception:
        date_display = raw_date
    rows = [
        ("CPT Reference", analysis.reference),
        ("Ground Elevation", f"{md.get('ground_elevation'):.2f} m" if isinstance(md.get('ground_elevation'), (int, float)) else ""),
        ("Easting", f"{md.get('easting'):.3f}" if isinstance(md.get('easting'), (int, float)) else ""),
        ("Northing", f"{md.get('northing'):.3f}" if isinstance(md.get('northing'), (int, float)) else ""),
        ("Cone ID", str(md.get("cone_id") or "")),
        ("Test Date", date_display),
        ("Test Depth", f"{float(np.nanmax(depth)):.2f} m"),
        ("Verification", analysis.status),
    ]
    if analysis.status == "NO SILT":
        rows += [("Silt start", "NO SILT"), ("Silt depth", "0.00 m")]
    elif analysis.final_interval is not None:
        rows += [
            ("Silt start", f"{analysis.final_interval.start:.2f} m"),
            ("Silt depth", f"{analysis.final_interval.thickness:.2f} m"),
        ]
    else:
        rows += [("Silt start", "REVIEW"), ("Silt depth", "-")]
    table = ax_meta.table(cellText=rows, colWidths=[0.43, 0.57], loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(6.8)
    table.scale(1.0, 1.35)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#bdbdbd")
        cell.set_linewidth(0.5)
        if c == 0:
            cell.set_facecolor("#eeeeee")
            cell.set_text_props(weight="bold")

    ax_note = fig.add_subplot(gs[18:20, :])
    ax_note.axis("off")
    if analysis.status == "NO SILT":
        summary = "SILT INTERPRETATION: NO SILT - no sustained qualifying Ic >= 2.60 interval detected."
    elif analysis.final_interval is not None:
        summary = (
            f"SILT INTERPRETATION: start {analysis.final_interval.start:.2f} m BGL; "
            f"thickness {analysis.final_interval.thickness:.2f} m. {analysis.verification_note}"
        )
    else:
        summary = f"SILT INTERPRETATION: REVIEW REQUIRED. {analysis.verification_note}"
    ax_note.text(0.0, 0.72, summary, fontsize=8, weight="bold", va="top", wrap=True)
    ax_note.text(
        0.0, 0.18,
        "Method: GEF raw qc/fs/u2 -> qt, Fr, Qtn and Robertson-style Ic; deepest sustained Ic >= 2.60 interval selected. "
        "Default unit weight 18 kN/m3 and groundwater at ground level are configurable in the desktop tool.",
        fontsize=6.2, va="bottom", wrap=True, color="#555555",
    )

    fig.savefig(output_path, format="pdf", dpi=180)
    plt.close(fig)
    return output_path


def export_excel(analyses: Iterable[CPTAnalysis], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    analyses = list(analyses)

    wb = xlsxwriter.Workbook(str(output_path))
    ws = wb.add_worksheet("CPT Analysis")

    header_fmt = wb.add_format({
        "bold": True, "font_color": "#FFC000", "bg_color": "#000000",
        "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True,
    })
    num_fmt = wb.add_format({"num_format": "0.00", "align": "center", "border": 1})
    int_fmt = wb.add_format({"align": "center", "border": 1})
    text_fmt = wb.add_format({"border": 1})
    center_text_fmt = wb.add_format({"align": "center", "border": 1})

    headers = ["SI.No", "CPT REFERENCE", "Silt start depth after (m)", "silt depth (m)"]
    for c, h in enumerate(headers):
        ws.write(0, c, h, header_fmt)
    ws.set_row(0, 32)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(1, len(analyses)), 3)
    ws.set_column(0, 0, 9)
    ws.set_column(1, 1, 28)
    ws.set_column(2, 2, 29)
    ws.set_column(3, 3, 17)

    for i, a in enumerate(analyses, start=1):
        ws.write_number(i, 0, i, int_fmt)
        ws.write(i, 1, a.reference, text_fmt)
        if a.status == "NO SILT":
            ws.write(i, 2, "NO SILT", center_text_fmt)
            ws.write_number(i, 3, 0.0, num_fmt)
        elif a.final_interval is not None:
            ws.write_number(i, 2, a.final_interval.start, num_fmt)
            ws.write_number(i, 3, a.final_interval.thickness, num_fmt)
        else:
            ws.write(i, 2, "REVIEW", center_text_fmt)
            ws.write_blank(i, 3, None, num_fmt)

    wb.close()
    return output_path
