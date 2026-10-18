"""Professional in-app help and the actual computational method.

This is shown by a visible HELP button and F1, not hidden as dozens of Excel
instructions sheets. Equations deliberately distinguish project screening
assumptions, cached source workbook results and genuine design calculations.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import webbrowser


TOPICS=[
("Start here", """CPT ENGINEERING STUDIO — WORKFLOW

1. Import one or more GEF/GFF numerical soundings (preferred) or compatible vector CPT PDFs.
2. Check calculation assumptions: soil unit weight, groundwater depth, source cone area ratio and PRE/POST stage.
3. Click START ANALYSIS. Results, charts, and the single consolidated Excel workbook use the same project-level CPT selection.
4. Open SITE MAP and choose Risk screening plan. Set WATCH and HIGH thickness screening thresholds, click pins or ALL HIGH CPTs. Every high-scoring point is selectable.
5. OPEN INTERACTIVE 3D GEOLOGY opens a self-contained OFFLINE HTML in your browser: rotate, zoom, show/hide screening layers and inferred wedges.
6. Investigate all REVIEWs in QA & REVIEW. A REVIEW must not be replaced with zero, and an UNKNOWN sensor interval must never be assumed clean sand or silt.
7. Use FOUNDATIONS and PRE / POST to inspect externally supplied engineering results and paired changes. Accept/reject design requires project-approved criteria.

Outputs: one CPT summary Excel with complete point measurements, all layers, a site plan/3D snapshot, provenance, QA and optional foundation/comparison worksheets, plus individual CPT PDFs when enabled.

Keyboard: Ctrl+O files; Ctrl+Shift+O folder; Ctrl+R analyze; Ctrl+E latest Excel; Ctrl+M maps; Ctrl+Q QA; F1 help.
"""),
("CPT equations", """CALCULATION METHOD — RAW NUMERICAL GEF/GFF

All depths are corrected depths below ground level (BGL) where available.
Source units: qc and u2 in MPa; fs in MPa; stress quantities in kPa.

Corrected tip resistance:
    qt (MPa) = qc (MPa) + u2 (MPa) × (1 − a)
    a = net cone area ratio, read from the raw CPT header when present.
    Do NOT substitute the original Excel default a=0.80 for a raw file that explicitly reports a different ratio.

Total vertical overburden:
    sigma_v0 (kPa) = gamma_soil (kN/m³) × z (m)

Hydrostatic groundwater:
    u0 (kPa) = gamma_w × max(z − groundwater_depth_BGL, 0)
    gamma_w = 9.81 kN/m³
    sigma'_v0 = max(sigma_v0 − u0, 1 kPa)

Net cone resistance:
    qnet = 1000 × qt − sigma_v0
    Fr (%) = 100 × (1000 × fs) / qnet  (only where fs>0 and qnet>0)

