# Operator-first CPT Studio — Windows Acceptance Checklist

**Source of truth:** [Production Closure Plan, Section 8](PRODUCTION_CLOSURE_PLAN.md) and W01–W12.  
**Disposition:** TARGETS PENDING VERIFICATION. Checkboxes below are not claims of test success.  
**Release policy:** If a critical box is unchecked, publish only an engineering preview, not a production-approved release.

## A. One step input UX (UX-01)

- [ ] Default opening screen contains exactly the main actions **OPEN CPT FILES**, **OPEN CPT FOLDER**, **START FULL ANALYSIS**. A clear Results/Open Latest Excel area is available after completion.
- [ ] No `SOURCE CALCULATION XLSB`, `RAFT / ISOLATED SUMMARY XLSX`, `SITE LIMIT / COORDINATES` on default screen. All optional reference/engineering controls are in **Review → Advanced Reference Data**, collapsed by default.
- [ ] GEF file, GFF file, vector PDF, mixed source files, PDF-only folder, raw-only folder, mixed folder, uppercase extensions and paths with Unicode/Arabic are accepted.
- [ ] Auto-scanning the chosen folder discovers optional approved workbook/coordinate assets if present; ambiguous candidates are flagged, not silently selected.
- [ ] Missing reference XLSB/summary/CRS does not prevent numerically supportable core CPT analyses. Unsupported foundation calculations are visibly `REFERENCE ONLY / NOT AVAILABLE`, not zeros/unchecked PASS.
- [ ] Default output folder is created automatically and exactly the expected output products are produced.
- [ ] All primary buttons look clickable, have hover/disabled/loading/focus states and keyboard navigation.

## B. Progress/reliability (PROG-01)

- [ ] While running, progress is visible globally on Analyze/Results and during map/QA navigation.
- [ ] Source count, current file, percent, valid/review/error counts and stage text update from actual worker events.
- [ ] Stage coverage: discover → read/parse → calculate → resolve versions → PDF generation → one workbook/maps → output validation and commit.
- [ ] Percent moves forward monotonically; `100%` appears only after verified completed output exists.
- [ ] Blocking test files and 448-PDF folder demonstrate UI remains responsive and Cancel works.
- [ ] Cancellation and Windows process crash do not overwrite the last verified `Latest` workbook.
- [ ] Retry of failed sources works without duplicated CPT rows or unaccounted file omissions.
- [ ] Unknown ETA is shown as unavailable rather than invented.

## C. 2D/3D engineering explorer (MAP-01)

- [ ] Every accepted source appears at the correct local XY and ground RL, linked to its exact physical file, reference and stage.
- [ ] Coordinate QA lists missing/out-of-range/outlier values (including the nine known source anomalies) without automatically correcting them.
- [ ] 2D map: zoom, pan, click-to-profile/PDF, site outline when known, labels, legends, metric filter, deepest/thickest individual and cumulative layer rankings.
- [ ] 3D: rotate, zoom, measured column XY, RL, true vertical depth, valid and UNKNOWN band colors, stand-alone full-screen view, optional exaggerated vertical scale clearly labeled.
- [ ] Depth slice and cross-section work for single/multiple layers, including gaps and noisy/partial sounding data.
- [ ] Unsupported interpolation is off by default; inferred surfaces have a separate legend/coverage boundary and are not passed off as measured soil.
- [ ] Interactive view remains responsive on 1, 10, 100 and 400+ point datasets.
- [ ] Screenshot and clickable tests run at 1024×697, 1366×768, 1920×1080, and at 125–200% Windows DPI; no clipped or overlapping controls.

## D. Exactly one fully populated Excel output (XLSX-01)

