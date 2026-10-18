# CPT Engineering Platform — Master Implementation Plan
**State:** Engineering work in progress. CI passing is not proof of validated geotechnical design or parity with proprietary Excel/VBA calculations.

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
