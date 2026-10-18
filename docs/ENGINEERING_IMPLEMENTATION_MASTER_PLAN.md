# CPT Engineering Platform — Master Implementation Plan
**State:** Engineering work in progress. CI passing is not proof of validated geotechnical design or parity with proprietary Excel/VBA calculations.

## Operator experience addendum — binding requirements (2026-10-19)

**The authoritative, testable plan is [PRODUCTION_CLOSURE_PLAN.md](PRODUCTION_CLOSURE_PLAN.md), section 8**, which is part of W04/W06/W07/W08/W10/W11/W12. These commitments supersede earlier setup controls and any assumption that existing features have passed acceptance just because they appear in screenshots.

- **No technical input selection in normal workflow.** User chooses only **Open CPT Files** or **Open CPT Folder** (GEF/GFF/PDF), then **Start Full Analysis**. The screenshot's separate `SOURCE CALCULATION XLSB`, `RAFT / ISOLATED SUMMARY XLSX`, `SITE LIMIT / COORDINATES` buttons must be removed from the default Analyze screen. Optional approved reference assets may be discovered automatically or supplied within collapsed Expert/QA settings; never block the core analysis when absent.
- **Persistent, truthful progress** with real phases (source discovery, per-file analysis, revision verification, PDF generation, single-XLSX/maps assembly, atomic final verification), processed/total counts, current filename, review/error count, safe Cancel and restart. It must be visible while navigating, not hidden in the Results tab.
- **Professional 2D + real 3D engineering explorer** using actual XY, RL and classified observed depth intervals, with zoom/rotation, depth slices, profile drilldown, site boundaries where verified, max individual/cumulative silt layers, unknown sensor spans, and no misrepresented continuous inferred volumes. 400+ CPT navigation needs measured responsive performance and documented coordinate exceptions.
- **Exactly one comprehensive XLSX** per successful run. Five-column first sheet plus all numerical samples, all layers, foundation/reference provenance, full site summary, QC, comparison results when supplied, and embedded 2D/3D views. No extra PNG or second XLSX by default. Excel row-limit overflow requires split and an index.
- **Complete PDF output** with no unexplained empty client/site/date/coordinate/unit/test columns, correct plots, all-layer/QC appendix, and verified official-page preservation where available; missing fields explicitly N/A with reason.
- **UI acceptance before release:** simple Analyze/Results/Site & 3D/All Layers/Compare/Reports/Review hierarchy, visible primary actions, working Open Latest Excel/PDF, no inactive buttons, screenshots at 1024×697, 1366×768, 1920×1080 and DPI-scaled layouts. Full input/mapping/progress/cancellation/workbook/PDF Windows functional and visual test matrix is mandatory.
- **No false engineering signoff:** generic source-batch data can run without the original XLSB, but unvalidated raft/isolated/liquefaction results may only be shown as imported/cached and labelled reference-only. REVIEW must carry a specific reason rather than be auto-converted to success.

**Do not mark these complete or publish a certified build without the new numbered checks** `UX-01`, `UX-02`, `PROG-01`, `MAP-01`, `XLSX-01`, `PDF-01` in the authoritative closure plan.

## Mission
Offline Windows desktop application for raw GEF/GFF and supported PDF inputs, with validated CPT measurements, complete SBT layer segmentation, georeferenced charts/maps, raft/isolated-footing summaries, auditable Pre/Post comparisons, Excel and PDF outputs.

## Rules and engineering decisions
1. Preserve original source data and each reported assumption (groundwater, unit weight, area ratio, depth convention, smoothing, test phase). Maintain distinct RAW, REFERENCE, VALIDATED and REVIEW statuses.
2. Source Excel calculation workbook is the baseline to reproduce, **not automatically assumed correct**. Audit formulas/VBA, Qtn/Fr/Ic, fines-content calibration, QC masks, stress normalization, design equations, charts and print settings. Record parity failures.
3. Use project Ic >= 2.60 as a **screening criterion for silt-like behavior**; do not claim laboratory USCS classification. Thin spikes require a defined persistence rule.
4. Never extend a measured silt layer through zero-fs or missing-data tail without independently supported evidence. Show UNKNOWN and boundary censoring separately.
5. Detect and retain **all** soil-behavior layers, unclassified gaps and isolated threshold crossings, not just deepest terminal silt. Show observed and reported thickness separately; never inflate measured 0.06 m to 0.10 m silently.
6. Engineer's rolling windows PRE=3, POST=10 must be reproducible, with raw and common-settings comparison modes; their position in the calculation order must be verified against the workbook.
7. Match CPTs by approved identity and coordinates/date/phase; a filename B-prefix or revision suffix is not proof of same physical test. Retain all source revisions with reasons.
8. Foundation settlement/FOS need verified raft/isolated equations, loads, dimensions, groundwater and project acceptance criteria; until approved, only import/reference external values.
9. Maps must use verified local coordinate reference system (CRS), plot surveyed points, and not imply interpolation outside the data hull; label estimated contours and uncertainty.
10. Every output—individual CPT chart, project chart, map, workbook, PDF, comparison—reads from one versioned validated result object.

