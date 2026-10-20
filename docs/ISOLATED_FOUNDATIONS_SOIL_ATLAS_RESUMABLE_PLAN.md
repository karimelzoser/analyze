# Resumable engineering delivery plan — isolated foundations + navigable 2D/3D soil model
**Created:** 2026-10-20 | **Repo:** karimelzoser/analyze
**Rule:** Each completed subtask requires a GitHub commit and test evidence. Do not declare complete merely because CI builds; preserve incomplete items below for the next session. **Do not replace missing settlement values with 0 or guessed "PASS".**

## Files / evidence
- Latest source XLSX: `Pre CPT Summary.xlsx` → `Isolated Summary` has 393 populated CPT references, but 214 have **blank settlement (mm)**; some source "Settlement check" cells read **Pass** even where saved settlement exceeds 40 mm. This is a source QA inconsistency.
- Original `CPT analysis v2.5.7 - pore pressure 1.xlsb`: saved project foundation reference data, model templates, site boundary / CPT charts, but many changing inputs/outputs lack independently approved formula parity.
- User's `CPT_Interactive_2D_3D_Atlas(2).html` is a large self-contained Plotly atlas with heavy observed soil-block geometry and cluttered many-point inspection.
- Source `01 GEF FILES(6).zip` contains 71 GEF soundings; use for real acceptance where source data match the summary.
- All uploads private. **Do not commit original XLSB or confidential GEF/Excel into the public repo.**

## Contract: isolated foundation results
1. **Source audit:** import both `Raft Summary` and `Isolated Summary`, keeping settlement, FOS, geometry, date, coordinate, source-check and absent values distinct. Deduplicate by physical point coordinates/date/test, **not** arbitrary CPT string. No unconditional "Pass".
2. **Native calculation:** implement a transparent bounded **CPT-derived settlement estimate** for isolated footing, using engineer-supplied footing width/length, design pressure, embedment and calibrated constrained modulus factor. Vertical stress distribution and numerical depth integration, only across valid observed sounding. Missing depth/pressure/modulus cannot generate a certified value. Categorize result as ESTIMATE / INCOMPLETE_COVERAGE / SOURCE_CACHED / APPROVED_REVIEW.
3. **Source reconciliation:** compare computed values to nonmissing original summary values at the same physical location. Show differences and model assumptions. Never fit unknown geotechnical coefficients just to force agreement.
4. **One consolidated Excel:** `Isolated Footing` main results (including all 393 source rows), `Foundation Inputs`, `Foundation Calculations` (depth-by-depth stress / strain / coverage), `Foundation QA` and updated dashboard; preserve *raw CPT 5-column* overview, all 2D/3D charts and raw measurement tables. Show source blanks explicitly as `NOT PROVIDED`.
5. **UI:** selection between Raft vs Isolated, numeric parameter panel with units and provenance, sortable results grid, drill-down stress/strain profile, visual warnings, source-vs-native toggle and reproducible export.

## Contract: soil visualization
1. **2D depth slice:** depth and thickness-window sliders; measured categorical SBT at actual CPT coordinates; locally bounded colored Voronoi/triangular regions and transparent low-confidence hatching; no interpolation across major holes, outside survey boundary, or unknown sensor runs.
2. **3D subsurface:** progressive level-of-detail spatial soil volume / fence slices derived from measured CPT intervals and *explicitly flagged* limited interpolation. Implement clipping/exploded sections; controls for profile count, vertical exaggeration, layer legend, uncertainty, and selectable CPT drilldown. Never render thousands of text labels or all thin soil blocks simultaneously by default.
3. **Usability:** start on full-site 2D soil slice; 3D on demand; sidebar with CPT search, area selector, depth slider, category filters and selected-layer info; UI keeps 60 FPS-like responsiveness by limiting geometry. Export map snapshot and data source audit into **one output XLSX**, and HTML saved separately only if user explicitly requests it.
4. **Engineering quality:** if no valid neighboring CPT supports a pixel/voxel, show UNKNOWN, not sand; use colors consistently across all 2D, 3D, Excel, PDF/legend. Distinguish measured from interpolated and report sample distance.

## Test requirements / release gates
- Source workbook fixture: 393 isolated rows, 214 blank settlement values, source flags inconsistent with 40 mm criterion; these must survive import/export without inferred pass.
- Formula unit tests: elastic settlement dimensional limits, surcharge zero, higher qc modulus reduces settlement, increasing net load increases settlement, invalid/insufficient coverage blocked; explicit calibrated parameters.
- Real 71 GEF batch: location reconciliation, baseline comparison, coverage report, no invented settlements for missing tests; recorded exceptions.
- Browser visual smoke: 2D slice depth changes colors, search selects exact CPT, 3D clipping/filter works, sampled points not mislabeled as interpolated; 1024×768 and 1440×900 screenshots.
- UI source + packaged Windows EXE launch tests, full Excel workbook structure and formulas/data audit.
- Production engineering sign-off still needs a qualified engineer to accept the selected CPT-to-modulus correlation and stress/settlement method; the output is **estimated** until then.

