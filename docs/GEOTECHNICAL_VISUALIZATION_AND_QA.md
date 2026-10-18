# Geotechnical visualization & software reliability — 2026-10-18

## Design principle
A set of raw CPT measurements is **not** a proved continuous 3D lithological formation. Report what the soundings show, distinguish unobserved intervals, and visually separate interpretation from measurement. Screening classifications are not accepted design PASS/FAIL criteria.

## New desktop map workflow
- SITE MAP → **Risk screening plan** is the default. It draws real Easting/Northing coordinates and the original Site Limit plan if imported.
- Adjustable WATCH and HIGH thickness limits (defaults 0.10 / 0.30 m) are **attention thresholds**, not regulatory/design criteria.
- All qualifying HIGH points are in an inspectable, clickable table, including ties. Click CPT pins to open complete measured depth profiles; toolbar pan, zoom, home and save PNG.
- Optional transparent indicative shading uses linear triangulated interpolation only inside supported neighboring CPT triangles. Long edges between distant data, outside-hull regions, and project-boundary crossings are excluded; no arbitrary positive results outside measured coverage. Unknown source locations are flagged and withheld.
- The offline 3D browser view is opened from the app and can be saved as a standalone `html` file with local Plotly.js assets. The model offers camera controls, rotating/zooming, hover data and legend-based visibility toggles.

## 3D evidence classes
1. **Observed:** vertical CPT sensor/source-zone intervals at measured XY and ground elevation. Source XLSB zones are original saved categorical codes 1–9, **not calculated continuous Ic**.
2. **Inferred with limited spatial support:** a triangular transparent fine-grained-like wedge only when all three nearby CPTs have qualifying depth intervals with at least 0.05 m shared vertical elevation and local XY spacing within a conservative distance gate. Wedges are entirely inside supported CPT triangles.
3. **Unknown/unobserved:** areas beyond surveyed support, broad CPT gaps, sensor dropout, ambiguous source identity, or horizons with noncorrelatable layers. No automatic geotechnical continuity is shown.

Spatial method references:
- AGSi model sections and fence guidance: https://ags-data-format-wg.gitlab.io/agsi/AGSi_Documentation/Guidance_Model_Sections/
- ArcGIS Pro Fence Diagram: https://doc.esri.com/en/arcgis-pro/latest/tool-reference/3d-analyst/fence-diagram.html
- SciPy unstructured-data interpolation (convex hull and triangulated support): https://docs.scipy.org/doc/scipy/tutorial/interpolate/ND_unstructured.html
- Plotly 3D mesh interactive plotting: https://plotly.com/python/3d-mesh/

## Compact analysis deliverable
Exactly **one XLSX** is delivered per current batch; the source data, QC and images are embedded within the workbook. Regular sheets:
- Summary (KPIs, **every** HIGH screening CPT, compact site plan)
- CPT Analysis (user-specified five columns)
- Full Analysis
- All Soil Layers
- CPT Measurements (complete numerical depth-by-depth measured curves; no silent 1,048,576-row truncation)
- Project Maps (measured 2D plan & vertical model image)
- Source Audit (revision/measurement warnings)

The **Coordinate QA** sheet is added **only when** there are source coordinate exceptions. Optional **Foundation Results**, **Reference Comparison**, **Original SBT Curves** and **Pre Post Changes** appear only when respective source documents/results are available. Instruction-only Methodology, duplicate chart tabs, and empty foundation tabs were removed. Calculation methodology is in the in-app **HELP · EQUATIONS** dialog instead.

## Reliability and error path
- Worker exceptions are trapped and generate `CPT_Processing_Failure.log` in the output folder. The GUI returns to enabled controls instead of remaining permanently busy.
- A failed export cannot leave a corrupt "latest" Excel workbook: the exporter writes `.partial.xlsx`, validates completion by closing it, then atomically renames it to final.
- The Open Excel resolver ignores `.partial.xlsx` and temporary `~$...` files.
- Every unreadable-input case is a visible batch error rather than an empty "success" report.
- Real Windows CI covers tests, normal GUI launch, all tabs/screenshots, synthetic GEF→PDF/XLSX test, 400 CPT synthetic processing, offline 3D browser asset creation, PyInstaller packaging, and frozen EXE startup.
- CI verifies software behavior, **not** geotechnical design approval, full original XLSB/VBA numerical parity, or real-world soil layer continuity.

## Important project decisions still subject to approval
- The Ic >=2.60 criterion is a project screening convention, not laboratory USCS. Validity and thin-layer persistence controls cannot be loosened simply to suppress REVIEW.
- Source groundwater/unit-weight/area ratio must follow actual test/project methods, not hardcoded Excel defaults.
- Design weak-point/ground-improvement acceptance needs approved settlement, liquefaction, qc and other applicable engineering criteria; thickness-only map colors must not be labelled true engineering PASS/FAIL.
