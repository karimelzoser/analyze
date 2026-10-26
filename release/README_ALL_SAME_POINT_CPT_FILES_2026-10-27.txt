CPT SILT ANALYZER — PRESERVE ALL PHYSICAL CPT SOURCE FILES
Engineering preview / Oct 27, 2026

COMPATIBILITY
This build does NOT alter CPT numerical equations, Robertson Ic calculations,
groundwater assumptions, 0.10m rounding, PRE/POST smoothing, minimum observed
layer, sensor-dropout detection, or 3-of-4 agreement rules. Only source
selection, reporting labels, duplicate visibility, QA and output directories
have changed.

HOW TO USE
1. Extract this ZIP. Double click CPT_Silt_Analyzer.exe on Windows.
2. Select the GEF/GFF files or the folder containing them.
3. Run Full Analysis.
4. Open the single consolidated Excel workbook. CPT Analysis contains one row
   per physical RAW GEF/GFF sounding — including multiple files for the SAME
   point. Duplicates are visibly marked "(FILE 1 OF 2)" / "(FILE 2 OF 2)".
5. Open "Repeated CPT Files" to see exact original source filenames, per-file
   status, field test date, sounding depth, measured candidate silt results
   and duplicate/retest engineering caveats.
6. Generated PDFs are in CPT_Output/PDFs/Run_<timestamp>/, one for each
   independently analyzed sounding, with the same unique FILE X OF Y label.
   Old PDFs from previous batches are never mixed with new per-run PDFs.
7. Full Analysis, Source Audit, Original GEF Headers, raw CPT Measurements,
   map/atlas and QA remain available.

IMPORTANT INTERPRETATION
- A nominal CPT point may have MORE THAN ONE REAL physical sounding.
  Distinct files are not silently merged, discarded or superseded.
- Short/aborted tests remain present with measured raw data but are clearly
  marked INCOMPLETE; absence of observed qualifying silt in a very short
  sounding does NOT prove full-depth NO SILT.
- The quick Excel column previously called "Sand layer thickness before silt"
  is now correctly "Depth to selected silt — NOT continuous sand".
  Its values are preserved for qualifying VERIFIED soundings; blank for
  NO SILT/REVIEW/short aborted tests when continuous sand is not measured.
- Two profiles from one XY remain independently inspectable in the atlas;
  they are not automatically treated as independent spatial points for an
  interpolated soil model or a geotechnical design decision.
- An official PDF page is not paired to both competing raw retests without
  evidence uniquely identifying the correct physical test.

SOURCE DATA VERIFICATION
The operator-supplied private A2 archive includes 71 physical GEF files
representing 68 canonical CPT point references. Three point references have
two source soundings (B253, B254, B256). These data were audited independently
for the previously reported baseline (not uploaded to GitHub). This build's
Windows CI includes a source-specific two-file end-to-end regression and
checks that calculations do not change when a point is repeated.

LIMITATION
This is an ENGINEERING PREVIEW, not a certified soil/foundation design tool.
Ic soil-behavior screening is NOT laboratory USCS silt identification.
An engineering reviewer must adjudicate retests/short aborted soundings and
the original XLSB/VBA design parity before using outputs for engineering
acceptance.
