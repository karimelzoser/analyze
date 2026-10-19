# Actual 448-PDF project acceptance and REVIEW resolution — 2026-10-19

This audit is based on the repository's **real 448 original CPT PDFs**, not synthetic files. It records what the application was able to extract and what still requires geotechnical adjudication. The latest machine-readable records and complete all-in-one engineering workbook are published as a GitHub Actions artifact by [Real CPT PDF Source Acceptance](../.github/workflows/real-pdf-acceptance.yml).

## Completed automated source checks

- Physical PDF inputs: **448**
- Successfully opened and parsed: **448**; parser exceptions: **0**
- Unique CPT families: **418** (30 duplicate/revision source files)
- Project family outcomes: **301 VERIFIED by the PDF algorithm, 100 NO SILT under the project persistence rule, 17 REVIEW**.
- **WARNING:** An algorithmic VERIFIED classification does not mean laboratory USCS identification or engineer-approved ground-improvement design.

## Why 17 CPTs remain REVIEW

The current evidence separates **12 thin positive measured Ic screening intervals** from **5 conflicting source revisions**. These are not 17 simply unreadable PDFs. The observations below are direct approximate values from the extracted vector chart, in metres below ground; original unrounded values remain in the main Excel and JSON source audit.

| CPT | Observed start | Observed end | Observed thickness | Resolution |
|---|---:|---:|---:|---|
| CPT-A1-306-100 | 5.160 | 5.210 | 0.051 | Reporting precision policy |
| CPT-A1-B56-100 | 4.851 | 4.921 | 0.070 | Reporting precision policy |
| CPT-A1-B86-100 | 1.680 | 1.739 | 0.059 | Reporting precision policy |
| CPT-A1-B90-100 | 4.989 | 5.039 | 0.050 | Reporting precision policy |
| CPT-A1-B101-100 | 4.650 | 4.720 | 0.070 | Reporting precision policy |
| CPT-A1-B104-100 | 1.979 | 2.041 | 0.062 | Reporting precision policy |
| CPT-A1-B136-100 | 4.690 | 4.740 | 0.050 | Reporting precision policy |
| CPT-A1-B149-100 | 4.949 | 5.030 | 0.081 | Reporting precision policy |
| CPT-A1-B176-100 | 4.951 | 5.021 | 0.070 | Reporting precision policy |
| CPT-A1-B227-100 | 5.651 | 5.710 | 0.059 | Reporting precision policy |
| CPT-A1-B259-100 | 5.558 | 5.628 | 0.070 | Reporting precision policy |
| CPT-A1-B268-100 | 2.060 | 2.130 | 0.070 | Reporting precision policy |

Source-revision discrepancies needing adjudication: **CPT-A1-B67-100, CPT-A1-B275-100, CPT-A1-B277-100, CPT-A1-B300-100, CPT-A1-B327-100**. Review original physical test identity, coordinates, ground datum, and source revision; do not select an arbitrary value because a PDF export is newer.

**Engineering action needed:** Choose the project's sanctioned treatment for observed thin intervals at 0.1m reporting resolution. Options may include retaining measured thickness to 0.01m (with uncertainty disclosure), explicit `<0.1m` notation, or engineered categorical thin-layer notes. Never fabricate a 0.10m *measured* layer from an observed 0.050m interval. Source conflicts are distinct and cannot be automatically resolved by a thickness policy.

## Five manually annotated GEF/GFF soundings: independent numerical cross-check

An independent Robertson-style Ic calculation was made on the raw GFF records using corrected depth, input `a=0.75`, assumed `gamma=18 kN/m³` and groundwater BGL `2m`, and observed `fs > 0`. These are not reproductions of the original XLSB/VBA exact equation and smoothing order.

| CPT | Engineer annotation | Raw sustained Ic ≥2.60 interval | Interpretation |
|---|---|---|---|
| CPT-A1-B18-100 | Silt 0.20m | about 4.289–4.479m, 0.19m | Consistent to project precision |
| CPT-A1-B19-100 | Silt 0.30m | about 4.309–4.549m, 0.24m | Near the 0.1m reported result; filtering shifts limits |
| CPT-A1-B05-100 | NO SILT | None qualifying minimum persistence | Consistent |
| CPT-A1-B07-100 | NO SILT | None qualifying minimum persistence | Consistent |
| CPT-A1-B04-100 | Silt 0.20m | about 4.239–4.358m, 0.12m before invalid fs tail | **Not fully reconciled**; do not extend missing sensor data automatically |

Observed numerical runs can depend on smoothing, unit weight, groundwater and endpoint interpolation. These values must not be treated as independently approved design strata.

## A1-292 discrepancy

The project PDF extraction produced approx **6.20 / 0.20 m** while the original XLSB saved SBT zone sequence supports approximately **6.20 / 0.10 m**. The difference cannot be eliminated by blindly rounding or extending into invalid `fs=0` data. Native-vs-reference QA must keep both results, processing settings, and the discrepancy visible.

## Implemented correction and remaining release gate

- The single project Excel includes `Review Evidence` and **`Review Resolution`** when needed.
- The app's QA interface displays observed positive thin-layer thickness (e.g., `0.070 OBSERVED`), even when the official engineering status remains `REVIEW`.
- The real PDF acceptance JSON includes categorized review counts and a measurement-preserving resolution register.
- The application can read saved source XLSB foundation and soil-zone values and use Excel itself for optional recalculation/printing on a licensed Windows computer.

**Still not certified:** The proprietary original XLSB formula/VBA parity, the native raft/isolated settlement and liquefaction-FOS calculation equations, exact raw-only report pixel parity, real field survey CRS and the unresolved geotechnical adjudications. A passing Windows build or source parsing is not a substitute for licensed geotechnical approval.
