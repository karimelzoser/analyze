# CPT Silt Analyzer - Professional Desktop

Local Windows desktop application for CPT `.GEF`, `.GFF` and project CPT `.PDF` reports.

## Professional workflow

The desktop build uses a modern three-tab workflow:

1. **Setup** - choose individual files or a folder, engineering settings, output folder and report options.
2. **Results** - searchable/filterable engineering results with direct PDF/Excel/output controls.
3. **Charts** - interactive project-level plots with sorting, filtering, show/hide controls, zoom/pan and PNG export.

The application is fully local; project files are not uploaded to a cloud service.

## Supported inputs and source priority

- `.GEF` / `.GFF`: preferred source. The raw corrected depth, qc, fs and u2 values are used directly.
- Native-vector CPT `.PDF`: supported when the report contains the project Soil Behaviour Type Index (Ic) vector chart and readable native text.
- Scanned/image-only or unsupported PDF templates: retained as `REVIEW`; the program does not guess a silt interval.

When a selected folder contains both a raw GEF/GFF and a PDF for the same CPT reference, the application automatically prefers the raw numerical file and skips the duplicate PDF so the CPT is not double-counted.

## PDF analysis method

For the supplied Terra Firma project-report format, PDF analysis is performed locally without OCR or cloud services:

1. Read project metadata and ground elevation from native PDF text.
2. Identify the vector `Soil Behaviour Type Index, Ic` panel.
3. Extract the native vector Ic trace from the PDF drawing geometry.
4. Map panel coordinates to level/depth using the report level axis and ground elevation.
5. Detect sustained `Ic >= 2.60` intervals and select the deepest project-relevant interval.
6. Extend a short terminal chart-return tail to the plotted sounding end when it falls within the validated terminal tolerance.
7. Run two independent passes; disagreements receive eight sensitivity rechecks.
8. Apply the project 0.10 m reporting convention to start/end, then calculate reported thickness as `reported end - reported start`.

PDF-derived interpretation is intentionally labelled lower-confidence than raw GEF/GFF numerical analysis. If the vector chart cannot be verified, the result is `REVIEW` rather than an estimate.

Validated PDF regression anchors:

- `CPT-A1-B342-100` -> 6.20 m start / 0.40 m silt thickness
- `CPT-A1-B343-100` -> 6.20 m / 0.30 m
- `CPT-A1-B355-100` -> 6.30 m / 0.30 m
- `CPT-A1-B356-100` -> 6.40 m / 0.20 m

These anchors are executed automatically in the Windows CI test suite before a release is published.

## Performance

- Independent raw GEF/GFF numerical analyses run concurrently with up to 8 local worker threads.
- PDF analysis is intentionally serialized because PyMuPDF does not guarantee thread safety.
- PDF/report generation is serialized for deterministic Matplotlib/PyMuPDF output.
- Users can disable **Generate individual CPT PDFs** when they only need the Excel workbook and project charts.
- Progress is stage-aware: analysis, PDF generation and workbook completion are shown separately.

## Raw GEF/GFF accuracy / QA rules

- Uses raw corrected depth, qc, fs and u2.
- Calculates qt, Fr, Qtn and Robertson-style Ic.
- Detects terminal exact-zero sleeve-friction dropout so it cannot create a false high-Ic tail.
- Interpolates the Ic=2.60 threshold crossing between measurements.
- Performs two interval-analysis passes; disagreements go through eight sensitivity rechecks.
- Never guesses unresolved cases: they remain `REVIEW`.
- Writes `NO SILT` only when the analysis verifies no qualifying sustained terminal silt interval.
- Reported start and end are rounded to 0.10 m, then reported silt thickness is calculated as `reported end - reported start`.

For the supplied regression GEF `CPT-A1-292-100`, the production result is 6.20 m silt start and 0.20 m reported silt thickness.

## Sand thickness

`Sand layer thickness before silt` is the project layer thickness from ground level to the selected terminal silt start. For a verified `NO SILT` sounding it is the analyzed sounding depth. `REVIEW` cases remain blank rather than being guessed.

## Excel workbook

The primary `CPT Analysis` sheet contains five columns:

1. `SI.No`
2. `CPT REFERENCE`
3. `Silt start depth after (m)`
4. `silt depth (m)`
5. `Sand layer thickness before silt (m)`

Additional sheets preserve engineering traceability:

- `Full Analysis` - metadata, coordinates, test depth, raw/reported silt boundaries, sand thickness, Ic/Qtn/Fr and qc/fs/u2 when available, plus verification details.
- `Detected Intervals` - qualifying intervals considered by the algorithm.
- `Summary` - total/verified/no-silt/review counts, maximum silt thickness and CPT reference(s), averages and ranking.
- `Charts` - printable project charts for thickness, layer profile, silt start/end/test depth, highest-silt ranking and coordinates.
- `Processing Errors` - input/report-generation issues kept separate from engineering results.

PDF-derived rows naturally leave raw-only qc/fs/u2/Qtn/Fr fields blank because those values are not reconstructed from the report graphic.

## PDF output

For raw GEF/GFF input, the application creates the standard reference-style CPT page and appends the analysis page.

For PDF input, every original source PDF page is copied unchanged and one `CPT PDF ANALYSIS SUMMARY` page is appended. The source report is not redrawn or annotated.

## Interactive charts

Available desktop views:

- Line overview
- Grouped bars
- Layer profile
- Highest silt ranking
- Silt-thickness histogram
- Silt start vs thickness
- Coordinate map

Controls allow sorting, status filtering, show/hide of silt thickness, sand-before-silt thickness, silt start and test depth, maximum-thickness highlighting, zoom/pan/reset and PNG export.

## Run from source

```bash
cd desktop_app
python -m pip install -r requirements.txt
python app_modern_final.py
```

## Windows build

GitHub Actions runs the automated regression suite and Python smoke tests before building `CPT_Silt_Analyzer.exe` with PyInstaller. The tested executable is zipped and published to:

`release/CPT_Silt_Analyzer_Latest.zip`

A failed test prevents the release ZIP from being replaced.
