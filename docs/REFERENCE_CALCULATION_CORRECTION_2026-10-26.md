# CPT reference-calculation correction and qualification (2026-10-26)

## Traceable source of the report discrepancy

Two operator-provided Windows ZIP archives each contain one PyInstaller one-file EXE:

| Operator label | SHA256 (uncompressed EXE) |
|---|---|
| `CPT_Silt_Analyzer right calc.zip` | `4025fcf0e0fb5f7e7f76eda362891a6e2b66fdcc9e61be97aee99476498ae390` |
| `CPT_Silt_Analyzer calc deviated.zip` | `337dd86d61ca26511f6104d33eabefc708717838c9d9db3f63d8c71167cc33ac` |

Inspected PyInstaller Python 3.12 archive entries and compressed PYZ module hashes. **`engineering_layers` is byte-identical in both**, while `cpt_core`, `app_pdf_enabled`, `engineering_compact_export`, and other product modules differ. Binary identity alone cannot prove which source-level policy is correct. GitHub source history independently locates acceptance-policy changes (e.g. `aff4b461` in `cpt_core`).

### Restored reference reporting rule

- PRE: calculate the primary screening interval with **3 samples**, sensitivity widths **1/5/7**.
- POST: calculate the primary interval with **10 samples**, sensitivity widths **7/9/11**.
- All four primary/sensitivity results are compared at the existing **0.10 m report precision**. The primary is reportable as VERIFIED (or NO SILT) only when **at least 3/4 windows match**.
- Fewer than 3 agreements: **REVIEW**, no approved final interval, even if the primary shows measured evidence. Preserve observed candidate boundaries/thickness and the depth-wise soil layers.
- A positive sub-resolution interval that rounds to 0.00 m: **REVIEW**, retain unrounded evidence in Excel Review Evidence. Do not silently switch to a 0.01 m accepted reporting convention.
- This is a compatibility and QA rule, **not an independent proof of laboratory USCS silt classification**.

### Retest and source-version safeguards

The newer release's corrected incomplete-sounding detection is retained: a 0.27 m aborted push must not automatically veto a complete 6 m retest. Comparable physically substantial retests that disagree in source interpretation/location/elevation stay **REVIEW**. Their numerical candidates remain accessible in **Full Analysis**, **Source Audit** and **Review Evidence**, but not as accepted numbers in the five-column **CPT Analysis** quick sheet. A human reviewer must adjudicate source identity and interpretation.

### Validation evidence and limitations

The branch adds synthetic unit tests for PRE/POST 3-of-4 decisions, thin observed intervals, NO SILT versus REVIEW, and the Excel quick sheet. It also provides an independent **PR-only** Windows build workflow, which uploads a candidate ZIP without modifying the published `main` release.

**Still required for final approval:**
1. Windows CI unit/GUI/EXE smoke outcome for this exact branch commit.
2. Deterministic side-by-side processing of **the same private GEF/GFF inputs** with the archived 'right' EXE and this candidate, checking the five-column Excel, Full Analysis, Review Evidence, per-CPT layer boundaries and source-selected revision.
3. Explicit discrepancy register for any remaining differences (including source-selection fixes intentionally not reverted).
4. Engineer-approved primary vs supplementary smoothing convention, water table, cone ratio, rounding, soil semantics and original XLSB/VBA parity.
5. Project-authorized signoff before any acceptance claim. Release remains **ENGINEERING PREVIEW** until independent design validation.

Raw private geotechnical files and their coordinates are intentionally not added to the public GitHub repository.
