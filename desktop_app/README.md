# CPT Engineering Studio — Windows desktop

**Status: engineering upgrade under validation.** A successful automated build does NOT mean the original 40 MB Excel/VBA calculation model, foundation design equations, USCS classification or PDF print fidelity have been independently signed off.

See [Engineering Implementation Master Plan](../docs/ENGINEERING_IMPLEMENTATION_MASTER_PLAN.md) and [Validation Matrix](../docs/ENGINEERING_VALIDATION_MATRIX.md).

## Supported inputs
- Raw GEF/GFF (numerical corrected depth, qc, fs, u2 where present).
- Project-template PDF (native vector Ic); unsupported/raster PDFs require review.
- Generated five-column CPT Analysis XLSX, legacy Raft Summary / Isolated Summary XLSX for reference and comparison.
- Project Site Limit worksheet for boundary overlay.

## UI workspaces
Setup / Results / Charts / **Soil Layers** / **Site Map** / **Foundations** / **Pre / Post**.

**Soil Layers** — full-depth Ic curves, raw vs PRE window 3 vs POST window 10, all inferred SBT intervals, persistent Ic>=2.60 screening, brief spikes and unknown sensor depth. The complete observed strata and QA appear in the Excel workbook.

**Site Map** — offline measured Easting/Northing points colored by observed maximum silt-screen thickness, cumulative thickness, first qualifying depth or test depth. Import source Site Limit polygon, save PNG. CRS must be verified before external basemap use; no arbitrary interpolated surfaces.

**Foundations** — load Raft/Isolated Summary XLSX for coordinate-mapped imported settlement and FOS values, labeled REFERENCE ONLY. Engineering equations and ACCEPT/PASS outcomes are NOT recalculated or certified pending source-workbook formula audit and project design inputs.

**Pre / Post** — choose two summaries, match CPT identities with survey-coordinate checks, compute metric delta / safe percent change (undefined at zero baseline), visualize increase/decrease bars or coordinate delta map, export comparison XLSX with unmatched and ambiguous QA.

## Engineering QA updates
- Silt is a **project Ic screening label**, not a laboratory USCS class.
- Raw last valid Ic record bounds *measured* silt. Terminal zero-fs or missing-data tail is UNKNOWN and is never silently extended to full CPT depth.
- A positive thin silt interval rounded to 0.00 m is REVIEW instead of fabricating a measured 0.10 m.
- Every valid behavior interval can be inspected and exported (including estimated sand-like / silt-like / clay-like classes), plus spikes and invalid gaps.
- Legacy first sheet retains terminal-silt convention pending reference Excel parity, with an explicit Methodology and QA sheet. Do not infer that the entire overlying column is pure sand.
- The previously quoted A1-292 6.20/0.20 conflicts with the user's Raft Summary B292 6.20/0.10. This MUST be reconciled by workbook equations and engineer approval; do not treat either as presently definitive.

## Excel outputs
Five-column quick CPT Analysis, Full Analysis, Detected Intervals, All Soil Layers, Layer Statistics, Summary, printable Charts, Source Audit, Methodology and QA, Processing Errors. A run also generates four offline measured-coordinate PNG maps under Charts.

Pre/Post comparison exports a separate file with Matched Changes, Matching QA and Summary.

## Report outputs
Raw GEF/GFF reference-like PDF report and analysis appendix. Native PDF input keeps every source PDF page unchanged and appends the result. Exact chart/print parity with the proprietary XLSB has NOT been established. Preserve and compare the reference PDF before approving a new report layout.

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
GitHub Actions runs unit/regression tests, smoke compilation, builds the Windows executable, uploads artifact and publishes release/CPT_Silt_Analyzer_Latest.zip **only on successful build and tests**. Manual engineering sign-off remains a separate release gate.