## Work packages and dependencies
| ID | Deliverable | Gate |
|---|---|---|
| WS-01 | Workbook equation/VBA reference audit; five raw annotated CPT cases and PDF approved anchor dataset | G0 formula parity report |
| WS-02 | Corrected QC, terminal fs dropout, all-depth layer segmentation, configurable smoothing, uncertainty | G1 unit/regression green + engineer review |
| WS-03 | Revision-aware source matching and provenance; source audit and errors | G2 matching regression |
| WS-04 | Individual raw/smoothed CPT profiles; all-layer strip; project charts | G3 numerical consistency |
| WS-05 | Coordinate map and area plan; CPT hover/select, color metric, export; optional bounded contours | G3 CRS+map tests |
| WS-06 | Foundation raft (50x60m) and isolated (3x3m) summaries; source workbook formulas | G4 engineer validation |
| WS-07 | Pre/Post summary importer, matched/unmatched/ambiguous QA, absolute/relative deltas, charts and maps | G3 compare tests |
| WS-08 | Five-column quick sheet, Full Analysis, Soil Layers, Source Audit, QA, raft/isolated, compare | G3 workbook test |
| WS-09 | Excel-reference PDF styling, Qtn-Fr plotting, original PDF+appended result, visual diff | G5 visual parity |
| WS-10 | Modern maximized UI, chart/map tabs, comparison wizard, caching, analysis-only, responsive batch progress and Windows release CI | G5 GUI/Windows tests |

## Deliverables and project shape
- desktop_app/engineering_layers.py: all-layer segmentation / quality and observed boundaries.
- desktop_app/engineering_maps.py: offline coordinate chart and export; CRS explicit.
- desktop_app/engineering_comparison.py: pair summaries and compute validated deltas.
- desktop_app/engineering_workspace.py: integrate layers, maps and comparisons with desktop.
- docs: methodology, validation matrix, discrepancies, benchmark and release notes.
- Tests for raw/dropout/multiple strata, revisional alias conflicts, mapping, comparison and output parity.

## Acceptance dataset
- Five engineer-annotated GEF cases: B05/B07 no sustained silt; B18 0.20, B19 0.30, B04 4.3+ / 0.20 (numbers **provisional** until workbook parity confirmed).
- A1-292 legacy app 6.20/0.20 vs Raft Summary B292 6.20/0.10 must be explicitly unresolved until reconciled by coordinates and source formulas.
- Approved project PDF cases B342, B343, B355, B356 must remain stable under native-vector parsing.
- Synthetic alternating SBT, missing fs terminal tail, thin layer and invalid coordinate fixtures.

## Release and safety gates
- G0 reference formula and foundation engineering parameters audited. 
- G1 all soil observations bounded; full profile detection independently verified.
- G2 every duplicate and ambiguous match auditable; no silent source priority changes.
- G3 maps, comparisons, spreadsheets and full charts numerically consistent; representative large-batch benchmark.
- G4 foundation calculations match engineer-approved source and design criteria; otherwise explicitly NOT VALIDATED.
- G5 PDF reference visual regression reviewed and Windows GUI behavior checked on a real interactive Windows desktop.
A GitHub Actions success covers automated tests and package build only. Do not label the entire project COMPLETE before G0-G5 are met.


## 2026-10-19 product-correction contract (user acceptance)