- [ ] First worksheet retains exactly five requested columns (SI.No, CPT REFERENCE, Silt start depth after (m), silt depth (m), sand layer thickness before silt (m)).
- [ ] Same workbook includes all depth sample data qc/fs/u2/qt/Fr/Qtn/Ic, ALL interpreted intervals, raw & reported boundaries, unknown segments, source metadata, revision audit and full engineering QA.
- [ ] Same workbook includes project map, 3D overview, project dashboard, project-wide maximum with CPT reference/coordinate, foundation/reference results if source-approved, and PRE/POST changes when supplied.
- [ ] All missing values are explicitly typed as N/A/REVIEW with reason; no fabricated 0.00 m.
- [ ] Excel row-cap test (>1,048,576 numeric rows) splits into numbered sheets and includes a point index.
- [ ] Workbook opens without corruption, images are embedded internally, numbers and dashboard sums match source cases, no separate auto PNGs or duplicate XLSX.
- [ ] Open Latest Excel opens this run's verified completed workbook, not a stale or incomplete file.

## E. Complete individual CPT PDF reports (PDF-01)

- [ ] Names/client/location/test date/ground elevation/XY/cone ID/area ratio/bottom depth are populated when available; unavailable fields explicitly say N/A with reason.
- [ ] Correct qc/fs/u2/Ic graphs, true measured Qtn vs Fr plot, legend, axes and units, with full interpreted all-layer appendix and QC.
- [ ] Existing official PDF pages are preserved exactly when provenance matches; when mismatched, PDF reuse is refused and audited.
- [ ] Side-by-side plot/text/geometry checks for minimum ten approved reference PDFs, plus B04/B05/B07/B18/B19 and A1-292.
- [ ] No blank metadata cells, overlaps, cut-off logos, empty PDFs or missing appendix.

## F. Engineering review integrity (W01–W06/W11/W12)

- [ ] Engineer-annotated B04/B05/B07/B18/B19 outputs independently reproduced under signed assumption list.
- [ ] A1-292 original cached 6.20/0.10 vs old 6.20/0.20 discrepancy resolved numerically; B342/B343/B355/B356 explained.
- [ ] Ic screening threshold and smoothing semantics (3 cm above/below vs PRE=3/POST=10 samples), per-cone area factor and groundwater data documented.
- [ ] Raster/no-friction/uncertain-tail CPTs remain explicit REVIEW or UNKNOWN; no overreporting measured sand or silt.
- [ ] Raft/isolated/liquefaction outputs computed from approved equations and validated independently **or** displayed as reference-only with no design signoff.
- [ ] Actual 448 source PDFs run end-to-end with per-file manifest, source resolution, PDF output, one workbook, 2D/3D and runtime/error report.
- [ ] Versioned Windows EXE tested interactively (dialogs, external file opening, cancel, full-screen 3D, Excel, PDFs), CI test artifacts/screenshots retained and reviewed.
- [ ] Project lead and licensed geotechnical reviewer confirm release criteria. No `PRODUCTION ENGINEERING VALIDATED` label without approvals.

## Required evidence bundle
One immutable acceptance package per release containing:
- Release source SHA, EXE/ZIP SHA256, Windows runner ID and precise app version;
- numerical acceptance matrix, real-file manifest, per-file exception list, XLSX schema check, PDF rendered-difference summary;
- screenshot set showing full workflow/3D/progress at all required resolutions;
- 400+ real input performance and memory benchmark, cancellation and error injection logs;
- explicit list of engineer decisions, unresolved exceptions, and signed status.

## Execution order
1. **Workflow/UI contract:** remove mandatory technical controls and add global progress; test input paths.
2. **Engine/source quality:** confirm historical real examples, provenance and revision policy.
3. **Unified deliverables:** complete PDF metadata and all-in-one Excel schema, validate raw depth rows and map embeddings.
4. **2D/3D engineering viewer:** proper site mapping, cross-sections, depth slices and fast project navigation.
5. **Acceptance and release:** execute genuine 448-PDF run, private reference validations, visual UX and Windows executable testing; publish approved deliverable only after gates close.
