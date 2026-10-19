# CPT Engineering Studio — verified implementation status
**Updated:** 2026-10-19

## Latest Windows software verification

- [Windows build and automated verification](https://github.com/karimelzoser/analyze/actions/runs/39179048160): **success**, **124 automated tests passed**; source GUI opened all eight workspaces; Windows frozen EXE launched via smoke and normal double-click startup paths.
- Synthetic end-to-end source test: raw GEF → CPT PDF plus analysis appendix and exactly **one comprehensive XLSX** with 2D and 3D embedded maps.
- Synthetic 400-CPT benchmark passed; recorded total approximately **13.98 seconds**, excluding generation of every individual PDF. This is not a real-project performance guarantee.
- Windows published release archive: `release/CPT_Silt_Analyzer_Latest.zip`, containing `CPT_Silt_Analyzer.exe`.
- All-source [448 real PDF project acceptance](https://github.com/karimelzoser/analyze/actions/runs/39178894856): **success**, **448/448 physical PDFs parsed**, 0 parser failures, 418 unique CPT project families.

## Real-source classification outcomes

| Result | Unique CPTs | Engineering meaning |
|---|---:|---|
| PDF algorithm VERIFIED | 301 | Numerically consistent PDF-vector extraction under current project screening model; NOT geotechnical design certification |
| NO SILT | 100 | No qualifying sustained Ic-screen interval; not proof of absence of laboratory fines |
| REVIEW | 17 | Preserves unresolved but visible measurement evidence |
| **Total** | **418** | One project result per family; 448 physical files, 30 duplicates/revisions |

Of 17 REVIEW rows: **12 measured positive thin Ic-screening intervals** (around 0.05–0.08m) need an approved reporting precision/convention, **5** involve conflicting physical source revisions. Full references, depths, categories and actions are in [Real PDF Engineering Findings](REAL_PDF_448_ENGINEERING_FINDINGS.md) and the `Review Resolution` tab of the complete downloadable project Excel.

## Implemented

- Source selection, GEF/GFF and supported vector PDF input, corrected depth and Ic engineering screening, dropout/precision guards, all-layer source audit and evidence preservation.
- Interactive eight-workspace Windows UI, quality review tab, all CPT layer graphs, source trace, depth-wise Pre/Post comparisons, foundation reference import and explicit engineer-entered acceptance thresholds.
- Survey-grid 2D map, rotatable/offline 3D CPT observed profile model and 3D interactive HTML explorer with high-risk screening and optional interpretive wedges. Never present a wedge as a measured soil boundary.
- One cohesive Excel output: first five-column CPT Analysis, overview, raw numerical measurement tables, raw source headers/metadata, all soil layers, review evidence and review resolution, coordinates/embedded 2D+3D maps, chart objects, source audit; original XLSB and foundation/pre-post datasets appear only when explicitly provided.
- CPT PDF reporting keeps unavailable metadata clearly N/A. A matching official reference PDF may be preserved unchanged with analysis appendix; an unmatched raw-only report remains source-style rather than unproven pixel-identical.
- Original 40MB XLSB workbook has read-only cached data and categorical SBT zone ingestion (447 CPT reference profiles, 448 saved raft rows). Separate optional Excel COM print and formula recalculation pathway exists for Windows machines with Microsoft Excel.

## Not independently verified / blocking genuine engineering certification

1. **Exact source XLSB/VBA formula parity across arbitrary raw CPTs**: source caches and sample QA exist, but complete exact normalized Ic/fines/settlement formulas and live Excel/VBA behavior were not independently reconciled under an Excel-equipped session.
2. **Full native raft/isolated design-model validation**: reference settlement/FOS results can be imported and compared to explicitly given limits, but accepted underlying stress, layer modulus, constitutive and liquefaction equations have not been independently reconstructed and design-signed-off.
3. **New raw-only PDF pixel fidelity**: original matched PDFs are preserved; the generated renderer has not been certified geometrically identical for every source Excel chart/print configuration.
4. **Geotechnical adjudications**: twelve real thin-layer precision cases, five source-revision conflicts, A1-292 native-vs-source silt discrepancy, and B04 terminal sensor censoring remain openly flagged until project-authorized rules or original field evidence resolve them.
5. **Survey CRS/ground surface**: project Easting/Northing plots use surveyed coordinates; local grid CRS and 9 implausible source coordinates need site survey verification. Do not present interpolated contours as measured facts.

**Release classification: Tested engineering preview — NOT engineer-certified for ground improvement design or acceptance.** A passing software test verifies its stated outputs and workflow, not proprietary worksheet/VBA assumptions or the actual ground conditions.
