# Real 448-PDF source acceptance — observed results (2026-10-19)

**Scope:** Existing publicly committed project PDFs in `pdfs/pdf_Single/`; vector-PDF interpretation, revision selection, all-in-one Excel, and source audit. This is **software/source processing evidence**, not geotechnical design approval or exact source-XLSB formula equivalence.

## Execution evidence
- [Successful Windows run 39175504701](https://github.com/karimelzoser/analyze/actions/runs/39175504701), source commit `53f27a3ba3fafc957d28634e25a0061c23dc72d0`.
- Two test cases using original CPT report fixtures passed; all 448 physical PDFs were then analyzed and written to a single project XLSX.
- **448 / 448** actual PDF files parsed, **0** parser errors.
- **418** unique CPT identities, **30** physical duplicate/revision copies.
- Final project status: **301 VERIFIED**, **100 NO SILT** (no sustained measured project-Ic-screen layer), **17 REVIEW**.
- Physical file status: **304 VERIFIED**, **103 NO SILT**, **41 REVIEW**.
- Observed Windows job processing plus workbook runtime: **130.52 seconds**; does not include generating 418 separately appended PDF output reports.
- [Workflow artifacts](https://github.com/karimelzoser/analyze/actions/runs/39175504701#artifacts): `Real_Project_PDF_Acceptance.xlsx` (one combined project workbook, 15.3 MB unpacked), `PDF_Source_Manifest.csv` (SHA256 per file), `PDF_Source_Audit.csv` (every physical revision), `PDF_Acceptance_Result.json` (exact exception reasons).

## Precisely why 17 unique CPTs remain REVIEW
**Twelve observed thin positive intervals:** original native-vector Ic trace supports positive layer thickness *below* the 0.10m reporting convention. Do not silently round to zero or manufacture 0.10m measured thickness.

| CPT | Approximate observed interval (m BGL) | Observed thickness |
|---|---|---:|
| CPT-A1-306-100 | 5.160–5.210 | 0.051m |
| CPT-A1-B56-100 | 4.851–4.921 | 0.070m |
| CPT-A1-B86-100 | 1.680–1.739 | 0.059m |
| CPT-A1-B90-100 | 4.989–5.039 | 0.050m |
| CPT-A1-B101-100 | 4.650–4.720 | 0.070m |
| CPT-A1-B104-100 | 1.979–2.041 | 0.062m |
| CPT-A1-B136-100 | 4.690–4.740 | 0.050m |
| CPT-A1-B149-100 | 4.949–5.030 | 0.081m |
| CPT-A1-B176-100 | 4.951–5.021 | 0.070m |
| CPT-A1-B227-100 | 5.651–5.710 | 0.059m |
| CPT-A1-B259-100 | 5.558–5.628 | 0.070m |
| CPT-A1-B268-100 | 2.060–2.130 | 0.070m |

**Five source-revision conflicts:** `CPT-A1-B67-100`, `CPT-A1-B275-100`, `CPT-A1-B277-100`, `CPT-A1-B300-100`, and `CPT-A1-B327-100`. The app conservatively flags conflicting classification, surveyed position or elevations across physical revisions. Survey/source approval is required before selecting one as a final accepted physical interpretation.

## Workstream closure interpretation
- **W04 actual-PDF ingestion and accounting:** executed. Every source has a manifest and status, with no hidden parse errors; 17 decision cases remain open.
- **W07 all-in-one project XLSX:** executed on actual 418 unique PDF results. The workbook has the 5-column quick sheet plus QA/charts and embedded 2D/3D preview figures. Real PDF inputs do not contain raw numerical fs/u2/qc depth series with the reliability of GEF/GFF; absence is explicitly documented rather than invented.
- **Not closed:** original XLSB formula/VBA parity, independent raft/isolated/liquefaction calculations, live Microsoft Excel plotting parity for new raw files, approved survey CRS, detailed Windows human UI interaction at all DPI settings, and engineer approval for all exceptions.

## Next engineering decisions (not software guesses)
1. Define accepted reporting policy for raw positive intervals less than 0.10m: preserve full precision, approve a separate displayed-thickness rule, or keep as thin-layer REVIEW.
2. Obtain approved revision/true-test identity for the five conflicting families and compare reference GEF/GFF where available.
3. Run full source-XLSB case parity and original PDF rendering comparison, particularly around A1-292 and B342/B343/B355.
4. Validate footing stress, settlement and liquefaction against the project design criteria before any PASS/FAIL certification.

The latest release ZIP remains **ENGINEERING PREVIEW** until source equations, project geotechnical criteria and survey decisions are approved.
