# CPT A2 isolated-footing + soil-atlas implementation handoff
Updated 2026-10-20. This document is the checkpoint for W05 / W07 / W08 / W10 within [PRODUCTION_CLOSURE_PLAN.md](PRODUCTION_CLOSURE_PLAN.md).

## What the engineer requested
- **Full isolated-footing result in the same sortable CPT results table and the ONE complete project XLSX**, not only an independent graphic.
- Real measured 2D soil categories and legible rotatable 3D blocks, with depth slicing, color labels, point search, and drill-down. Large 71/400+ batches must be usable, not a dense cloud of tiny markers and hundreds of overlapping polygons.
- An incomplete sounding must be differentiated from a genuinely valid zero result or a measured full-window settlement.
- Preserve source/retake conflicts and report the exact known missing BGL ranges. No fake engineering PASS.

## Private 71-GEF dataset (do NOT commit the user archive)
Source input (user uploaded privately): `01 GEF FILES(6).zip` with 71 .GEF soundings (including multiple attempts/revisions).
Source-output XLSX is the user's generated `CPT_Silt_Analysis_20261019_105200_263(4).xlsx`.
Do not upload these proprietary input files or their coordinates to this repository. Public repo tests use synthetic fixtures.

**Local independent numerical coverage check of the archive** using corrected GEF depth, positive qt, 2 cm integration grid, 1.0–5.5m BGL, 3 × 3m footing:
- 71 physically supplied soundings, of which 68 have >=90% sampled-depth coverage, 59 have >=99.5% sampled-depth coverage.
- `CPT-A2-B253-100` initial: last corrected depth ~0.269m, **0%** usable influence data. `...-1`: last corrected depth ~6.080m, **100%**.
- `CPT-A2-B256-100` initial: last corrected depth ~0.559m, **0%**; `...-1`: ~5.785m, **100%**.
- `CPT-A2-B254-100` earlier attempt: ~4.871m last corrected, **86.2% depth coverage**, but approx **94.0% stress-weighted coverage** (lower stress in deep missing tail). This does **not** establish full measured settlement.
- `CPT-A2-B254-100-1` later attempt: ~5.730m last corrected, **100%** sampled influence data. Both attempts are substantial but can disagree on observed soil-layer interpretation. The full numerical run must preserve that source conflict/REVIEW and avoid silently accepting whichever soil interpretation is convenient.
- All fractions are engineering screening coverage, not accepted settlement/FOS; qt-source quality, design load/modulus assumptions and test identity still require confirmation.

## Implemented code (source build, subject to CI)
1. `engineering_geo_atlas.py`: Default SVG 3D now implements a deterministic **700 measured-polygon drawing budget** across CPTs. It fairly rotates through each surveyed CPT, giving the selected CPT priority. **ALL MEASURED LAYERS** mode retains the full source geometry. The view reports displayed/available count, while all original intervals remain in the inspector and workbook. Purpose: fix Microsoft Edge browser regression `default_shapes=1020`, required <900.
2. `engineering_isolated_settlement.py`: Keeps measured-only settlement integration; now calculates sampled-depth coverage **and stress-weighted influence coverage**, records missing BGL runs and missing depth. Important missing zone near footing cannot pass by a misleading nominal depth percentage alone. CPTs flagged REVIEW for source/revision conflict remain calculable for exploratory qt screening but carry an explicit provisional warning.
3. `engineering_isolated_export.py`: ONE XLSX now includes extra per-CPT coverage/stress-depth fields and a dedicated **Isolated Coverage QA** sheet, in addition to Isolated Settlement Results and Isolated Strain Integration and the existing original-source results.
4. `engineering_workspace.py`: Sortable isolated-footing table gains stress coverage and unmeasured BGL range columns. The note explains what is provisional and how many soundings are incomplete.
5. Regression tests added for: near-footing vs deep missing-data severity, complete coverage, under-sounded influence, and REVIEW source that nonetheless contains observed qt.

## Engineering model and reporting discipline
- Existing estimator: simplified rectangular 2:1 stress spread under 3 × 3m isolated footing, default net pressure 150kPa, embedment 1m, influence 1.5B, empirical constrained modulus M = alpha × qt (default alpha=5). It is **provisional** and **NOT equivalent** to the original Excel/XLSB bearing/settlement implementation.
- `calculated_settlement_mm` is only a provisional screening result when both measured-depth coverage and stress-weighted coverage meet the configured threshold; unknown intervals are never filled. `observed_settlement_mm` is partial integrated contribution only.
- Neither a full numeric CPT nor a source-workbook cached PASS authorizes native geotechnical design acceptance. Need engineer-approved load, groundwater, stiffness correlation and acceptable settlement with real benchmark validation.
- Original external isolated source values remain independent from new raw-screening outputs.

## Tests / release gates
- Unit/regression: `cd desktop_app && python -m pytest -q`.
- 68-point interactive offline atlas real Edge browser smoke: `python ci_geo_atlas_browser_smoke.py` on Windows with Microsoft Edge/Playwright. Assert default fewer than 900 3D measured bodies, switch **ALL** above 900, during drag fewer than 720. All points continue to be individually inspectable, horizons/depth search preserved.
- Windows actions: `.github/workflows/build-desktop.yml`; source GUI smoke; original PDF/one XLSX smoke; 400 synthetic CPT benchmark; packaged EXE visual startup and GitHub ZIP artifact.
- Private-data acceptance STILL REQUIRED: rerun all 71 actual GEF files through the packaged Windows app, compare the three B253/B254/B256 retest families, independently inspect per-CPT isolated table rows, output workbook's missing-range QA, verify 2D/3D soil atlas in a real desktop session and capture approved engineer interpretations.
- W05 is **NOT VERIFIED FOR ENGINEERING DESIGN** until independent original-workbook formula parity and geotechnical signoff. W08 requires project CRS/sections and actual site-map topology signoff.
- Never claim all 71 are fully calculated simply because 68 have >=90% nominal depth coverage; 90% may omit influential near-footing depth.

## If work stops — resume in this order
1. Inspect **most recent** GitHub Actions run; previous reproducible failure was run `39370283126`, browser assertion `default_shapes=1020` versus <900. Determine whether new focused-budget patch passes before packaging.
2. If any tests fail, pull specific job logs and correct source/tests. Do not publish another ZIP before GUI/browser smoke and frozen EXE are green.
3. Run private 71-GEF acceptance on the currently attached archive; expected source/retest lengths/coverage above should hold. Reconcile B254 source conflict, without forced source preference.
4. Inspect workbook `Isolated Settlement Results` + `Isolated Coverage QA` together; compare coverage percentages, isolate partial observed contribution, and explicitly explain missing influence depth.
5. Inspect screenshots for 2D colored soil depth slices, default 3D >=10cm vertical visual length and manageable polygons, full-mode complete soil blocks, selected CPT inspector, legends and site boundaries.
6. Only after validations: update `PRODUCTION_CLOSURE_PLAN.md` item-level statuses, publish downloadable Windows ZIP and label **ENGINEERING PREVIEW** unless W05 actual formula parity is approved.

**Critical distinction:** Software build success is not same as geotechnical-design certification.