**Single obvious operation:** Select GEF/GFF/PDF files OR a folder; click **ANALYZE PROJECT**; show count/percentage/phase/current CPT at all times even when reviewing another tab; then **Open Excel** or **Open PDFs**. Default output beside the selected source. Advanced engineering parameters and source-workbook tools must be collapsed/discoverable, not competing with this primary action.

**Why earlier screenshots were inadequate**
- Progress was placed on Setup, but analysis switched to Results; the bar was not visible during processing.
- Normal map UI showed thin 3D line strokes/point plan without accessible depth/elevation context, and full source-project XLSB map required a separate manual import.
- REVIEW cells lacked useful measured evidence and there could be duplicate/unparsed source versions in uncollapsed views. REVIEW must have code, technical cause, observed interval, point name and missing tail; never replace a defensible uncertainty with a guessed VERIFIED.
- PDF metadata cells often contained blanks when an input lacked an equivalent source field. Use explicit 'Not supplied in source' or 'Not measured', not empty values. Do not misuse GEF export date as CPT test date.
- Output had multiple separately exported spreadsheets/maps; normal workflow must create **one comprehensive Excel file** with all raw/derived/source QA, charts and embedded site-map figures, plus PDF reports.
- GUI's advanced buttons and settings distracted from the one-step intake requested.

### Priority P0 — pre-release blocking checks
1. Persistent sidebar/footer progress bar with stage, current/total and filename; GUI thread never blocks; queues for raw/PDF analysis and PDF/report/workbook stages; tested failure path, cancel and 100% only after atomic output finalization. No fake zero-depth rows on parsing errors; error reasons in workbook.
2. Group sources into unique CPTs with provenance, revision and coordinate/datum conflicts; main results one row per CPT, source QA separate. Distinguish NO SILT (no sustained *observed* qualifying interval) from REVIEW (measurement inadequate or disagreement); never infer across invalid fs.
3. Robust PDF: source originals untouched; numerical raw data preferred; appended analysis with nonblank source metadata, all intervals, measured/unknown regions, calculation assumptions and sensor-quality conclusions. For PDF-only, report graphical evidence limits. Diff against original PDF.
4. Exactly one normal-run XLSX with original five-column quick sheet (sand fifth), full analysis, every sample when available, all observed/unknown layers, original reference and foundation values if supplied, source audit, QA, site coordinates, embedded 2D+3D maps, methodology and max-thickness identification. Zero standalone PNG or second workbook unless explicitly user-exported.
5. Site map must render verified coordinates, survey boundary, ground datum, colored CPT interval columns, selectable point with a full vertical profile, mouse-rotatable 3D view and risk/slice view only where supported. No falsely continuous geology/hull extrapolation, coordinate outlier QA.
6. One-step default UI at 1024×697, 1366×768, 1920×1080 and scaled Windows DPI. Interactive screenshots, assertions on visible primary buttons, no control overlap, modal file-picker and multi-stage pipeline tested.
7. Source engineering model: original cached workbook supports reference mode; full original XLSB Excel formula execution requires licensed Microsoft Excel and no prohibited macros. No claim of numerical formula parity, independently validated footing settlement/FOS or certified USCS when not evidenced.

### Product acceptance matrix
| Feature | Positive | Failure/edge | Release criterion |
|---|---|---|---|
| GEF/GFF intake | Single/folder mixed-case extensions | corrupted header, duplicates | One result/source QA, no zero-depth fake |
| PDF intake | Vector template and paired raw | raster/image-only | Original unchanged, REVIEW reason visible |
| Progress | 1 CPT, 400 CPTs, Reports tab open | cancel/error/worker exception | Visible bar all tabs, monotonic progress, no false 100 |
| Review | B04/B05/B07/B18/B19 and A1-292 | fs zero/end dropout; conflicting original | Observations/reasons visible; no inferred thickness |
| XLSX | One output with embedded maps and raw points | 400 samples, missing metadata, source flags | no blank semantic cells, all tabs open |
| PDF | raw-generated, PDF-appended | missing cone ID, date or u2 | explicit not-supplied, complete appendix |
| Mapping | 3D surveyed columns and 2D points | bad coords, no CRS, empty data | coordinates grounded, outliers audit |
| UI | source-only default setup, overview and output buttons | compact screen & high DPI | visual QA and keyboard input tested |
| Pre/Post | matched coordinate pairs, harmonized windows | mismatched ID, missing samples | audit and no invented differences |
