# CPT Silt Analyzer - Desktop

Local Windows desktop application for CPT `.GEF` / `.GFF` files.

## Workflow

Select individual files **or** a folder, confirm the output location, then press **START ANALYSIS**. The app generates:

- `PDFs/<CPT reference>.pdf` for every successfully analyzed CPT.
- `CPT_Silt_Analysis.xlsx`.

The UI includes **Open PDFs**, **Open Excel Sheet**, and **Open Output Folder** buttons. Double-clicking a result row opens that CPT PDF.

## Accuracy rules

- Uses raw corrected depth, qc, fs and u2.
- Calculates qt, Fr, Qtn and Robertson-style Ic.
- Detects a terminal exact-zero sleeve-friction dropout so it cannot create a false high-Ic tail.
- Interpolates the Ic=2.60 threshold crossing between measurements.
- Performs two independent interval analyses; disagreements go through eight detailed rechecks.
- Never guesses unresolved cases: they remain `REVIEW`.
- Writes `NO SILT` only when the independent analysis verifies no qualifying sustained terminal silt interval.
- Reported start and end are rounded to 0.10 m, then reported silt thickness is calculated as `reported end - reported start`.

For the supplied regression GEF `CPT-A1-292-100`, the production result is 6.20 m silt start and 0.20 m reported silt thickness.

## Sand thickness

`Sand layer thickness` is the project layer thickness from ground level to the selected terminal silt start. For a verified `NO SILT` sounding it is the analyzed sounding depth. `REVIEW` cases remain blank rather than being guessed.

## Excel

The first sheet, `CPT Analysis`, remains exactly four columns:

1. `SI.No`
2. `CPT REFERENCE`
3. `Silt start depth after (m)`
4. `silt depth (m)`

Additional sheets:

- `Full Analysis`: sand thickness, reported and raw silt boundaries/thickness, corrected test depth and status.
- `Summary`: total/verified/no-silt/review counts, the **maximum silt thickness and the CPT reference(s) where it occurs**, average silt thickness, and a full-project layer-thickness chart.

## PDF

Page 1 follows the supplied project-report structure: source metadata, qc, fs/u2, Ic zones, normalized behavior plot and the metadata table. No silt-analysis annotation is added to the standard data page.

Page 2 is added **after** the standard CPT data and contains the analysis table with reported values, raw interpolated values, sand thickness, sounding depth, terminal sensor-dropout information and verification status.

## Interactive chart

The desktop `Full Analysis Chart` tab has independent show/hide checkboxes for:

- Silt thickness
- Sand thickness
- Silt start

The Matplotlib toolbar supports zoom and pan for large batches.

## Run from source

```bash
cd desktop_app
python -m pip install -r requirements.txt
python app.py
```

CLI:

```bash
python cli.py "C:\path\to\folder" --output "C:\path\to\CPT_Output"
```

## Windows build

GitHub Actions runs the automated tests before building `CPT_Silt_Analyzer.exe` with PyInstaller. A failed test prevents delivery of the executable.
