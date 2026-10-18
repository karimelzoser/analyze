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

**Site Map** — zoomable/clickable surveyed site plan, area boundary, ALL HIGH CPT review list, configurable LOW/WATCH/HIGH screening thicknesses, and an optional locally bounded *interpretive* contour. **Depth slice plan** allows independently selecting a top and bottom depth BGL; every CPT must have sufficient valid observed/classified depth coverage (minimum 80%) or it is shown as REVIEW, never as clean sand. The offline interactive 3D viewer contains ALL observed screened layers, multiple vertically distinct uncertainty-bounded 3-CPT overlap prisms, and independently zoomable East-West and North-South measured CPT fence sections. No interpretation is extended across absent CPTs, far gaps, or known sensor dropout. The survey CRS must be confirmed before overlaying geographic/satellite basemaps.

**Foundations** — load Raft/Isolated Summary XLSX for coordinate-mapped imported settlement and FOS values, labeled REFERENCE ONLY. Engineering equations and ACCEPT/PASS outcomes are NOT recalculated or certified pending source-workbook formula audit and project design inputs.

**Pre / Post** — choose two summaries, match CPT identities with survey-coordinate checks, compute metric delta / safe percent change (undefined at zero baseline), visualize increase/decrease bars or coordinate delta map, export comparison XLSX with unmatched and ambiguous QA.

**QA & Review** — searchable/filterable project exceptions with original-source opening, profile drilldown, source-model XLSB inventory, PDF visual-difference testing, QA CSV export, **OPEN ERROR DIAGNOSTICS**, and keyboard shortcuts. The output explicitly labels source conflicts and sensor dropout; the UI does not hide unverified intervals.

## Recommended investigation and engineering methodology

The default screen thresholds in the plan (watch=0.10 m, high=0.30 m) prioritize detailed investigation; they are **not** engineering hazard, failure or ground improvement acceptance limits. Every displayed point is a measured surveyed CPT; optional shading is a limited 2D interpolation, not independent soil testing. The 3D viewer uses actual observed depths and CPT positions and infers continuity only where *all three* spatially proximate CPTs share **the same vertical screened interval**, including multiple distinct horizons.

Use **Site Map → Depth slice plan** for 2D screening within a particular depth interval; use **OPEN OFFLINE INTERACTIVE 3D SOIL MODEL** for 3D zoom/pan, toggle of observed vs inferred components, plus surveyed E-W and N-S fence sections. Inspect all points in the clickable **ALL HIGH CPTs** list; ties are not arbitrarily discarded.

For geotechnical ground modelling practice and sparse-data limitations, see:
- https://www.seequent.com/leapfrog-works-best-practice-building-a-geological-model/
- https://www.issmge.org/uploads/publications/132/133/ISFOG2025-376.pdf
- https://docs.pyvista.org/examples/00-load/create_tri_surface.html
- https://doi.org/10.1016/j.compgeo.2020.103681

## Reliability and output contract

The main desktop workflow writes **one consolidated project XLSX** with a concise dashboard, CPT analysis, full numeric measurements, every observed SBT layer, compact site maps (with embedded figures), and source QA. Foundation results and source-reference parity appear only when the relevant files are supplied; instructions and explanations are in the in-app HELP / F1 view, not dozens of redundant workbook tabs. Original CPT PDF pages are preserved when sourced from an approved matching report; report uncertainty is explicit.

A Windows UI exception is saved locally under `.cpt_engineering/diagnostics/` and reported in a dialog; the QA workspace provides an **OPEN ERROR DIAGNOSTICS** control. Worker failures are handled separately, and partial Excel output files are not treated as finished. GitHub CI gates packaging on numeric regressions, 400 synthetic CPTs, screenshot/GUI tests and direct launch of the packaged Windows executable.

Successful software tests do not establish that the private original Excel/VBA foundation equations, site-specific design limits, or every proprietary reference PDF has received independent geotechnical validation.

## Original Excel calculation and exact report workflow

This app now provides several distinct, auditable ways to use the ORIGINAL supplied calculation workbook without changing its formulas or leaking the private XLSB into GitHub:

