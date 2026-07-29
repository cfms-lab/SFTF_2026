param(
    [Parameter(Mandatory = $true)]
    [string]$DocxPath,
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$word = $null
$document = $null
try {
    $resolvedDocx = (Resolve-Path -LiteralPath $DocxPath).Path
    $resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
    if (-not (Test-Path -LiteralPath $resolvedOutput)) {
        New-Item -ItemType Directory -Path $resolvedOutput | Out-Null
    }

    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($resolvedDocx, $false, $true)
    $document.Repaginate()
    $pageCount = $document.ComputeStatistics(2)

    for ($page = 1; $page -le $pageCount; $page++) {
        $pageStart = $document.GoTo(1, 1, $page).Start
        if ($page -lt $pageCount) {
            $pageEnd = $document.GoTo(1, 1, $page + 1).Start - 1
        }
        else {
            $pageEnd = $document.Content.End
        }
        $pageRange = $document.Range($pageStart, $pageEnd)
        $pageRange.Select()
        $word.Selection.CopyAsPicture()

        $image = $null
        for ($attempt = 0; $attempt -lt 20 -and $null -eq $image; $attempt++) {
            Start-Sleep -Milliseconds 100
            if ([System.Windows.Forms.Clipboard]::ContainsImage()) {
                $image = [System.Windows.Forms.Clipboard]::GetImage()
            }
        }
        if ($null -eq $image) {
            throw "Word did not place page $page on the clipboard as an image."
        }
        try {
            $outputPath = Join-Path $resolvedOutput ("page-{0:D3}.png" -f $page)
            $image.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
            Write-Output "Rendered page $page -> $outputPath"
        }
        finally {
            $image.Dispose()
        }
    }
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
    [System.Windows.Forms.Clipboard]::Clear()
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
