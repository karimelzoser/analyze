# CPT Silt Analyzer - Desktop

Local Windows desktop tool for CPT GEF/GFF files.

## Why desktop

This workflow does not require the internet. A desktop application keeps project data on the workstation, handles large batches efficiently, and can generate PDFs and Excel locally.

## Inputs

- `.GEF` or `.GFF` ASCII CPT files using the GEF header/data convention.
- The parser reads the raw channels from `#COLUMNINFO`, including corrected depth/penetration length, cone resistance `qc`, sleeve friction `fs`, and pore pressure `u2` when available.

## Outputs

For every input file:

- One professional CPT PDF under `PDFs/`.
- One batch Excel workbook: `CPT_Silt_Analysis.xlsx`.

The Excel has exactly four columns:

1. `SI.No`
2. `CPT REFERENCE`
3. `Silt start depth after (m)`
4. `silt depth (m)`

If no qualifying silt interval is found, the tool writes `NO SILT` and `0.00`.

## Silt analysis

The engine works directly from the raw GEF/GFF numerical data, not from PDF pixels:

1. Read corrected depth, qc, fs, u2 and cone area ratio.
2. Calculate corrected cone resistance `qt`.
3. Calculate stress-normalized `Fr`, `Qtn` and Robertson-style `Ic`.
4. Detect sustained `Ic >= 2.60` intervals.
5. Ignore shallow startup artefacts and very short/noisy crossings.
6. Select the deepest qualifying interval, matching the project convention established from the reference PDF set.
7. Perform two independent passes. If they disagree, run eight detailed rechecks before accepting a result.
8. Round reporting values to 0.10 m while displaying two decimals in Excel/PDF.

Defaults are soil unit weight `18 kN/m3` and groundwater at ground level. Both are editable in the desktop UI.

## Validation sample

The supplied sample `P261074_CPT-A1-292-100.GEF` contains 637 records, an end depth of approximately 6.36 m, and produces the project result:

- Silt start: `6.20 m`
- Silt depth: `0.10 m`

## Run from source

```bash
cd desktop_app
python -m pip install -r requirements.txt
python app.py
```

Batch/CLI:

```bash
python cli.py "C:\path\to\gef-folder" --output "C:\path\to\output"
```

## Windows EXE

The repository includes a GitHub Actions workflow that builds a single-file Windows executable with PyInstaller. Download the `CPT-Silt-Analyzer-Windows` artifact from the workflow run and extract `CPT_Silt_Analyzer.exe`.

## Engineering note

The PDF includes the raw CPT curves, calculated Ic, normalized CPT behaviour plot, test metadata, and the selected silt interval. The Excel deliberately remains limited to the requested four columns. Results that do not converge during independent verification are written as `REVIEW`, not guessed.