## Implementation checkpoints — KEEP UPDATED
- [x] PLAN documented as this Markdown file.
- [ ] FOUNDATION-A: deterministic and auditable source import / missing data / passing rules.
- [ ] FOUNDATION-B: native isolated-footing settlement estimate with transparent inputs and coverage QA.
- [ ] FOUNDATION-C: UI + merged Excel outputs / source-vs-estimated results.
- [ ] MAP-A: fast 2D categorical depth-slice viewer + uncertainty mask.
- [ ] MAP-B: navigable 3D soil model (clipping, fences, observed/interpolated toggle, search).
- [ ] MAP-C: screenshot/performance/regression tests at full 71-source data scale.
- [ ] RELEASE: successful Windows tests+artifact publication, visual review and clearly stated engineering limitations.

## Resumption protocol
1. Read this file **and** `docs/IMPLEMENTATION_STATUS.md`, inspect `.github/workflows/build-desktop.yml` and latest workflow results.
2. Check uncommitted/incomplete files in `desktop_app/engineering_foundations.py`, `engineering_workspace.py`, `engineering_geo_atlas.py`, `engineering_soil_maps.py`, `engineering_unified_excel.py`.
3. Match each task above to a commit SHA and CI run. Never mark a checkbox based on a tool call alone.
4. Continue from the *first unchecked* subtask. Do not overwrite real source results or collapse REVIEW into VERIFIED solely to improve counts.
5. Run `python -m pytest -q` in `desktop_app`; then GitHub Windows workflow. Publish latest EXE only after automated tests, GUI smoke, HTML browser smoke and workbook validation succeed.
6. Log actual last completed task, validation results, remaining dependencies and release path at bottom of this file.

## Implementation evidence and source-data finding (2026-10-20)

**Critical discovery:** The 71 new A2-B190..B272 GEF references have **zero matching CPT references** in the supplied historical `Pre CPT Summary.xlsx` isolated sheet. Source results must therefore be preserved while the new raw CPTs receive *separate* provisional screening rows; do not merge by nearby position or fabricate historical settlement.

**Coverage:** New sounding corrected depth: 0.269 m to 6.687 m; median 5.709 m. None reaches 7.0 m BGL. A 3×3 m isolated footing at 1m embedment screened to 2B below base needs 7m; this would be INCOMPLETE for every one of these new GEFs. The implementation allows explicitly provisional 1.5B screening (to 5.5m BGL) and reports the depth window. 1.5B screening is NOT a complete approved settlement solution.

**Implemented commits / files**
- `a57bce6` `engineering_isolated_settlement.py`: deterministic 2:1 stress increment and calibrated-modulus-factor strain summation, no extrapolation, explicit valid coverage and trace data.
- `775c444` `engineering_isolated_export.py`: separate source vs native values, full missing-value provenance, **Isolated Settlement Results**, **Isolated Strain Integration**, and **Isolated Model QA** worksheets.
- `d0ba3f7`, `b69fbf9`: append native screening to the unified workbook even without historical foundation summaries.
- `e5aa80d`, `7e3113e`: Foundations UI calculation inputs, sortable source+new-CPT table and colored map of screened settlement.
- `8626fba`, `ccfb803`: 3D horizon slab stacks and default focused section + on-demand full measured-layer control, preserving per-point inspection and measurement/interpretation warnings.
- `74a786e`: browser smoke now tests focused default, full-detail toggle and drag preview.
- `c91f464`, `4dac034`: regressions for 393 source/214 missing entries, pressure vs modulus, deep unsounded profiles, and entirely unmatched new raw CPT campaign.
- Initial CI at `c91f464` found 3 **test assertion** issues (shared string locations and nonmatching pressure-window input); updated test commits `4e47eeb` and `f37ca17`. Await latest complete Windows run; do not call completed until PASS.

### Unresolved tasks after code implementation
- [ ] Confirm latest **full** GitHub Actions run passes numerical + browser + source GUI + frozen EXE.
- [ ] Inspect recent 1440×900 and 1024×768 browser screenshots for the 2D categorical soil map and stacked 3D volume, fix any clipped controls.
- [ ] Benchmark actual 71 raw GEFs privately (not committed) against 393 source rows and summarize valid/partial/excluded coverage; no source overlap expected.
- [ ] Confirm per-location input and approved empirical qt→M factor with project engineer; **must not claim licensed settlement design PASS**.
- [ ] Test full source XLSB + historical `Pre CPT Summary.xlsx` integration on Windows with Excel availability as applicable.
- [ ] Publish tested release ZIP and link latest SHA/run in this file.

## Status log
2026-10-20: Confirmed via supplied `Pre CPT Summary.xlsx` workbook: 393 isolated source rows, 214 missing isolated settlement values; source settlement flags can read Pass despite >40 mm. Code work follows after this plan commit.
