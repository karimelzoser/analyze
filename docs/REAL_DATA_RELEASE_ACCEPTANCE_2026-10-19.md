# CPT Engineering Studio — Real Data and Windows Release Acceptance (2026-10-19)

**Release:** `release/CPT_Silt_Analyzer_Latest.zip`, ZIP size 84,976,171 bytes; Windows GUI and executable tests passed in GitHub Actions [run 39215079461](https://github.com/karimelzoser/analyze/actions/runs/39215079461).

## Independent automated checks

- **125 regression tests passed.**
- All **8 UI workspaces** opened from source and frozen EXE; the real normal startup and cancellation paths were tested.
- Synthetic end-to-end integration generated **one PDF, one consolidated Excel workbook containing embedded 2D/3D maps**, and the expected engineering sheets.
- Synthetic 400-CPT numerical+spreadsheet+4-map benchmark: **20.05 seconds** on GitHub Windows runner (3.64 s numerical, 13.33 s workbook, 3.09 s four charts). NOT a performance promise for 400 real PDFs; the PDF-heavy run is separate.
- Local inspection verified a **single 16-worksheet workbook** can retain six measured GEF/GFF analyses + 448 original XLSB cached raft rows + the separate pre-CPT raft/isolated cases, 8 native editable Excel charts and two embedded site maps in one file.
- In the original-visual PDF flow, the original user-supplied B355 report page was pixel-identical before and after the analysis appendix was appended.

## Real raw CPT acceptance set (private source files were NOT uploaded to GitHub)

| CPT | Reference expectation | Native observed result | Status |
|---|---|---|---|
| CPT-A1-B18-100 | 4.30 / 0.20m | 4.30 / 0.20m | Match |
| CPT-A1-B19-100 | 4.30 / 0.30m | 4.30 / 0.30m | Match |
| CPT-A1-B04-100 | approx. 4.20 / 0.20m | 4.20 / 0.20m | Match |
| CPT-A1-B05-100 | no qualifying persistent silt | NO SILT | Match |
| CPT-A1-B07-100 | no qualifying persistent silt | NO SILT | Match |
| CPT-A1-292-100 | original XLSB summary 6.20 / 0.10m | 6.20 / 0.10m | Match |

The model uses current source-data assumptions (water level 2m default, original numerical cone area ratio from each raw header), observes terminal sensor invalid data as UNKNOWN, and retains unrounded thickness and metadata in reports. **These matches are not independent validation of USCS soil laboratory classification.**

## Actual project 448-PDF acceptance (completed repository workflow)

[Run 39211419932](https://github.com/karimelzoser/analyze/actions/runs/39211419932) audited **448 physical PDFs** in 131.89 seconds with **0 file parse failures**.

- **418 unique CPT locations** (30 duplicate/revision files).
- **301 VERIFIED**, **100 NO SILT**, **17 REVIEW** at the unique project-result level.
- Of 17 REVIEW: **12 observed positive but thin source-PDF intervals** requiring a stated 0.10m reporting rule, and **5 revision/physical-source conflicts** requiring reconciliation. These are surfaced in **Review Evidence**, **Review Resolution** and **Source Audit**; they are not discarded or silently relabeled.
- 448-PDF acceptance workbook contains raw/derived information available from PDF, coordinate QA, embedded 2D/3D maps and 8 editable chart objects. A parsed PDF vector trace is not as authoritative as its numerical GEF/GFF source.

## Original source workbook parity

The supplied original XLSB includes **17 worksheets**, **448 saved raft rows**, **447 distinct saved profile series** and cached source assumptions:
- groundwater BGL 2.00m;
- cone area ratio 0.80 in workbook input (native raw source may specify a different ratio);
- smoothing values Above=3 and Below=3 in workbook configuration.
- `Combined CPTs` 'Ic' display in saved source is integer SBT zone codes, not a continuous calculated Ic field.
- A1-292 original zone 4 occurs near 6.20–6.29m, supporting 6.20/0.10m reporting; a previous app report 6.20/0.20m was incorrect.

## Remaining release gate — cannot be called independently design-certified yet

The supplied XLSB contains compiled formula/VBA dependencies not independently reconstructed and approved for arbitrary new sounding inputs. A separate Windows Excel-based original-model export route exists, but **it cannot be exercised or certified by GitHub-hosted runners without the licensed Excel runtime and approved source calculation execution**. Raft/isolated-footing design PASS/FAIL statements require engineer-approved geotechnical loads, input parameters, soil correlations and design criteria. No sample binary/UI smoke result can substitute for this sign-off.

**Release classification:** Tested engineering desktop application and audited real-project screening; **NOT independently certified geotechnical design software**. Do not force unresolved thin intervals, contradictory physical test revisions, or source date/CRS conflicts to VERIFIED automatically.

The full implementation master plan, validation matrix, forensic XLSB findings and open engineering issues remain in `docs/` and GitHub Issues.
