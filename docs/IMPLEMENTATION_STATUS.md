# Implementation status — 2026-10-18
**Latest tested Windows build:** GitHub Actions run 39139010989, commit 165a3538d60142cf063b684d755c11b0e2e9f31e, 39 automated tests passed; built ZIP in release/CPT_Silt_Analyzer_Latest.zip. Publication commit f9f9929. Package ≈70.5MB.

## Delivered and exercised by CI
| Workstream | Delivered | Important qualification |
|---|---|---|
| WS1 raw sensor logic | No automatic fs-dropout extension; thin raw censoring marked REVIEW | Exact parity with original XLSB still unverified |
| WS2 multi-layer | Full-depth observed SBT classes, UNKNOWN gaps, sustained Ic>=2.60 and brief crossings, 1/3/10 rolling windows | Windows 3/10 smoothing order vs original formula not audited |
| WS3 candidate/reference audit | Existing physical file revisions, source audit and selection logic | CPT aliases/retests need engineer-approved pairing, cannot infer solely by filename |
| WS4 individual/full-project plots | Existing CPT plots, all-layer interactive tab, batch PNG coordinate maps | Existing PDF visual output is reference-like, not proven pixel-identical |
| WS5 maps | Measured Easting/Northing, point click-to-profile, Site Limit boundary import, project metric maps | CRS unspecified; no inferred contour surfaces |
| WS6 foundation | External Raft/Isolated summary imported, mapped, labeled REFERENCE ONLY | Settlement, liquefaction FOS and footing formulas have **not** been independently re-implemented/verified |
| WS7 Pre/Post | Import generated/legacy summaries, guarded matching, delta/percent, unmatched QA, charts/coordinate delta, comparison XLSX | No depth-by-depth comparison of full raw PRE/POST GEF curves yet |
| WS8 Excel | Original five-column and detailed sources, all observed layers, layer stats, methodology QA | Five-column legacy terminal silt result is provisional pending formula reconciliation |
| WS9 PDF fidelity | Existing PDF input/append/report paths + conservative thin-layer REVIEW | XLSB/Excel exact printing and comprehensive visual regression outstanding |
| WS10 desktop | Soil Layers, Site Map, Foundations, Pre/Post tabs; published one-file Windows EXE | Human GUI click-through/400+ file timed benchmark outstanding |

## Blocking external technical decisions
1. Reverse engineer/reference approved XLSB calculation workbook including VBA formulas and exact report print definition; compare with raw CPT and explicit groundwater/load parameters.
2. Engineering agreement on minimum qualifying silt persistence, exact thin-layer reporting and whether silty clay counts as silt-screening vs soil-lithology label.
3. Geotechnical sign-off on five manually annotated GEF fixtures and B292 legacy 6.20/0.20 vs foundation summary 6.20/0.10 discrepancy.
4. Confirm survey CRS, area polygons, settlement/FOS limits, footing stress/load assumptions, pre/post sampling and match tolerances.
5. Approve original Excel PDF side-by-side visual comparison, full Windows interactive smoke, end-to-end batch benchmark.

## Shipping rule
The current EXE is a **functional engineering-preview build**, not a certified design-analysis model. It should not be used as sole authority for ground improvement or footing compliance. The CI success proves package/test health, not technical model sign-off.