1. **QA & Review → ANALYZE COMPLETE ORIGINAL XLSB PROJECT**: Select the original `.xlsb` file and an output folder. The app reads its saved BIN cache directly (no Excel required), extracts the project summary/settlement/FOS/coordinates and 1-9 SBT ZONE series, creates a five-column results sheet, all-layer intervals, full source-reference summary and **four project maps**. The saved source has 448 foundation rows and 447 unique CPT series. These are *saved reference outputs*; not independently recalculated.
2. **QA & Review → SET XLSB PARITY BASELINE**: Subsequent normal GEF/GFF/PDF batches can embed the original model's cached reference rows and a native-vs-source comparison within the **same completed project workbook**, comparing by CPT identity and surveyed coordinates. Groundwater/cone-ratio differences and disagreements remain explicit.
3. **Foundations → LOAD ORIGINAL XLSB / XLSX**: Directly map cached original raft settlement and minimum FOS; still do not label imported design results independently validated.
4. **QA & Review → PRINT EXACT ORIGINAL XLSB PDF**: Uses locally installed Microsoft Excel to print the source workbook's *currently saved* `CPT-Graphs` sheet, retaining exact original Excel chart layout, fonts and plot series. It will NOT pretend to print another CPT.
5. **QA & Review → RECALCULATE NEW GEF IN ORIGINAL EXCEL**: Optional on Windows PCs with Microsoft Excel. Validates the new GEF's header field positions, opens the original XLSB READ-ONLY with VBA macros and external link updates disabled, loads the new data into `Input Data`, invokes Excel's own full recalculation, verifies the new `Input!B5` CPT ID, prints the original `CPT-Graphs` sheet, then verifies the generated PDF's CPT identity. Does not overwrite the original workbook. The source model's live Excel/VBA requirements must still be validated on a Windows PC with Excel installed; some templates require enabled macros and are intentionally NOT executed in this safer mode.

### Discovered model details

Read [forensic source findings](../docs/ORIGINAL_XLSB_FORENSIC_FINDINGS.md): source XLSB Input `a=0.80`, groundwater `2.0 m`, smoothing 'Above 3 / Below 3' in centimeters; original Combined CPTs 'Ic' field is **categorical SBT zone**, not a continuous Ic float. A1-292 source zones show approx 6.20-6.29m qualifying zone 4 and support **6.20/0.10**, versus the earlier app's incorrect 6.20/0.20. Do not silently assume a 0.10m source discrepancy is acceptable; use `CPT_Reference_Parity.xlsx` and engineer review.

## Engineering QA updates
- Silt is a **project Ic screening label**, not a laboratory USCS class.
- Raw last valid Ic record bounds *measured* silt. Terminal zero-fs or missing-data tail is UNKNOWN and is never silently extended to full CPT depth.
- If versions of a nominal CPT disagree in accepted silt thickness, surveyed location or elevation, the final project CPT is **REVIEW** until reconciled. The audit preserves all physical sources.
- A positive thin silt interval rounded to 0.00 m is REVIEW instead of fabricating a measured 0.10 m.
- Every valid behavior interval can be inspected and exported (including estimated sand-like / silt-like / clay-like classes), plus spikes and invalid gaps.
- Legacy first sheet retains terminal-silt convention pending reference Excel parity, with an explicit Methodology and QA sheet. Do not infer that the entire overlying column is pure sand.
- The previously quoted A1-292 6.20/0.20 conflicts with the user's Raft Summary B292 6.20/0.10. This MUST be reconciled by workbook equations and engineer approval; do not treat either as presently definitive.

## Single project Excel workbook — current product contract
The normal batch creates **one completed, atomic XLSX per run**, not multiple automatic PNG maps or separate parity workbooks. The active exporter is `engineering_compact_export.export_excel`; `reporting_export_v2` forwards to it. The first/default sheet retains exactly the requested five columns. Other tabs include project Summary, editable Charts, CPT Curves, Full Analysis, All Soil Layers, original depth-by-depth numerical readings, coordinates/maps, metadata/GEF source headers, source audit, and explicit REVIEW evidence. The workbook embeds 2D/3D preview imagery, subject to available survey coordinates. Large raw tables can span numbered sheets to respect Excel's row limit.

**Conditional data are conditional.** Raft/isolated/FOS source results and native-vs-original XLSB comparison appear only when the corresponding supported source workbook is selected. Pre/Post matched changes appear in the main workbook when a comparison has been run before the export; the comparison workspace also has an optional standalone XLSX export action. Missing external calculations are never silently fabricated.

The separate `ANALYZE COMPLETE ORIGINAL XLSB PROJECT` command intentionally exports an original-workbook *reference study*; it is distinct from a normal CPT run. Its cache-derived results are not recomputed native engineering equations.

## Report outputs
The app generates a CPT PDF with source-style qc/fs/u2/Ic and Qtn–Fr plots, complete engineering/QC appendix and full observed soil-layer profile when measurements permit. The report prints explicit `N/A`/source-unavailable explanations rather than leaving missing metadata cells blank. A coordinate/elevation/identity-matched official PDF is preserved as the original report pages with appended analysis. A GEF without a verified official PDF uses the native reference-style renderer; exact pixel parity with the supplied proprietary Excel printout has **not** been independently established for every raw file.

## Real original-PDF acceptance
The repository contains 448 original PDF files. `desktop_app/real_pdf_acceptance.py` and [Real CPT PDF Source Acceptance](../.github/workflows/real-pdf-acceptance.yml) run a source-by-source audit and generate `PDF_Source_Manifest.csv`, `PDF_Source_Audit.csv`, `PDF_Acceptance_Result.json`, and `Real_Project_PDF_Acceptance.xlsx`. The workflow tests the real PDF ingestion and grouping process; engineering REVIEW rows remain visible and must not be interpreted as software failures or forced to conclusive values. Running this workflow does **not** certify source-workbook formulas, foundation design, or exact print layout.

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
