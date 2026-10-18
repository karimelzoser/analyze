# CPT Engineering Studio — Windows desktop

**Status: engineering upgrade under validation.** A successful automated build does NOT mean the original 40 MB Excel/VBA calculation model, foundation design equations, USCS classification or PDF print fidelity have been independently signed off.

See [Engineering Implementation Master Plan](../docs/ENGINEERING_IMPLEMENTATION_MASTER_PLAN.md) and [Validation Matrix](../docs/ENGINEERING_VALIDATION_MATRIX.md).

## Supported inputs
- Raw GEF/GFF (numerical corrected depth, qc, fs, u2 where present).
- Project-template PDF (native vector Ic); unsupported/raster PDFs require review.
- Generated five-column CPT Analysis XLSX, legacy Raft Summary / Isolated Summary XLSX for reference and comparison.
- Project Site Limit worksheet for boundary overlay.

## UI workspaces
Setup / Results / Charts / **Soil Layers** / **Site Map** / **Foundations** / **Pre / Post** / **QA & Review**.

**Soil Layers** — two independent display views: a full-height Ic profile with all colored intervals, and a detailed table of every observed soil-behavior layer. Choose raw, PRE window 3, or POST window 10; UNKNOWN sensor readings remain visible. All depth intervals also appear in Excel.

**Site Map** — offline measured Easting/Northing points colored by observed maximum silt-screen thickness, cumulative thickness, first qualifying depth or test depth. Import source Site Limit polygon, save PNG. CRS must be verified before external basemap use; no arbitrary interpolated surfaces.

**Foundations** — load Raft/Isolated Summary XLSX for coordinate-mapped imported settlement and FOS values, labeled REFERENCE ONLY. Engineering equations and ACCEPT/PASS outcomes are NOT recalculated or certified pending source-workbook formula audit and project design inputs.

**Pre / Post** — choose two summaries, match CPT identities with survey-coordinate checks, compute metric delta / safe percent change (undefined at zero baseline), visualize increase/decrease bars or coordinate delta map, export comparison XLSX with unmatched and ambiguous QA.

**QA & Review** — searchable/filterable project exceptions with original-source opening, profile drilldown, source-model XLSB inventory, PDF visual-difference testing, QA CSV export and keyboard shortcuts. The output explicitly labels source conflicts and sensor dropout; the UI does not hide unverified intervals.

## Engineering QA updates
- Silt is a **project Ic screening label**, not a laboratory USCS class.
- Raw last valid Ic record bounds *measured* silt. Terminal zero-fs or missing-data tail is UNKNOWN and is never silently extended to full CPT depth.
- If versions of a nominal CPT disagree in accepted silt thickness, surveyed location or elevation, the final project CPT is **REVIEW** until reconciled. The audit preserves all physical sources.
- A positive thin silt interval rounded to 0.00 m is REVIEW instead of fabricating a measured 0.10 m.
- Every valid behavior interval can be inspected and exported (including estimated sand-like / silt-like / clay-like classes), plus spikes and invalid gaps.
- Legacy first sheet retains terminal-silt convention pending reference Excel parity, with an explicit Methodology and QA sheet. Do not infer that the entire overlying column is pure sand.
- The previously quoted A1-292 6.20/0.20 conflicts with the user's Raft Summary B292 6.20/0.10. This MUST be reconciled by workbook equations and engineer approval; do not treat either as presently definitive.

## Excel outputs
Five-column quick CPT Analysis, Full Analysis, Detected Intervals, All Soil Layers, Layer Statistics, Summary, printable Charts, Source Audit, Methodology and QA, Processing Errors. A run also generates four offline measured-coordinate PNG maps under Charts.

Pre/Post comparison exports a separate file with Matched Changes, Matching QA and Summary.

## Report outputs
Raw GEF/GFF reference-like PDF report and analysis appendix. When a GEF has a coordinate/elevation/date-verified official PDF sibling, the app **retains those original PDF report pages exactly** and appends a new analysis based on raw GEF; when no safely matching original PDF exists, it generates a reference-like CPT report. Native PDF input also preserves its original pages. Exact chart/print parity for generated raw-only reports with the proprietary XLSB has NOT been established. Preserve and compare the reference PDF before approving a new report layout.

## Engineering completion gates
1. Audit all relevant XLSB formulas, VBA, source design criteria, rolling mean order and sampled reference point results.
2. Verify the five engineer-annotated raw GEF soundings against the original workbook.
3. Verify full-layer classifications and sensor quality on multiple real examples and source PDF revisions.
4. Match site boundaries, coordinates, CRS and foundation acceptance criteria with approved project data.
5. Compare complete original reports page-by-page; test full interactive Windows UI and 400+ file batch.
6. Only then mark the engineering model as production approved.

## Local run
From desktop_app: install requirements.txt and run python app_modern_final.py.

## GitHub build
GitHub Actions runs regression tests, opens all 8 GUI workspaces, generates an end-to-end synthetic GEF → PDF/Excel/site-map report, captures all-tab screenshot artifacts, benchmarks a synthetic 400-sounding batch, then launches the frozen Windows EXE before publishing release/CPT_Silt_Analyzer_Latest.zip. The synthetic batch is a performance smoke, not proof of engineering accuracy on the confidential real project dataset. Release remains gated by successful automated tests. Manual engineering sign-off remains a separate release gate.
