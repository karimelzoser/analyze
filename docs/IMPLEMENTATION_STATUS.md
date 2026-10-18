# CURRENT STATUS — 2026-10-18 (supersedes historical snapshot below)

**Engineering status:** Feature-complete in substantial areas, **not geotechnical-production validated**.

- Current successful Windows Actions run: [39164020555](https://github.com/karimelzoser/analyze/actions/runs/39164020555). **104 automated tests passed**; normal GUI and frozen EXE launched successfully.
- Synthetic performance benchmark: **400 generated GEFs**, each ~130 readings; 3.63s numeric analysis + 11.17s XLSX + 3.10s four map renders, **17.90s total**. No evidence of the full physical PDF/report workload from that timing.
- Repository contains **448 real PDF input files** and **zero committed GEF/GFF inputs**; the current Windows CI **does not** execute the whole 448-PDF acceptance campaign.
- Original XLSB engineering formula/VBA numerical equivalence, native raft/isolated/liquefaction formulas, exact new PDF report parity, and engineer-signed project criteria remain OPEN as [#2](https://github.com/karimelzoser/analyze/issues/2), [#3](https://github.com/karimelzoser/analyze/issues/3), [#4](https://github.com/karimelzoser/analyze/issues/4).
- Consolidation remains: multiple older entrypoints/exporters; `reporting_export_v2.export_excel` delegates to compact exporter while old exporter code is unreachable; legacy `analysis-work` PDF engine is separate from current desktop engine.
- **Execution and pass/fail criteria:** [Production Closure Plan](PRODUCTION_CLOSURE_PLAN.md) (W01–W12). This document is authoritative for pending work and release classification.

---

## Historical snapshot (2026-10-18; no longer authoritative)


**Latest tested Windows build:** GitHub Actions [run 39142811473](https://github.com/karimelzoser/analyze/actions/runs/39142811473), source commit `ce02302af706088b34fdb46fce7cccb54f0d07bb`, **49 automated tests passed**. Source GUI and frozen PyInstaller EXE launched and navigated all 7 tabs successfully. End-to-end source GUI smoke processed one synthetic GEF -> one CPT PDF (with analysis appendix), comprehensive Excel workbook, and 4 project maps. Release ZIP published to `release/CPT_Silt_Analyzer_Latest.zip`, approximately 70.5 MB.

## Deliverables and evidence

| Workstream | Delivered / tested | Outstanding engineering approval |
|---|---|---|
| Raw sensor and layer calculations | Terminal fs dropout never silently extends *measured* silt; censored terminal and zero-rounded thin interval become REVIEW. Synthetic regression tests and batch integration. | Original XLSB formula order and numeric parity; five real engineer-annotated GEF results; B292 discrepancy |
| Multilayer stratigraphy | All observed Ic SBT bands, silt threshold crossings, brief spikes, UNKNOWN gaps; raw/pre-3/post-10 views; all layers Excel exports. | Exact smoothing order and SBT persistence rule against reference workbook |
| Source identification | GEF/GFF/PDF revisions audited; conflicting repeated CPT references retained as ambiguous in pre/post. | Survey-date and project survey identity verification on real files |
| Individual/project charts | Interactive charts, individual raw Ic and layers, 4 offline project point maps. | Detailed visual QA for full project and accurate coordinate reference system |
| Foundation reference | Existing Raft/Isolated XLSX input, settlement/FOS map, explicit settlement/FOS thresholds and source-check discrepancy workbook. | Native verified design formula implementation and project acceptance criteria. **No independent PASS asserted** |
| Pre/Post summary and raw depth | PRE/POST summary import, coordinate-safe matching, delta bars/maps, XLSX. Raw qc/fs/u2/qt/Fr/Qtn/Ic depth pairing with harmonized or 3/10 windows; PNG, PDF and XLSX export; missing-sensor and spatial tests. | Paired real PRE/POST field data and engineering approval for changed groundwater/elevations |
| Reference XLSB audit | Local read-only binary-workbook chart/range/cached-data inventory; optional Windows Excel formula snapshot script disables macros and external link updates. | Actual complete formula/VBA extraction and equation-level parity not yet achieved |
| PDF fidelity | Original input PDF preserved byte-equivalent in visual rendering; visual difference tool and exact-pixel false-positive regression. GEF reference-like report and analysis summary still provided. | Reference XLSB printed-report *exact* visual reproduction remains unverified |
| Excel | Original 5 columns plus Full Analysis, All Soil Layers, Layer Statistics, Summary, QA, Source Audit and charts; end-to-end XLSX created in Windows smoke. | Reference model B292 and formatting signoff |
| UI/performance | Windows opens/maximizes UI with 7 workspaces; GUI startup from source and packaged EXE; end-to-end worker; parallel raw, serial PDF. | Human Windows clickthrough (file dialogs/associations) and 400+ real source batch timed performance benchmark |

## Unresolved source dependencies
1. Workbook **CPT analysis v2.5.7 - pore pressure 1.xlsb** is binary and includes VBA. Its 49 native chart definitions and numeric cache references were inspected; this does *not* constitute validated Excel formulas. A qualified engineer with licensed Windows Excel can execute `desktop_app/tools/export_excel_reference_formulas.ps1` read-only with macros disabled to provide a formula snapshot for reconciliation.
2. Five engineer-annotated raw GEF tests and A1-292 **6.20/0.20 (legacy analyzer)** vs summary **B292 6.20/0.10** discrepancy need independent numerical acceptance. The new sensor handling intentionally changes earlier results; do not assume a historical VERIFIED figure remains valid.
3. Settlement and liquefaction-FOS calculations require validated project loads, layer stiffness assumptions, ground water, stress model and code/design acceptance limits. The app validates **imported results** against user-supplied limits but does NOT independently design raft/isolated footings.
4. A geodetic CRS is required for a geographically correct base map. Maps today are in local measured Easting/Northing; contour interpolation is not presented as measured fact.
5. Full PDF exact parity cannot be guaranteed without native original Excel print output matching from the same current input dataset and visual sign-off.

## Engineering release classification
**ENGINEERING PREVIEW — NOT CERTIFIED FOR DESIGN SIGN-OFF.**
The Windows tests prove source, reporting, GUI, frozen EXE and synthetic end-to-end workflow function. They do not prove all engineer-approved source equations, footing acceptance, or every one of 400+ real CPT reports has been independently checked.
