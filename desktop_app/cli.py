from __future__ import annotations

import argparse
from pathlib import Path

from cpt_core import analyze_gef
from reporting import export_excel, generate_pdf


def collect_files(inputs):
    files = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.GEF")))
            files.extend(sorted(p.rglob("*.gef")))
            files.extend(sorted(p.rglob("*.GFF")))
            files.extend(sorted(p.rglob("*.gff")))
        elif p.is_file():
            files.append(p)
    return sorted(set(files), key=lambda p: p.name.lower())


def main():
    ap = argparse.ArgumentParser(description="Batch CPT GEF/GFF analyzer")
    ap.add_argument("inputs", nargs="+", help="GEF/GFF files or folders")
    ap.add_argument("--output", default="CPT_Output", help="Output directory")
    ap.add_argument("--gamma", type=float, default=18.0, help="Total unit weight kN/m3")
    ap.add_argument("--water-table", type=float, default=0.0, help="Groundwater depth below ground (m)")
    args = ap.parse_args()

    files = collect_files(args.inputs)
    if not files:
        raise SystemExit("No .GEF/.GFF files found")

    out = Path(args.output)
    pdf_dir = out / "PDFs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    analyses = []
    for i, p in enumerate(files, 1):
        a = analyze_gef(p, gamma_soil=args.gamma, water_table_depth=args.water_table)
        analyses.append(a)
        generate_pdf(a, pdf_dir / f"{a.reference}.pdf")
        print(f"[{i}/{len(files)}] {a.reference}: {a.silt_start_display} / {a.silt_depth_display} ({a.status})")
    export_excel(analyses, out / "CPT_Silt_Analysis.xlsx")
    print(f"Finished. Output: {out.resolve()}")


if __name__ == "__main__":
    main()
