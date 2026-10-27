CPT SILT ANALYZER — WINDOWS LONG PATH ERROR CORRECTION
October 27, 2026

ISSUE
Windows [WinError 206] The filename or extension is too long.
For projects under deeply nested OneDrive paths, the old application created
CPT_Output\\PDFs\\Run_<timestamp>\\<CPT report name>.pdf, which can exceed
the Win32 MAX_PATH limit.

WHAT HAS CHANGED
- Preflight every candidate output directory before analyzing CPT data,
  including reserved space for nested PDF, Excel temporary and HTML files.
- When the chosen path is too long, the application prompts to redirect
  OUTPUT ONLY to %USERPROFILE%\\CPT_Results.
- GEF, GFF and source PDFs remain at their original location and are not
  moved or changed.
- Individual PDF filenames are bounded/sanitized, and exceedingly long
  identifiers receive a deterministic hash suffix.
- Prevent bad output paths during direct/headless batch execution.
- If a processing failure cannot be logged to the selected long folder,
  the diagnostic log is written to the local short output folder instead.
- All independent same-point CPT files retain separate results and PDFs.
- Normal project geometry, Ic calculations, PRE/POST screening and
  engineering analysis numerical formulas are COMPLETELY UNCHANGED.

HOW TO USE
1. Extract ZIP to a local Windows folder.
2. Run CPT_Silt_Analyzer.exe.
3. Select your existing CPT source folder from OneDrive.
4. Click Analyze Project.
5. If Windows detects a too-long output path, choose YES when asked to use
   the recommended local folder.
6. Open output under C:\\Users\\<your Windows username>\\CPT_Results.
   You may later manually copy completed exports to your desired OneDrive
   location if Windows allows it.
7. Leave source files at their original locations.

ALTERNATIVE IMMEDIATE WORKAROUND FOR OLDER VERSIONS
Manually Browse and select a short writable output folder,
e.g. C:\\Users\\<your username>\\CPT_Results, BEFORE starting analysis.

ENGINEERING QUALIFICATION
Numerical CPT source processing, reviewer flags and layered-soil calculation
methods are identical to the previous corrected build. Engineering acceptance,
original XLSB/VBA formula parity and adjudication of repeated soundings
remain project review tasks independent of this Windows filesystem fix.
