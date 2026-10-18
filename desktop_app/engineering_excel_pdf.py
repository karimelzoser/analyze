"""Use installed Microsoft Excel itself to export its saved original chart layout.

Excel is a separate optional Windows dependency. This renders original XLSB
report pages without claiming the native Python renderer is pixel-identical.
The workbook is opened read-only with all macros disabled and no link updates.
It does NOT change CPT source input or execute VBA/ground engineering formulas.
"""
from pathlib import Path
import base64
import json
import subprocess
import sys


SHEETS={
    "CPT-Graphs":"Original CPT curves and SBT graphics",
    "Analysis-Graph":"Original analysis results and settlement charts",
    "Analysis-Graph Aramco":"Original Aramco alternate format",
    "Liq-Graphs":"Original liquefaction plots",
}


def export_original_excel_pdf(workbook_path,output_pdf,*,sheet_name="CPT-Graphs",
                              expected_cpt=None,timeout_s=100):
    if sys.platform!="win32":
        raise RuntimeError("Original XLSB PDF printing requires Microsoft Excel on Windows")
    if sheet_name not in SHEETS:
        raise ValueError("Unsupported reference print worksheet")
    wb=Path(workbook_path).resolve()
    out=Path(output_pdf).resolve()
    if not wb.is_file() or wb.suffix.lower()!=".xlsb":
        raise ValueError("Select original .xlsb file")
    from engineering_xlsb_reference import ReferenceWorkbookCache
    with ReferenceWorkbookCache(wb) as ref:
        source=ref.summary()
        selected=source["cached_selected_cpt"]
        if expected_cpt and str(expected_cpt).strip().upper()!=str(selected).strip().upper():
            raise ValueError("Workbook currently caches CPT %r, not requested %r. Do not export a mismatched original report."%
                             (selected,expected_cpt))
        if sheet_name not in ref.sheetfiles:
            raise ValueError("The XLSB file does not contain "+sheet_name)
    out.parent.mkdir(parents=True,exist_ok=True)
    # PowerShell script is independent of shell argument quoting; variables
    # passed as Base64-encoded JSON to avoid command injection.
    payload=base64.b64encode(json.dumps({
        "workbook":str(wb),"output":str(out),"sheet":sheet_name
    }).encode("utf-8")).decode()
    script=r"""
$ErrorActionPreference='Stop'
$p=[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__PAYLOAD__')) | ConvertFrom-Json
$xl=$null;$book=$null
try {
 $xl=New-Object -ComObject Excel.Application
 $xl.Visible=$false
 $xl.DisplayAlerts=$false
 $xl.EnableEvents=$false
 $xl.AskToUpdateLinks=$false
 $xl.AutomationSecurity=3
 $xl.ScreenUpdating=$false
 $xl.Calculation=-4135
 $book=$xl.Workbooks.Open($p.workbook,0,$true)
 $sheet=$book.Worksheets.Item($p.sheet)
 $sheet.ExportAsFixedFormat(0,$p.output,0,$true,$false)
 if(-not [IO.File]::Exists($p.output)){throw 'Excel did not create the PDF'}
} finally {
 if($book -ne $null){$book.Close($false)}
 if($xl -ne $null){$xl.Quit()}
 if($book -ne $null){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book)}
 if($xl -ne $null){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($xl)}
 [GC]::Collect()
}
""".replace("__PAYLOAD__",payload)
    encoded=base64.b64encode(script.encode("utf-16le")).decode("ascii")
    run=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                        "-EncodedCommand",encoded],capture_output=True,text=True,
                       timeout=timeout_s)
    if run.returncode!=0:
        raise RuntimeError("Microsoft Excel original PDF export failed: "+
                           (run.stderr or run.stdout).strip()[-1200:])
    if not out.exists() or out.stat().st_size<1000:
        raise RuntimeError("Excel returned success but no valid PDF was generated")
    return out,selected
