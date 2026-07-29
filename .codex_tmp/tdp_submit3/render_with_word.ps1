param(
    [Parameter(Mandatory = $true)]
    [string]$DocxPath,
    [Parameter(Mandatory = $true)]
    [string]$PdfPath
)

$word = $null
$document = $null
try {
    $resolvedDocx = (Resolve-Path -LiteralPath $DocxPath).Path
    $resolvedPdf = [System.IO.Path]::GetFullPath($PdfPath)
    $pdfDirectory = [System.IO.Path]::GetDirectoryName($resolvedPdf)
    if (-not (Test-Path -LiteralPath $pdfDirectory)) {
        New-Item -ItemType Directory -Path $pdfDirectory | Out-Null
    }

    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($resolvedDocx, $false, $true)
    $document.Repaginate()
    $pageCount = $document.ComputeStatistics(2)
    $document.ExportAsFixedFormat($resolvedPdf, 17)
    Write-Output "Rendered $resolvedDocx"
    Write-Output "PDF: $resolvedPdf"
    Write-Output "Pages: $pageCount"
}
finally {
    if ($null -ne $document) {
        $document.Close($false)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($document)
    }
    if ($null -ne $word) {
        $word.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
