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

## 8. Immediate backlog (start in this order)
1. Fix stale status docs and retire unreachable/competing exporter and analysis paths after parity regression.
2. Implement real 448-PDF batch acceptance runner (reuse `main` PDFs; do not mix with `analysis-work` legacy logic) with a machine-readable per-source exception manifest; baseline without weakening `REVIEW`.
3. Extract/validate source XLSB formula/VBA and run golden real annotated raw soundings; produce a difference matrix and approved algorithm configuration.
4. Implement/test full footing and liquefaction formulas and native report parity with source Excel.
5. Integrate single authoritative XLSX, map/3D and PRE/POST sources, then run full real + synthetic benchmark.
6. Conduct visual/user acceptance; publish only after W12.

**Done means the required capabilities are not just implemented or smoke-tested: every accepted numerical output is reproducible, every source is accounted for, reference discrepancies are explained, 2D/3D maps are supportable, and a qualified engineer approves the selected methods.**
