<#
 Read-only, opt-in formula snapshot from original CPT XLSB through installed desktop Excel.
 WARNING: Executing unknown macros or external workbook links can be dangerous.
 This script forces VBA macros off, opens read-only, disables link updates, and does
 not save the workbook. Always run on a trusted isolated engineering workstation.

 Exports: worksheet names, selected formula expressions and cached read values
 in a JSON file for a qualified engineer's reconciliation with native equations.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Workbook,
    [string]$Output = "CPT_XLSB_Formula_Snapshot.json",
    [int]$MaxRows = 150,
    [int]$MaxColumns = 135
)
$ErrorActionPreference = "Stop"
if ($MaxRows -lt 1 -or $MaxRows -gt 5000) { throw "MaxRows must be between 1 and 5000." }
if ($MaxColumns -lt 1 -or $MaxColumns -gt 200) { throw "MaxColumns must be between 1 and 200." }
$path = (Resolve-Path -LiteralPath $Workbook).Path
$excel = $null
$book = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.EnableEvents = $false
    $excel.ScreenUpdating = $false
    $excel.AskToUpdateLinks = $false
    $excel.AutomationSecurity = 3 # msoAutomationSecurityForceDisable
    $excel.Calculation = -4135  # xlCalculationManual
    $book = $excel.Workbooks.Open($path,0,$true)
    $out = [ordered]@{
        SourceFile = [IO.Path]::GetFileName($path)
        Mode = "Read-only Excel formula snapshot; macros disabled; no linked-data updates."
        Limitation = "Sampled cells only; workbook may contain additional formulas and cached values. Numerical equivalence requires independent validation."
        Worksheets = @()
    }
    foreach ($sheet in $book.Worksheets) {
        $used = $sheet.UsedRange
        $rows = [Math]::Min($MaxRows,[Math]::Max(1,$used.Rows.Count))
        $cols = [Math]::Min($MaxColumns,[Math]::Max(1,$used.Columns.Count))
        $formulaCells = @()
        # Bulk COM read is orders of magnitude faster than per-cell COM calls.
        $formulas = $sheet.Range($sheet.Cells(1,1),$sheet.Cells($rows,$cols)).Formula2
        $values = $sheet.Range($sheet.Cells(1,1),$sheet.Cells($rows,$cols)).Value2
        for($row=1;$row -le $rows;$row++){
            for($col=1;$col -le $cols;$col++){
                $formula = if ($formulas -is [Array]) { $formulas.GetValue($row,$col) } else { $formulas }
                if (($formula -is [string]) -and ($formula.StartsWith("="))) {
                    $val=if ($values -is [Array]) { $values.GetValue($row,$col) } else { $values }
                    $formulaCells += [ordered]@{R=$row;C=$col;Formula=$formula;CachedValue=$val}
                }
            }
        }
        $out.Worksheets += [ordered]@{
            Name = $sheet.Name
            UsedRows = $used.Rows.Count
            UsedColumns = $used.Columns.Count
            SampleRows = $rows
            SampleColumns = $cols
            SampleFormulaCount = $formulaCells.Count
            FormulaCells = $formulaCells
        }
    }
    $out | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $Output -Encoding utf8
    Write-Host "Formula snapshot written to $Output"
} finally {
    if ($book -ne $null) { $book.Close($false) }
    if ($excel -ne $null) { $excel.Quit() }
    if ($book -ne $null) { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($book) }
    if ($excel -ne $null) { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel) }
    [GC]::Collect()
}