Iterated normalized penetration resistance:
    Qtn = (qnet / Pa) × (Pa / sigma'_v0)^n
    Pa = 100 kPa
    Ic = sqrt[(3.47 − log10 Qtn)^2 + (log10 Fr + 1.22)^2]
    n = clip[0.381 × Ic + 0.05 × (sigma'_v0 / Pa) − 0.15, 0, 1]

This is Robertson-style CPT soil-behavior classification. The project screening threshold is Ic ≥ 2.60 (configuration subject to accepted engineering criteria). It is NOT a laboratory grain-size / USCS determination.

Source XLSB cache and numerical Ic are DIFFERENT quantities: the source Combined CPTs column labelled 'Ic' holds integer SBT zone codes 1–9, NOT the continuous Ic index.

The original Excel's saved groundwater depth was 2.0 m and area ratio 0.80, with 'Above/Below' settings in centimeters. Those source settings are not universally correct for each raw sounding. PRE/POST 3/10-sample means require formula-order comparison before asserting exact XLSB parity.
"""),
("Layer boundaries & QA", """SOIL-LAYER OBSERVATION & VALIDATION

* The chosen project screening rule detects persistent depth intervals above Ic ≥ 2.60; it is not a direct soil-type proof.
* Brief excursions below the minimum sustained thickness remain visible in QA.
* fs=0 or missing fs/qc/u2 can make Fr, Qtn or Ic undefined. Such intervals are UNKNOWN, not observed sand/silt.
* Interpolate threshold crossings only between adjacent VALID observations with adequate depth spacing. Do not extrapolate to an arbitrary report plot limit.
* Preserve full raw unrounded depth bounds (start, end, thickness); report precision is distinct.
* For all-layer analysis: cumulative qualifying thickness = sum(end−start) over ALL qualifying intervals.
* Maximum individual layer = max(end−start). Several CPTs can share the same maximum; the app does not discard ties.
* Legacy quick sheet: sand before selected silt is the upper PROJECT interval, not the sum of all laboratory-confirmed sand layers.
* REVIEW: insufficient data, conflicting revisions, ambiguous thin boundary or source/calculation disagreement. Inspect the source and accepted engineering judgement; do not force a numerical result simply to remove REVIEW.

For the original XLSB, the cached zone series may be screened separately by source SBT groups. That screening is a reference output and is not automatically identical to a new numeric Ic threshold calculation.
"""),
("2D site plan & screening", """2D GEOTECHNICAL SITE PLAN

Pins show surveyed (Easting, Northing) coordinates, not arbitrary order along a spreadsheet row. Import SITE LIMIT to draw the approved survey boundary. The original coordinate reference system must be checked before using a geographic/satellite basemap.

Observed CPT values:
  LOW: below the chosen watch thickness;
  WATCH: at or above the chosen watch thickness;
  HIGH: at or above the chosen high thickness;
  REVIEW: unavailable, ambiguous, invalid or unapproved source observation.

WATCH/HIGH are screening priorities ONLY, not design PASS/FAIL or proof of ground-improvement failure.

Optional background surface:
  local linear triangulated interpolation using measured screening thickness;
  only triangles supported by three independent surveyed CPTs;
  triangles spanning sparse gaps are masked;
  no extrapolation outside CPT convex hull or the approved site boundary;
  interpolate ONLY confirmed measurable values; keep REVIEW points excluded.

Click any point to inspect its CPT chart. ALL HIGH CPTs lists every qualifying location even when plot labels would overlap. Native Matplotlib toolbar supports pan, zoom, home and export PNG. In 3D the browser handles mouse-wheel zoom and drag rotation.
"""),
("3D geology & uncertainty", """3D SUBSURFACE MODEL

The 3D viewer uses the actual Easting/Northing and ground elevation RL of each sounding, with vertical zones at their corrected depths BGL. The independent numerical data at CPTs are shown as observed column intervals.

TRANSPARENT WEDGES / FENCE-TYPE INTERPRETATION:
  1. At least three neighboring valid CPTs are required.
  2. Each must have an observed qualifying interval.
  3. Intervals must overlap in vertical elevation enough to support comparison.
  4. No wedge may cross a sparse horizontal gap or leave the surveyed triangulated region.
  5. Each wedge remains transparently labeled INTERPRETED / UNCERTAIN.

The inferred body is NOT a proven continuous lithological unit. No assumption is made about properties between sparse points, deep unmeasured strata, fines percentage or ground-improvement acceptance. A geological solid model certified for design would additionally require borehole/sample logs, site geology and calibration. 

Controls: rotate with mouse drag, pan using Plotly toolbar, zoom with wheel, click legends to hide/show observed lines or inferred solids, reset camera or switch plan/isometric views. HTML works offline with no external scripts or account.
"""),
("Raft / isolated foundations", """FOOTING AND LIQUEFACTION VALIDATION

The app can IMPORT original XLSB/XLSX saved foundation results, map settlements/minimum factors of safety and compare them with EXPLICIT engineer-approved limits. It does NOT independently recompute settlement or factor of safety by simply inspecting Ic or silt thickness.

Examples of checks ONLY if project limits and underlying reference calculations are accepted:
  Settlement check = PASS if imported settlement_mm ≤ allowable_settlement_mm
  FOS check = PASS if imported minimum_FOS ≥ engineer_required_minimum_FOS
  If either value or limit missing: NOT ASSESSED.

Source example inputs (not universal design constants):
  Reference raft 50×60 m at 100 kPa; allowable settlement 60 mm
  Reference isolated 3×3 m at 150 kPa; allowable settlement 40 mm
  Source liquefaction minimum FOS ≈ 1.25 target; magnitude 6, PGA 0.078g

The input workbook/VBA underlying settlement, bearing capacity and liquefaction equations require engineering model-parity approval before native designs can claim exact equivalence.
"""),
("PRE / POST comparison", """GROUND IMPROVEMENT COMPARISON

Match CPT references and surveyed locations. If identifiers changed, optional coordinate-only pairing is available, but all ambiguous matches require review.

For any comparable result:
   delta = POST − PRE
   percentage = 100×(POST−PRE)/PRE  only when PRE≠0

For raw depth profiles: interpolate PRE and POST only within overlapping measured depths and between adjacent valid sensor readings, not across gaps. Use common smoothing for a fair numerical comparison. Original source PRE and POST rolling windows can be displayed separately (PRE 3, POST 10 samples), but smoothing differences may mimic apparent improvement.

Interpretation caution:
  Increased qc may indicate stronger penetration response, but must be reviewed against source calibration, stress, depth and design target.
  Reduced Ic-defined 'silt' after treatment does NOT mean fines physically disappeared.
  The comparison workbook reports unmatched, ambiguous and unavailable metrics.
"""),
("Excel / PDF / reliability", """DELIVERABLES & RUNTIME RELIABILITY

The project produces ONE Excel workbook for the batch. It contains a clean summary, 5-column CPT Analysis, Full Analysis, all soil behavior layers, full numerical measurements, source QA, plan/3D embedded visuals, and optional foundation/reference/comparison when those files are supplied.

There are no instructions-only Excel sheets. In this HELP dialog, you can review every calculation equation and threshold.

PDFs:
  Compatible original CPT PDF report pages stay visually unchanged; a complete analysis appendix follows them.
  A raw-only PDF is a reference-like report; an installed Microsoft Excel can optionally export the original workbook's own chart layout when input and source workbook are compatible.
  Unrecorded values are labelled N/A or UNKNOWN rather than empty.

Safeguards:
  GEF/GFF preference over graphical PDF where numeric data are available; revision/source conflicts → REVIEW.
  Independent batch jobs should never crash the window; unavailable maps/3D should show an explanatory error.
  No automatic correction of erroneous coordinates.
  Large-batch work can consume RAM. Excel's 1,048,576-row worksheet limit cannot be exceeded or silently truncate records.

A passing software test suite validates implemented code paths, not geotechnical design certification or formula parity.
"""),
]


def show_help(parent):
    window=tk.Toplevel(parent)
    window.title("CPT Engineering Studio — Guide & Calculation Equations")
    window.geometry("1080x750")
    window.minsize(790,560)
    window.transient(parent)
    container=tk.Frame(window,bg="#f5f8fb")
    container.pack(fill="both",expand=True,padx=14,pady=14)
    tk.Label(container,text="Engineering Guide & Calculation Reference",
             font=("Segoe UI Semibold",18),fg="#183550",bg="#f5f8fb").pack(anchor="w")
    tk.Label(container,text="Search calculations, layer interpretations, 3D uncertainty, maps and deliverables. "
             "Project settings override example values.",font=("Segoe UI",10),
             fg="#58758b",bg="#f5f8fb").pack(anchor="w",pady=(3,12))
    search=tk.Frame(container,bg="#f5f8fb");search.pack(fill="x",pady=(0,9))
    tk.Label(search,text="SEARCH",fg="#41576a",bg="#f5f8fb",
             font=("Segoe UI Semibold",9)).pack(side="left",padx=(0,8))
    value=tk.StringVar()
    field=ttk.Entry(search,textvariable=value,width=50)
    field.pack(side="left",fill="x",expand=True)
    notebook=ttk.Notebook(container)
    notebook.pack(fill="both",expand=True)
    fields=[]
    for title,content in TOPICS:
        frame=ttk.Frame(notebook)
        notebook.add(frame,text="  "+title+"  ")
        text=tk.Text(frame,wrap="word",font=("Consolas",10),bg="white",fg="#183146",
              borderwidth=0,padx=16,pady=15,undo=False)
        scrollbar=ttk.Scrollbar(frame,orient="vertical",command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left",fill="both",expand=True)
        scrollbar.pack(side="right",fill="y")
        text.insert("1.0",content)
        text.configure(state="disabled")
        fields.append(text)
    status=tk.StringVar(value="F1 reopens this guide · values are source-aware, not design approvals")
    tk.Label(container,textvariable=status,bg="#f5f8fb",fg="#607184",
             anchor="w",font=("Segoe UI",9)).pack(fill="x",pady=(8,0))
    def find(_event=None):
        word=value.get().strip().lower()
        if not word:
            status.set("Enter a word or equation symbol to search the engineering guide.")
            return
        matches=[]
        for idx,(name,content) in enumerate(TOPICS):
            if word in content.lower() or word in name.lower():
                matches.append(idx)
        if matches:
            notebook.select(matches[0])
            status.set(f"Found in {len(matches)} section(s): "+
                       ", ".join(TOPICS[i][0] for i in matches))
        else:status.set("No matching sections. Try 'Ic', 'Fr', 'FOS', '3D', 'groundwater' or 'Review'.")
    field.bind("<Return>",find)
    ttk.Button(search,text="FIND",command=find).pack(side="left",padx=9)
    ttk.Button(search,text="CLOSE",command=window.destroy).pack(side="right")
    field.focus_set()
    return window
