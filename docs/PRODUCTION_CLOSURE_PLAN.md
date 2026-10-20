# CPT Engineering Studio — Production Closure Plan (evidence-based)
**Date:** 2026-10-18  
**Disposition:** NOT READY for geotechnical-design acceptance. Functional Windows preview exists.  
**Source of truth:** This document supersedes the outdated numbers in `docs/IMPLEMENTATION_STATUS.md` and any prior completion claims. It is an execution/validation contract, not proof of implementation.

## 0. Evidence from actual repository (as audited)
- Current `main` source tree contains **448 real CPT PDF blobs** under `pdfs/pdf_Single/` and **zero GEF/GFF blobs**. These PDFs can be used for a real PDF pipeline acceptance run; private GEF/GFF and XLSB data should not be newly exposed in a public release.
- Last successful Windows workflow [39164020555](https://github.com/karimelzoser/analyze/actions/runs/39164020555) reported **104 passing automated tests** plus source and frozen EXE GUI startup tests.
- The workflow's **400-sounding synthetic** speed test builds 400 simple ~130-measurement GEF inputs, generates a workbook and four maps, but **does not exercise** the 448 original PDFs, 400 generated PDFs, original Microsoft Excel/VBA runtime, or the real project's manual engineering reference judgments. Its recorded time was **17.90 seconds**, of which **3.63 s calculation**, **11.17 s workbook**, **3.10 s four charts**; those figures are NOT a project runtime SLA.
- Original supplied XLSB has 448 saved foundation rows / 447 saved CPT zone series, as previously decoded. Saved numeric outputs are **caches**; binary formula and macro parity remains unproved. This is not necessarily the same physical test/revision inventory as the repo's 448 PDFs.
- `engineering_foundations.py` explicitly compares **imported** settlement/FOS against supplied limits; it does not solve footing stress, settlement or liquefaction.
- `engineering_excel_engine.py` is an **optional Excel-installed Windows** route that assumes a specific GEF header and particular `Input Data` layout. That script is not validated by cloud CI against a real Excel+XLSB calculation session, particularly if source macros are required.
- There are several legacy app entrypoints and exporters. `reporting_export_v2.export_excel` immediately delegates to `engineering_compact_export.export_excel`; the large original exporter implementation below its return is unreachable. `analysis/analyze_cpt.py` is an older separate PDF interpretation path on a separate workflow/branch. The currently shipped exporter and interpretation policy need one canonical source of truth.
- The legacy status document lists **49 tests**, which is outdated, and the README still contains legacy chart/worksheet statements alongside the new compact workbook contract.
- Known cases requiring independent signoff include 5 engineer-annotated raw CPTs, A1-292 **6.20/0.10 saved XLSB vs 6.20/0.20 earlier native** and B342/B343/B355 layer-boundary discrepancies. Nine saved survey coordinates were withheld as gross outliers; not silently corrected.
- Existing [issue #2](https://github.com/karimelzoser/analyze/issues/2), [#3](https://github.com/karimelzoser/analyze/issues/3), and [#4](https://github.com/karimelzoser/analyze/issues/4) remain OPEN.

## A2 71-GEF isolated footing + soil-atlas continuation (2026-10-20)

**Executable implementation checkpoint:** [A2_ISOLATED_ATLAS_CONTINUATION.md](A2_ISOLATED_ATLAS_CONTINUATION.md). This is the handoff for the current W05/W07/W08/W10 improvements and the original 71-private-GEF acceptance. Preserve the private archive outside the public GitHub repository.

- W08 browser visualization regression: focused 3D measured blocks now have a fair per-CPT 700-polygon default budget, with opt-in ALL mode retaining every depth interval and CPT. Prior CI failure `39370283126` (default 1020 > 900 polygons) is the acceptance target. Do not skip browser smoke or relax the threshold just to make a build green.
- W05 provisional isolated-footing results: nominal sampled-depth coverage is **not** adequate by itself; stress-weighted influence coverage and exact unobserved BGL intervals are now calculated, displayed in the isolated table and included in a dedicated workbook QA sheet. A numerical screening estimate is not validated settlement/FOS.
- Real-data evidence: 71 physical A2 files, 68 with >=90% observed influence-depth coverage under the documented simplified 3×3m, 1.5B screen. B253/B256 aborted initial pushes are distinct from their later complete attempts; B254 earlier attempt ~86.2% versus later attempt 100%, with source-revision conflict to be preserved.
- New tests and browser/GUI/Excel regression must pass before claiming deliverable-ready; private 71-file field validation and original source-workbook formula signoff remain OPEN.
- Source and QA pointers and resumption order are documented in the continuation file; do not restart analysis from stale chat summaries.

## 1. Why progress has stalled
1. **Feature-build-first, validation-later:** successful code tests and GUI previews were described as delivered before formula equivalence and geotechnical review.
2. **Reference output mistaken for algorithm validation:** reading original XLSB cached values and drawing its charts is not independent reproduction of VBA/formulas across changed inputs.
3. **Synthetic test substituted for real acceptance:** convenient generated GEF files do not represent real PDF formats, missing traces, real coordinates, duplicates, or Excel report printing.
4. **Unresolved engineering policy:** 2.60 screening is not USCS silt proof; 3 cm above/below smoothing in XLSB may differ from 3/10-sample settings; original 0.80 area ratio and some raw 0.75 cone ratio should never silently override each other; no agreed policy for terminal sensor dropout, thin layers or acceptance criteria.
5. **Data provenance/identity problems:** filename suffixes, reference aliases, file dates, true test dates, coordinates and repeated locations can be conflated.
6. **Architecture drift:** duplicated entrypoints, multiple exporters, separate old/new interpreters, stale README and statuses result in ambiguous production behavior.
7. **Missing production environment:** real original Excel workbook recalculation needs compatible licensed Microsoft Excel, controlled macros policy and verification; project design loads/criteria and correct coordinate CRS must be supplied/approved.
8. **No end-to-end signoff evidence:** no traceable report of every real file, source-to-output matching, PDF visual differences, user GUI clickthrough and reviewed exception disposition.

## 2. Single product/output contract
- **Desktop:** one maximized Windows executable, one project at a time, with Setup, Results, All Layers, Georeferenced Map/3D, Foundations, Pre/Post, Reports and QA. Every action must provide success/failure feedback.
- **Source inputs:** GEF/GFF, compatible vector PDF, original XLSB, provided summary XLSX, site boundary and stage-specific pre/post data. Preserve originals, hashes, test time and coordinates.
- **Canonical observations:** corrected BGL/elevation, qc/fs/u2/qt/Fr/Qtn/Ic with units, sensor validity and processing settings, all observed layers, unclassified gaps, independent QA and provenance. One canonical calculation API; every PDF/XLSX/chart reads this record.
- **CPT classification:** project `Ic >= 2.60` is fine-grained-like screening, NOT definitive USCS silt. Observed vs inferred vs unknown intervals differentiated; multiple sand-like and fine-grained-like intervals shown, not only terminal silt.
- **Excel:** **one atomic, complete XLSX** per batch. First sheet exactly the requested five columns; remaining sheets contain every source/native depth sample (split into multiple numbered measurement sheets if Excel's row limit is reached), all layers, full engineering summary/raft/isolated and liquefaction *where validated*, source audit, coordinate QA and embedded 2D/3D figures. Optional sources have explicitly labeled cached/reference values. No fabricated blanks and no silent data truncation.
- **PDF:** original report pages preserved when matching official source exists, plus complete analysis/QC appendix; for new raw CPTs, native or Excel-generated template must be numerically and visually verified against a selected original. N/A with reason, not empty design fields.
- **Maps:** actual surveyed XY/RL, CRS and site limits explicit; full CPT 2D plan, depth slices, all qualified 3D columns and optional clearly marked inferred wedges only within supported local data. No invented continuous 3D strata.
- **Comparison:** PRE vs POST matching with coordinate/date/elevation/depth audit; harmonized-smoothing deltas separate from native pre=3/post=10 outputs; unmatched and ambiguous cases retained; changes are not automatically engineering improvement.

## 3. Work packages with tangible completion criteria

| ID | Work package | Engineering / implementation deliverable | Quantitative / objective exit test | Dependencies |
|---|---|---|---|---|
| W01 | Dataset control and truth-set | Manifest of 448 PDFs, reference XLSB, authorized raw GEF/GFF, manual B04/B05/B07/B18/B19 plus B292/B342/B343/B355/B356; hashes, identity, source/date, coords, groundwater, revision, reference status | **100% of supplied sources inventoried** with supported/unsupported/error disposition; no silent file omission; all "golden" expected outcomes approved | Access to protected raw and source workbooks |
| W02 | Source-workbook equation audit | Extract and independently document XLSB formulas/VBA, named constants, qc/qt/Fr/Qtn/Ic, stress normalization, 3cm vs 3/10 filters, and all design formulas; reproducible input/output cases | Engineer approves exact methods/units, and repeated source-workbook runs on representative CPTs reproduce saved values within explicitly approved tolerances | W01, licensed Excel or full formula decoding |
| W03 | Canonical CPT calculation + segmentation | One versioned engine, raw/readout QC, zero-fs/terminal dropouts, interpolated crossing boundaries, all soil behavior strata, observed vs unknown, controlled rounding | Golden cases B04/B05/B07/B18/B19/B292/B342/B343/B355/B356 all reconciled or explicit REVIEW with case-specific reasons; raw vs original method differences quantified; no unreviewed delta beyond approved tolerance | W02 |
| W04 | Identity, PDF input and revisions | Source registry; vector PDF validation, coordinate-verified linking and revision conflict resolution, readable error reasons; documented raster fallback only when defensible | Actual **448-PDF end-to-end test**: every input accounted for, exactly one documented selected version per true CPT identity, no hidden errors or guessed data, audit and deterministic rerun diff report | W01, W03 |
| W05 | Raft / isolated / liquefaction calculations | Native equation modules for independent stress distribution, bearing capacity, settlement, safety factors, with site-specific assumptions/acceptance checks; import reference path remains distinct | Both footing types have approved benchmark computations and parameter-sensitivity tests; independently reproduced settlement/FOS/check outcomes within engineer-approved tolerances; no unsupported PASS/FAIL | W02, project engineering decisions |
| W06 | Exact original PDF compatibility | Controlled Excel (where required) and/or canonical native renderer for measured profiles, Ic panel, true Qtn–Fr zone plot, original charts, metadata, logo/legend, complete QA appendix | At least 10 representative reference PDFs (simple, multiple-layer, dropout, duplicate, different template) compared both numerically and rendered page-by-page; field/plot parity explicitly reviewed and approved | W02,W03,W04 |
| W07 | Unified workbook and maps | Single authoritative XLSX, full raw numeric rows, all layers, raft/isolated/liquefaction, embedded 2D/3D, QA and PRE/POST when supplied; no extraneous PNG/second XLSX by default | Schema/cell-level parity and dashboard-metric consistency for all selected CPTs; Excel reopens; no truncation above 1,048,576 rows; source hashes and QC preserved; no missing values without explanatory status | W03-W06 |
| W08 | Georeferenced 2D/3D | Verified CRS and site outline, coordinate exception review, correct depth-slice/top-bottom windows, layered rotatable 3D, survey-based unclassified zones, filters and export | All accepted survey locations plotted correctly; known nine outliers documented/resolved or withheld; no interpolated results outside supported hull; engineer inspects topology/units and orientation | W01,W03,W05 |
| W09 | PRE/POST effectiveness | Validated comparison wizard, soundings/site summary pairing, common depth/elevation range, normalized qc and Ic change, settlement/FOS and layer deltas, uncertainty and QC maps | Real matched PRE/POST acceptance pairs with engineer-reviewed deltas; unmatched pairs and 3-vs-10-smoothing confounding explicit; zero denominator yields N/A | W03,W05,W08 |
| W10 | UX, reliability, simplification | One production entrypoint/exporter, dead code removal, nonblocking jobs, cancellation, progress, clear buttons, maximized/1024px/125-200% DPI, working Open Latest Excel/PDF, autosaved project, error diagnostics | Interactive Windows human test script passes every button and navigation flow; 100% uncaught errors logged; aborted batch leaves no corrupt latest.xlsx; screenshots examined on at least two display sizes | W04-W09 |
| W11 | Full real-world qualification | CI regression on actual PDFs + **private approved** raw XLSB/GEF fixtures, performance on representative 400+ actual cases, PDF generation and XLSX/3D timing, memory and stability | Per-file manifest/report with total, selected, review, unreadable, PDF/Excel discrepancies, runtime, peak RAM, failures and rerun repeatability; zero unaccounted source files; all critical tests green | W01-W10 |
| W12 | Engineering release signoff | Versioned methodology, change log, sample outputs, test/benchmark evidence, user training and rollback, engineering approvals | Geotechnical reviewer signs calculations, project lead approves reports/maps/UI, CI release attested to exact SHA and tested EXE; only then label **PRODUCTION ENGINEERING VALIDATED** | All |

## 4. Exact real-project validation instead of synthetic-only
**Public/repo-controlled dataset**: Run the shipped desktop pipeline against the **448 actual PDFs already in the repository** in a dedicated, manually triggered `workflow_dispatch` QA job. Never turn `REVIEW` into a passing value to improve percentages. Create artifact report (CSV or private/internal Excel) with:
- physical file, canonical CPT family, revision, source checksum, parse/extraction fidelity, format/vector status, selected/rejected reason and coordinate evidence;
- observed screen intervals, raw/report precision and source-XLSB comparison (where available), explicit REVIEW reason and missing-field inventory;
- number of CPTs, # reviewed, # unsupported and coverage, duration to read/analyze all real PDFs, duration to generate all CPT PDFs, workbook generation, map/3D and peak RAM;
- comparison of reruns for deterministic results and no file omissions.

**Private/controlled dataset**: Use the already supplied annotated GEF/GFF and reference XLSB / Pre Summary, plus a complete representative raw batch when available, in a secure Windows test workspace or dedicated private test artifact. Do not commit confidential source files or XLSB binaries to a public repo. Expand test sets across pre/post, dropout, poor quality, diverse cone configurations, duplicates, different depth lengths and soil profiles. Maintain original source copies read-only.

**Synthetic test** remains for quick CI performance/regression only; it is never titled a real engineering accuracy test.

## 5. Non-negotiable engineering interpretation decisions
Before declaring W02/W03/W05 complete, record signed decision notes for:
1. Sampling interval and rolling mean: original XLSB's `Above=3 / Below=3` **centimeters** vs colleague's `PRE=3 / POST=10` **samples**; exactly where smoothing occurs relative to Ic computation.
2. Actual per-cone measured `a` (GEF may say 0.75) vs original cached XLSB 0.80; do not apply one silently to every source. Groundwater, soil unit weight, stress model and elevation datum per investigation/phase.
3. Screen `Ic >= 2.60` vs strict `> 2.60`, minimum sustained measured layer length, brief spikes, sensor tail censoring, 0.10m report HALF_UP and classification of clay/organic-like screening.
4. Foundation settlement and liquefaction method/code, geometry, groundwater, magnitudes/PGA, loading, load factors, allowable settlement and safety margins; named approver for every design acceptance criterion.
5. Coordinate reference system (EPSG/project grid), survey site polygon, datum and approved handling of source location outliers.

If a decision cannot be supported, expose that result as `REFERENCE-ONLY` or `REVIEW` while continuing the rest of the software. **Do not substitute optimistic values.**

## 6. Dependency-driven execution (single final product, not partial launches)
**Track A — Engineering truth:** W01 → W02 → W03 → W05.  
**Track B — Source ingestion and artifacts:** W01 → W04 → W06 → W07.  
**Track C — Spatial, PRE/POST and UI:** W01/W03 → W08/W09 → W10.  
**Integration and release:** all tracks → W11 → W12.

Software engineers implement with fixed fixtures; geotechnical reviewer owns acceptance of calculation assumptions; QA owns automated and user acceptance evidence; project lead owns authoritative reference datasets and final scope. Initial planning estimate must be revised after the workbook/VBA and dataset audit, rather than committing to an unsupported finish date.

## 7. Release gating and governance
- **PR gate:** unit tests, typed/data schema tests, numerical fixture compare and no severe security/data exposure.
- **Integration gate:** PDF batch + source/reference workbook + optional Excel-driven compare + unified one-XLSX output + 3D map + PRE/POST.
- **Engineering gate:** signed reference-case results, formula/units/threshold decisions, no unexplained accepted-value discrepancies.
- **Windows gate:** frozen EXE installed/started on a real Windows machine, file-open dialogs/associations tested, UI accessible on 1024px and high-DPI, stress batch tested, delivery ZIP checksum verified.
- **Production release:** immutable versioned ZIP + release note linking methodology, source SHA, run IDs, exception register, coverage table and authorized signoffs. Keep today's successful build classified **ENGINEERING PREVIEW** until then.

## 8. Operator-first UX and full-output acceptance addendum (2026-10-19)

**This addendum is a binding part of the 12-work-package production contract, not a feature wish list.** It supersedes any earlier setup-screen design that expects the operator to select source XLSB, Raft / Isolated Summary XLSX or Site Limit / Coordinates separately before analysing CPTs. It also overrides any assumption that an existing progress bar, 3D widget, or XLSX drawing constitutes an accepted usable feature.

### 8.1 One-step default workflow — W10, W04, W07

The nontechnical operator interface must start with a **single dominant input path**:

```text
OPEN CPT FILES     or     OPEN CPT FOLDER
               ↓
Automatically inventory GEF / GFF / supported PDF inputs
               ↓
START FULL ANALYSIS
               ↓
Persistent real progress + source-level warnings
               ↓
Results, 2D/3D site map, all-depth layers, maximum silt, full XLSX, source PDFs
```

- Input accepts `.gef`, `.gff`, `.pdf` individually, mixed batches and folders (including case-insensitive extensions, predictable recursion, hidden/irrelevant file filtering). File drag-and-drop may be provided if reliable. **No mandatory XLSB, foundation workbook, project boundary, coordinate upload, test-stage or engineering-parameter form** for normal use.
- **Remove the three visible source-asset buttons from the main setup**: `SOURCE CALCULATION XLSB`, `RAFT / ISOLATED SUMMARY XLSX`, `SITE LIMIT / COORDINATES`. Put optional reference/advanced engineering inputs inside a clearly named **Advanced / QA → Reference Data** section, collapsed by default. The normal workflow must have no dead, decorative or confusing buttons.
- **Automatic discovery** in the selected directory tree is allowed for an approved original XLSB, summary and boundary; never silently choose between competing matches or execute XLSB macros. Attach provenance and source fingerprints; if no trusted optional model exists, still complete all measurements and SBT screening possible from the input and mark missing foundation/survey fields `NOT AVAILABLE — no approved source`, not fabricated zeros or invented PASS.
- Settings such as groundwater, soil unit weight, cone area ratio, PRE/POST rolling rules and Ic persistence are configurable in Advanced Settings with visible source/method badges in QA; safe defaults must be labeled *assumptions*. Automatically read per-source cone factors and coordinates where present. Unknown PRE/POST stage must not be guessed as PRE when it affects an engineering comparison.
- On completion, **one primary 'Open Complete Excel' button, one 'Open PDF Reports' button, one 'View Site Map' button** and an optional 'Review Exceptions' action. Excel must resolve to **that run's verified completed output**, never an old file or partial workbook.
- One input folder + one `CPT_Output` folder by default. No required manual destination selection and no sidecar PNG/duplicate XLSX by default. Explicit exports may still produce separate PNG/PDF/CSV if the operator asks.
- If source quality is insufficient, display `REVIEW` with the **specific reason, measured ranges, missing-data ranges and reference alternative where authorized**. Do not remove REVIEW by inventing silt or changing thresholds; report `NO QUALIFYING OBSERVED INTERVAL` separately from `UNKNOWN BELOW TEST`.

**Acceptance UX-01:** On a clean Windows workstation, an operator can launch maximized, choose a GFF/GEF/PDF file or a folder, press **Start Full Analysis** and access Excel, PDF and maps **without ever seeing or clicking a source XLSB/summary/site-limit button**. Run separate scenarios for GFF-only, PDF-only, mixed, single file, folder, empty folder, unsupported files, duplicate revisions and cancellation.

### 8.2 Real, persistent and accurate analysis progress — W10, W11

- A high-contrast, **always visible** progress component must remain visible on Setup and Results while a job is running; include percent, current stage, `processed / total`, elapsed time, current CPT filename, success/failed/review counts and last diagnostic message. A simple bar elsewhere in a hidden tab does **not** pass.
- Progress stages are **Discover/Validate → Parse/Analyze → Resolve Versions/QA → Generate PDFs → Build Complete XLSX/Maps → Verify/Publish**. Report weighted stage progress based on actual completed files/units. Progress must be monotonic to 100% for successful completion and must not jump to 100% before the XLSX has been atomically finalized.
- Worker threads/processes must not mutate Tk widgets directly. Use a thread-safe event queue with UI-mainloop consumption. The analysis must remain navigable, even for a 400+ physical-file batch; log parse/PDF/Excel errors individually.
- Support safe **Cancel** (cooperative cancellation, worker teardown, partial results clearly marked), retry of failed files and restart after crash. Never promote a partial XLSX as latest. Keep an attempt log and deterministic manifest. An overall status `Completed with N exceptions` is distinct from `Success`.
- Display stage-time and estimated remaining time only when defensible. No fake completion percentages or ETA when workload is unknown.

**Acceptance PROG-01:** Automated UI observation and Windows human testing show at least one visible progress change for each stage, periodic updates throughout a 400+ input batch, Cancel and retry tested, 100% shown only after verified output, UI remains responsive; simulated file/permission errors do not freeze the app.

### 8.3 Subsurface 2D/3D is an analysis tool, not decoration — W08, W07, W09

- Start with **real measured coordinates** from GEF/GFF headers or trusted vector-PDF metadata and the confirmed source project grid/CRS. Mark coordinates with disputed identity, missing ground RL or gross errors as `QA / not mappable` and list them in the workbook; do not distort map bounds by including them.
- A usable **2D plan** must plot every accepted CPT, label/search point, show site outline (when known), display metric legend, zoom/pan, filter by region/test stage/status, highlight maximum individual and cumulative silt, open the chosen sounding profile/PDF by click, and export the current view.
- A performant **rotatable/zoomable 3D subsurface view** must show the surveyed XY, true ground elevations and corrected depth/vertical observed segments. Display separate sand-like, fines-screened, clay-like/transition and UNKNOWN layers with stable legends. Preserve true axis units; where vertical exaggeration is used, label factor explicitly and allow true scale.
- Provide a **depth-window slider / depth-slice plan**, vertical section/cross-section from user-selected CPTs, orientation and coordinate readout, isolate/hide category toggles, and point hover/click tooltips with CPT reference, XY, test depth, valid/unknown spans, layer thicknesses and source-quality status.
- Add **maximum silt point** highlight, thickest continuous vs cumulative silt distinction, and optional PRE/POST comparison overlay; do not presume Ic>2.60 uniquely means laboratory USCS silt.
- Distinguish observed CPT columns from any **inferred 3D wedges/contours**, with visible estimate legend, support radius/hull and uncertainty; default to actual measured columns. No fabricated continuous underground surfaces or auto-interpolation across missing survey coverage.
- Full-project performance target shall be defined and measured with the 400+ real points: opening/rotating/filtering a dense 3D scene cannot block other controls. Provide adjustable quality and fallback to observed 2D if GPU/WebView/Plotly is unavailable.

**Acceptance MAP-01:** Verified CRS/coordinate datasets produce correctly oriented plots and well-scaled 3D columns, with map-to-profile drilldown; missing CRS and outliers generate explicit QA. Test 1, 2, 100 and 400+ points; all-UNKNOWN layers, multiple intermediate silt bands, 9 known source coordinate anomalies, invalid elevations, depth slices, cross-sections, toggles, and screenshots.

### 8.4 ONE complete, auditable XLSX — W07, W09, W11

- Deliver one completed `CPT_Analysis_<run-id>.xlsx` per analysis. **First sheet retains five columns**: SI.No; CPT REFERENCE; Silt start depth after (m); silt depth (m); sand layer thickness before silt (m). Its selection/status conventions must match approved engineering rules, including `REVIEW` and `NO QUALIFYING OBSERVED INTERVAL`.
- Additional tabs in **the same physical XLSX**: Project Dashboard; Full CPT Analysis; Raw/Normalized Depth Measurements (qc, fs, u2, qt, Fr, Qtn, Ic with corrected depth and data-validity reason); Every Soil Layer/Isolated Excursion; Source/Revisions Audit; Methodology & Parameters; Data Quality/REVIEW; Coordinate QA; Raft Summary, Isolated Summary and Liquefaction **only when computed from approved design equations or clearly labeled as imported cached references**; Project Charts; **embedded usable 2D site plan and 3D overview**; Pre/Post Changes and Pairing QA if applicable.
- Every supported CPT and all samples must be present; do not silently truncate above Excel's **1,048,576 rows per worksheet** (split measurements into consecutive numbered sheets and maintain a point index). Preserve raw depths and measured thickness separately from rounded display thickness. No invisible missing CPTs, stale versions or aggregate summaries that disagree with individual sheets.
- Plots should be actual embedded worksheet charts/images, searchable/selectable where technically possible, never dependencies on external PNGs. Coordinate site limits and explicit QA/exceptions must be included in the XLSX.
- Use atomic write/validate/rename, validate no corrupt ZIP, verify actual header order, dimensions, schema, measurement row counts, image/chart objects, formulas (when used), and source manifest after export. `Open Excel` must open the latest **successful** run.

**Acceptance XLSX-01:** 400+ genuine CPT files generate exactly one complete and reopenable XLSX with every accepted CPT, all valid/invalid observed measurements, both map views, reference values clearly labeled, correct dashboard maximum and source audit; deliberately large simulated data exercise multiple measurement sheets; output missing required data must fail QA rather than appear blank.

### 8.5 PDF report completeness and original fidelity — W06, W11

- Each CPT PDF must contain populated project/test identity, test date when known, coordinates, RL, cone ID and area ratio, correct depth range and units, qc/fs/u2/Ic, Qtn–Fr SBT graph with real measured points, legend and method details; any value genuinely absent is printed as **`N/A — reason`**, not an empty row or zero.
- Include a complete appendix: all qualifying layers, measured vs unknown depths, layer start/end/thickness, source QC, verified/reference status, assumptions, and links/keys to the XLSX/project audit. Native raw-only PDFs must be compared with approved Excel-produced pages for geometry and numerical parity.
- If an authoritative original PDF matches the physical raw sounding, preserve its pages unchanged and append a coherent analysis report; never pair by filename alone. Refuse an ambiguous or wrong-location PDF with QA reason.
- User may request full PDF batch, Excel-only mode or report regeneration. By default, produce each accepted CPT PDF once, not duplicates for revised sources.

**Acceptance PDF-01:** PDF text extraction and rendered page screenshots verify **zero unexplained empty mandatory fields**, correct coordinates and reference identity, valid Qtn-Fr points, no overlapping labels/logos/legends, correct pagination and original-page preservation. Test the five annotated raw CPTs plus at least 10 reference PDFs and representative different original export templates.

### 8.6 Professional minimalist visual design — W10

- Visual hierarchy: (1) Project input card with **Open files / Open folder**, (2) large Start button and always-visible progress, (3) preview/result summary, (4) simple **View Excel / View PDFs / View Map**. All engineering complexity moves into optional Expert/QA screens. Remove duplicate/technical launch buttons and gratuitous control rows.
- Cohesive accessible button geometry (consistent min height, hover/focus/disabled/loading states), readable labels, keyboard shortcuts, error/success feedback, sensible empty-state guidance. No controls styled like plain text or cropped at narrow widths.
- Minimal navigation: **Analyze**, **Results**, **Site & 3D**, **All Layers**, **Compare**, **Reports**, **Review / Advanced**; hide charts/tools within the appropriate section rather than a crowded set of competing tabs. No empty pages or technical settings needed to see core results.
- Validate Windows **1024×697 (the user's screenshot size)**, 1366×768, 1920×1080 and 125%, 150%, 200% DPI; use responsive/split/switchable panels. Test long filenames, Arabic/English pathnames, 400+ CPT lists, navigation through chart/3D and dialogs.
- The UI must not depend on Microsoft Excel, internet, CRS discovery, private workbooks or a 3D web backend simply to analyze raw GEF/GFF/PDF and export basic truthful project outputs.

**Acceptance UX-02:** Side-by-side before/after screenshots and automated control inventory prove technical source buttons absent from default screen; every clickable control exercises the advertised action (dialogs included by interactive test), primary buttons always visible, no clipping, no horizontal overflow, and 3D/progress/outputs readily discoverable.

### 8.7 Required cross-workstream test matrix and final release blocker

| Test group | Scenarios | Required evidence / exit |
|---|---|---|
| Input-only user journeys | Single GFF, single GEF, single vector PDF, folder GFF, folder PDF, mixed files, duplicate/revised source, unsupported/raster PDF | Ingested, documented REVIEW or explicit failure for every source; no XLSB reference input required |
| Engine truth | B04/B05/B07/B18/B19, A1-292, B342/B343/B355/B356, missing fs/u2, false starts, thin layer, final dropout, multiple strata | Convergence to approved source interpretation or case-specific REVIEW with reproducible calculations; no fabricated thickness |
| Unified workbook | All five quick columns, all raw samples, all-layer table, embedded maps, detailed QA, imported cached fields labelled, 400+ sources and >1,048,576 rows | One reopenable XLSX per run; every source accounted for, no missing rows or misleading blank fields |
| PDF completeness | Source metadata available/missing, vector plots, Qtn–Fr points, imported original PDFs, all review statuses | Mandatory fields filled or clear N/A reasons; visual regression on ≥10 approved reports |
| Maps and 3D | 1–400+ CPT XY/RL, verified site limits/CRS, 9 outliers, 3D rotate/zoom, depth window, cross-sections, map-to-profile, unknown bands | Correct coordinates and geometry; controls visible, responsive and screenshots reviewed |
| Progress and cancellation | 1 source, 448 PDFs, 400 synthetic, corruption, permission denied, cancel/retry/restart | Monotonic progress, visible stages, UI responsive, partial outputs never published as complete |
| Usability | Normal and high DPI, 1024-wide, 1366, 1920, all buttons and menu shortcuts, original source buttons hidden | Screenshot audit + human Windows full clickthrough; no unresponsive/inert control |
| Repeatability & release | Two re-runs of same real batch, project max calculation, audit logs, output hash, EXE on Windows | Same numerical results and disposition; CI and manual approvals recorded |

**Release rule for this addendum:** Passing only the synthetic benchmark or executable smoke test does not close this work. The product remains **ENGINEERING PREVIEW** until UX-01/UX-02, PROG-01, MAP-01, XLSX-01, PDF-01 and all existing W01–W12 engineering gates are evidenced and approved.

---

## 9. Immediate backlog (start in this order)
1. Fix stale status docs and retire unreachable/competing exporter and analysis paths after parity regression.
2. Implement real 448-PDF batch acceptance runner (reuse `main` PDFs; do not mix with `analysis-work` legacy logic) with a machine-readable per-source exception manifest; baseline without weakening `REVIEW`.
3. Extract/validate source XLSB formula/VBA and run golden real annotated raw soundings; produce a difference matrix and approved algorithm configuration.
4. Implement/test full footing and liquefaction formulas and native report parity with source Excel.
5. Integrate single authoritative XLSX, map/3D and PRE/POST sources, then run full real + synthetic benchmark.
6. Conduct visual/user acceptance; publish only after W12.

**Done means the required capabilities are not just implemented or smoke-tested: every accepted numerical output is reproducible, every source is accounted for, reference discrepancies are explained, 2D/3D maps are supportable, and a qualified engineer approves the selected methods.**
