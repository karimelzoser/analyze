"""Recalculate one GEF with *original* XLSB formulas using locally installed Excel.

This is an OPTIONAL high-fidelity Windows engine, not standalone fallback.
All VBA is disabled; source workbook opened read-only; no links updated.
The GEF header layout must align with the source workbook Input Data template.
"""
from __future__ import annotations
import csv,json,os,re,subprocess,sys,tempfile
from pathlib import Path


def input_matrix_from_gef(path,*,expected_header_lines=61,max_columns=12,max_rows=2000):
    f=Path(path)
    if f.suffix.lower() not in (".gef",".gff"):
        raise ValueError("Source must be .GEF or .GFF")
    lines=[line.strip() for line in f.read_text(encoding="utf-8-sig",errors="replace").splitlines()
           if line.strip()]
    end_headers=next((i for i,s in enumerate(lines) if s.upper().startswith("#EOH")),None)
    if end_headers is None:raise ValueError("GEF missing #EOH header terminator")
    if end_headers+1!=expected_header_lines:
        raise ValueError("Original XLSB uses a %d-line GEF header, but source contains %d. Field-by-field alignment is required before using original formula cells." %
                         (expected_header_lines,end_headers+1))
    if len(lines)-end_headers-1<10:raise ValueError("Insufficient CPT records")
    if len(lines)-end_headers-1>max_rows:
        raise ValueError("Source sounding exceeds original XLSB input capacity")
    result=[]
    for i,line in enumerate(lines):
        if line.startswith("#"):
            # Source XLSB Input Data uses whitespace-split header records.
            # Commas and semicolons serve as separators in these GEF exports.
            fields=re.split(r"[,;\s]+",line)
        else:
            fields=re.split(r"[;\s]+",line)
        fields=[x for x in fields if x]
        converted=[]
        for x in fields[:max_columns]:
            try:
                num=float(x)
                converted.append(num if abs(num)<1e12 else x)
            except ValueError:
                converted.append(x)
        result.append(converted)
    refline=next((x for x in lines if x.upper().startswith("#TESTID")),None)
    if refline is None:raise ValueError("Missing #TESTID")
    expected_ref=refline.split("=",1)[1].strip().split(",")[0].strip()
    if not expected_ref.upper().startswith("CPT-"):
        raise ValueError("Missing valid CPT source reference")
    return result,expected_ref


_EXCEL_WORKER = r'''
param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$Matrix,
      [Parameter(Mandatory=$true)][string]$Output,[Parameter(Mandatory=$true)][string]$Reference)
$ErrorActionPreference='Stop'
$xl=$null;$book=$null
try {
  $xl=New-Object -ComObject Excel.Application
  $xl.Visible=$false;$xl.DisplayAlerts=$false;$xl.EnableEvents=$false
  $xl.AskToUpdateLinks=$false;$xl.AutomationSecurity=3;$xl.ScreenUpdating=$false
  $book=$xl.Workbooks.Open($Source,0,$true)
  $input=$book.Worksheets.Item('Input Data')
  $input.Range('A2:L2300').ClearContents()
  $lines=Get-Content -LiteralPath $Matrix -Raw -Encoding utf8 | ConvertFrom-Json
  $total=$lines.Count
  $cols=12
  $cells=New-Object 'object[,]' $total,$cols
  for($i=0;$i -lt $total;$i++){
    for($j=0;$j -lt [Math]::Min($cols,$lines[$i].Count);$j++){
      $cells[$i,$j]=$lines[$i][$j]
    }
  }
  $input.Range('A2').Resize($total,$cols).Value2=$cells
  $xl.Calculation=-4105
  $xl.CalculateFullRebuild()
  $reported=[string]$book.Worksheets.Item('Input').Range('B5').Value2
  if($reported.Trim().ToUpper() -ne $Reference.Trim().ToUpper()){
    throw "Original XLSB calculated CPT '$reported', expected '$Reference'; PDF export stopped."
  }
  $book.Worksheets.Item('CPT-Graphs').ExportAsFixedFormat(0,$Output,0,$true,$false)
  if(-not [IO.File]::Exists($Output)){throw 'Microsoft Excel returned without a PDF'}
} finally {
  if($book -ne $null){$book.Close($false)}
  if($xl -ne $null){$xl.Quit()}
  if($book -ne $null){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book)}
  if($xl -ne $null){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($xl)}
  [GC]::Collect()
}
'''


def run_original_excel_gef(gef_path,xlsb_path,pdf_path,*,timeout_s=420):
    if sys.platform!="win32":
        raise RuntimeError("Requires Microsoft Excel locally installed on Windows")
    source=Path(xlsb_path).resolve()
    if source.suffix.lower()!=".xlsb" or not source.is_file():
        raise ValueError("Choose original XLSB source workbook")
    from engineering_xlsb_reference import ReferenceWorkbookCache
    with ReferenceWorkbookCache(source) as original:
        if not {"Input Data","Input","CPT-Graphs"}.issubset(original.sheetfiles):
            raise ValueError("Original XLSB required sheets absent")
        # Ensure workbook actually uses known GEF layout prior to writing.
        position=next((i for i,row in original.rows("Input Data",cols=[0],stop=150)
                       if str(row.get(0,"")).startswith("#EOH")),None)
        if position is None or position<10:
            raise ValueError("Source XLSB has no recognizable Input Data header")
    matrix,ref=input_matrix_from_gef(gef_path,expected_header_lines=position-1)
    output=Path(pdf_path).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cpt_orig_xlsb_") as temp:
        folder=Path(temp)
        jsonfile=folder/"source.json"
        jsonfile.write_text(json.dumps(matrix,ensure_ascii=False),encoding="utf-8")
        script=folder/"original_excel_engine.ps1"
        script.write_text(_EXCEL_WORKER,encoding="utf-8-sig")
        run=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                            "-ExecutionPolicy","Bypass","-File",str(script),
                            "-Source",str(source),"-Matrix",str(jsonfile),
                            "-Output",str(output),"-Reference",ref],
                           capture_output=True,text=True,timeout=timeout_s)
        if run.returncode!=0:
            raise RuntimeError("Original Excel recalculation failed: "+
                       (run.stderr or run.stdout).strip()[-1800:])
    if not output.exists() or output.stat().st_size<2000:
        raise RuntimeError("Original Excel recalculation created no valid PDF")
    import pymupdf
    with pymupdf.open(str(output)) as doc:
        txt="\n".join(page.get_text() for page in doc)
        # Worksheet must contain the actual current sounding ID, otherwise
        # Excel may have rendered stale, incorrectly linked chart caches.
        if ref.upper() not in txt.upper():
            output.unlink(missing_ok=True)
            raise RuntimeError("Original Excel output could not confirm CPT reference; report suppressed.")
    return output,ref
