# CPT Silt Analyzer - Professional Desktop

Local Windows desktop application for CPT `.GEF` / `.GFF` files.

## Professional workflow

The current desktop build uses a modern three-tab workflow:

1. **Setup** - choose files/folder, engineering settings, output folder and report options.
2. **Results** - searchable/filterable engineering results with direct PDF/Excel/output controls.
3. **Charts** - interactive project-level plots with sorting, filtering, show/hide controls, zoom/pan and PNG export.

The application is fully local; raw CPT files are not uploaded to a cloud service.

## Performance

- Independent CPT numerical analyses run concurrently with up to 8 local worker threads.
- PDF rendering remains serialized because Matplotlib PDF generation is intentionally kept single-threaded for reliability.
- Users can disable **Generate individual CPT PDFs** when they only need the Excel workbook and project charts; this removes the main batch-processing bottleneck.
- Progress is stage-aware: numerical analysis, PDF generation and workbook completion are displayed separately.

## Accuracy / QA rules

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

The primary `CPT Analysis` sheet now contains five columns:

1. `SI.No`
2. `CPT REFERENCE`
3. `Silt start depth after (m)`
4. `silt depth (m)`
5. `Sand layer thickness before silt (m)`

Additional sheets preserve engineering traceability:

- `Full Analysis` - metadata, coordinates, test depth, raw/reported silt boundaries, sand thickness, Ic/Qtn/Fr and qc/fs/u2 at the selected transition, sensor-dropout information and verification details.
- `Detected Intervals` - all qualifying intervals considered by the algorithm.
- `Summary` - total/verified/no-silt/review counts, maximum silt thickness and CPT reference(s), averages and ranking.
- `Charts` - printable project charts for thickness, layer profile, silt start/end/test depth, highest-silt ranking and coordinates.
- `Processing Errors` - input/report-generation issues kept separate from engineering results.

## PDF output

Page 1 follows the supplied project-report structure: source metadata, qc, fs/u2, Ic zones, normalized Qtn-Fr soil-behaviour chart and the metadata table. No silt-analysis annotation is added to the standard data page.

Page 2 is appended after the standard CPT page and contains the analysis table with reported values, raw interpolated values, sand thickness, sounding depth, sensor-dropout information and verification status.

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
