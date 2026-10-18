# Forensic findings from supplied original CPT XLSB — 2026-10-18

The private 40 MB input workbook `CPT analysis v2.5.7 - pore pressure 1.xlsb` was inspected **locally**, not uploaded to GitHub. New software `engineering_xlsb_reference.py` implements read-only standard-library BIFF12 parsing, preserving original source values without executing formulas or VBA.

## Confirmed reference model facts

- 17 binary worksheets, including Input, Input Data, CPT-Graphs, Analysis-Case 1/2/3, Analysis-Graph, Liquefaction, Combined CPTs, Summary and DataSBT.
- Original `Summary` contains 448 saved foundation rows / 447 distinct CPT references, all of type **Raft**.
- `Combined CPTs` contains 447 saved CPT sequences at nominal 0.01m depth sampling. Its column titled **Ic** is actually a **categorical SBT zone integer (1-9)**; it is **not** numeric Robertson Ic.
- Original `Input` cached model parameters: net cone area ratio = **0.80**; groundwater depth **2.00 m BGL**; saved smoothing inputs **Above=3, Below=3** with distance units indicated as **cm**. These are not equivalent to assuming a 3-sample rolling mean. The source also contains selected case input parameters:
  - Raft 50 × 60m, bearing pressure 100 kPa, allowable settlement 60mm, foundation depth 1m.
  - Isolated 3 × 3m, bearing pressure 150 kPa, allowable settlement 40mm, foundation depth 1m.
  - Liquefaction PGA .078g, magnitude 6.0, required FOS 1.25.
- The source `Input Data` embeds one specific CPT at a time. The source file in the supplied XLSB was `CPT-A2-B98-100`; it is not a generic recalculated report for arbitrary raw files.

## A1-292 numerical reconciliation

- Original XLSB `Summary` coordinate Easting 421092.37 / Northing 2928336.25; ground elevation 3.46.
- Saved raft settlement **71.544074 mm** with 60mm allowable → original `Settlement Check: Failed`.
- Saved minimum liquefaction FOS **2.43058466**; recorded check `Pass`.
- Original XLSB `Combined CPTs` zone sequence:
  - depth 6.15–6.19m: SBT **Zone 5**
  - depth **6.20–6.28m: Zone 4**
  - depth 6.29–6.31m: **Zone 5**
  - depth 6.32m: **Zone 6**, followed by 7.
- Thus original saved SBT Zone 4 screening yields approx **6.20m start / 0.09m observed interval / 0.10m reported**, supporting the engineer's original source summary `6.20 / 0.10`, not the earlier app's `6.20 / 0.20`.
- **Important:** Zone 4 fine-grained-like SBT does not alone constitute laboratory USCS silt. The zone sequence is saved source output, not independent equation recomputation.

## Remaining discrepancies from the same source

Approved historical graphical interpretations and SBT-zone boundaries are not identical in every CPT (B342/B343/B355/B356). Examples of cached terminal zone 4 runs:
- B342: approx 6.13–6.55m;
- B343: approx 6.17–6.36m;
- B355: approx 6.30–6.53m;
- B356: approx 6.37–6.54m.

The differences should be reconciled to the 0.1m reporting convention and the reference plot rule; **do not force the source cache to fit historic example results by modifying the threshold**.

## Software implementation added

- XLSB cached reference import and a project workbook plus four point maps from source data.
- Coordinate-verified native-vs-original numerical QA comparisons, preserving source settings and showing mismatches.
- Optional Microsoft Excel COM print of the original saved `CPT-Graphs` page, with macros/external links disabled, without altering original XLSB.
- Source reference results and custom footing pass criteria are distinct from native Python calculations and do not represent independent engineer certification.

## What remains an engineering acceptance gate

- Decoding/executing all XLSB formula tokens and validating VBA logic is **not complete**. Saved cache values are original Excel outputs, but do not replace formula parity for changed inputs.
- Full independent raft and isolated-footing formulas must be proved against the source workbook with approved loads/stress/soil parameters. The original XLSB Summary stores only raft outcomes across the full project; isolated results are available in the separately supplied `Pre CPT Summary.xlsx`.
- If Microsoft Excel is not installed, exact *newly calculated* XLSB report print is unavailable; original saved PDFs can instead be preserved verbatim. Native generated PDFs remain reference-style, not pixel-identical.

**Never assert the entire production engineering model is validated merely because the synthetic and Windows CI tests pass.**
