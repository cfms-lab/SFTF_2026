param(
    [Parameter(Mandatory = $true)]
    [string]$SectionName,

    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,

    [string]$SourceUrl = ""
)

$ErrorActionPreference = 'Stop'

function Convert-HtmlFragmentToMarkdown {
    param([AllowEmptyString()][string]$Html)

    if ([string]::IsNullOrWhiteSpace($Html)) {
        return ""
    }

    $value = $Html
    $value = [regex]::Replace(
        $value,
        '<a\s+[^>]*href=["'']([^"'']+)["''][^>]*>(.*?)</a>',
        {
            param($match)
            $label = [regex]::Replace($match.Groups[2].Value, '<[^>]+>', '')
            $label = [System.Net.WebUtility]::HtmlDecode($label).Trim()
            $href = [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value).Trim()
            if ([string]::IsNullOrWhiteSpace($label)) { $label = $href }
            return "[$label]($href)"
        },
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    $value = [regex]::Replace($value, '<br\s*/?>', "`n", 'IgnoreCase')
    $value = [regex]::Replace($value, '</(p|div|li|tr|h[1-6])>', "`n", 'IgnoreCase')
    $value = [regex]::Replace($value, '<[^>]+>', '')
    $value = [System.Net.WebUtility]::HtmlDecode($value)
    $value = $value -replace "\u00A0", ' '
    $value = $value -replace "[ \t]+", ' '
    $value = $value -replace "\r?\n[ \t]+", "`n"
    $value = $value -replace "\r?\n{3,}", "`n`n"
    return $value.Trim()
}

function ConvertTo-SafeFileName {
    param([string]$Value)

    $safe = $Value
    foreach ($character in [System.IO.Path]::GetInvalidFileNameChars()) {
        $safe = $safe.Replace([string]$character, '_')
    }
    $safe = $safe -replace '[\x00-\x1F]', '_'
    $safe = $safe -replace '\s+', ' '
    $safe = $safe.Trim(' ', '.')
    if ($safe.Length -gt 120) { $safe = $safe.Substring(0, 120).Trim() }
    if ([string]::IsNullOrWhiteSpace($safe)) { $safe = 'Untitled' }
    return $safe
}

function Test-TitleStartsWithDate {
    param([string]$Title)

    # OneNote year sections use both full ISO-like dates (2026-05-19) and
    # year-implied month/day dates (3/16).  Both satisfy the user's rule that
    # the page title must start with a date.
    $patterns = @(
        '^\d{4}[-./]\d{1,2}[-./]\d{1,2}(?:\s|$)',
        '^\d{1,2}/\d{1,2}(?:\s|$)',
        '^\d{4}년\s*\d{1,2}월\s*\d{1,2}일(?:\s|$)',
        '^\d{1,2}월\s*\d{1,2}일(?:\s|$)'
    )
    foreach ($pattern in $patterns) {
        if ($Title -match $pattern) { return $true }
    }
    return $false
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Get-GraphGroupKey {
    param([string]$Title)

    if ($Title -match '(?i)mathematica\s+shadow\s+tensor') {
        return 'Shadow Tensor Mathematica 연속 실험'
    }
    if ($Title -match '^로컬 AI 고려') {
        return '로컬 AI 연구 인프라 검토'
    }
    if ($Title -match '(?i)CUDA\s+for\s+colab') {
        return 'CUDA 및 Colab 실행 환경'
    }
    return $Title
}

$rawRoot = Join-Path $OutputRoot '원문-pages'
$corpusRoot = Join-Path $OutputRoot 'graph-corpus'
New-Item -ItemType Directory -Path $rawRoot -Force | Out-Null
New-Item -ItemType Directory -Path $corpusRoot -Force | Out-Null

# These two directories are generated exclusively by this script. Remove the
# previous Markdown snapshot so pages excluded by a later filter cannot linger.
foreach ($generatedRoot in @($rawRoot, $corpusRoot)) {
    Get-ChildItem -LiteralPath $generatedRoot -File -Filter '*.md' |
        Remove-Item -Force
}

$oneNote = New-Object -ComObject OneNote.Application
$hierarchyXml = ''
$oneNote.GetHierarchy('', 4, [ref]$hierarchyXml)
[xml]$hierarchy = $hierarchyXml

$section = $hierarchy.SelectSingleNode(
    "//*[local-name()='Section' and @name=" +
    "'" + $SectionName.Replace("'", "&apos;") + "']"
)
if ($null -eq $section) {
    throw "OneNote section not found: $SectionName"
}

$pages = @($section.SelectNodes("./*[local-name()='Page']"))
$indexLines = [System.Collections.Generic.List[string]]::new()
$indexLines.Add("# $SectionName — OneNote 원문 인덱스")
$indexLines.Add("")
$indexLines.Add("- 추출 시각: $([DateTimeOffset]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz'))")
$indexLines.Add("- 원본 페이지 수: $($pages.Count)")
$indexLines.Add("- 원본 OneNote: $SourceUrl")
$indexLines.Add("")

$grouped = [ordered]@{}
$exportedCount = 0
$sensitiveSkippedCount = 0
$undatedSkippedCount = 0
$pageNumber = 0

foreach ($page in $pages) {
    $pageNumber++
    $title = [string]$page.name

    if ($title -match '(?i)(AI|API)\s*Key|password|secret|access\s*token') {
        $sensitiveSkippedCount++
        continue
    }

    if (-not (Test-TitleStartsWithDate $title)) {
        $undatedSkippedCount++
        continue
    }

    $pageXml = ''
    $oneNote.GetPageContent([string]$page.ID, [ref]$pageXml, 0)
    [xml]$pageDocument = $pageXml
    $pageNode = $pageDocument.DocumentElement

    $bodyBlocks = [System.Collections.Generic.List[string]]::new()
    foreach ($textNode in $pageDocument.SelectNodes("//*[local-name()='T']")) {
        $plain = Convert-HtmlFragmentToMarkdown ([string]$textNode.InnerText)
        if (-not [string]::IsNullOrWhiteSpace($plain) -and $plain -ne $title) {
            $bodyBlocks.Add($plain)
        }
    }

    $ocrBlocks = [System.Collections.Generic.List[string]]::new()
    foreach ($ocrNode in $pageDocument.SelectNodes("//*[local-name()='OCRText']")) {
        $ocr = ([string]$ocrNode.InnerText).Trim()
        if (-not [string]::IsNullOrWhiteSpace($ocr)) {
            $ocrBlocks.Add($ocr)
        }
    }

    $attachmentNames = [System.Collections.Generic.List[string]]::new()
    foreach ($fileNode in $pageDocument.SelectNodes("//*[local-name()='InsertedFile']")) {
        $preferredName = [string]$fileNode.preferredName
        if (-not [string]::IsNullOrWhiteSpace($preferredName)) {
            $attachmentNames.Add($preferredName)
        }
    }

    $created = [string]$pageNode.dateTime
    $modified = [string]$pageNode.lastModifiedTime
    $numberText = $pageNumber.ToString('000')
    $safeTitle = ConvertTo-SafeFileName $title
    $fileName = "$numberText $safeTitle.md"
    $rawPath = Join-Path $rawRoot $fileName

    $markdown = [System.Collections.Generic.List[string]]::new()
    $markdown.Add('---')
    $markdown.Add('source_type: OneNote')
    $markdown.Add("notebook: 'inhwan의 전자 필기장'")
    $markdown.Add("section: '$($SectionName.Replace("'", "''"))'")
    $markdown.Add("page_number: $pageNumber")
    $markdown.Add("created: '$created'")
    $markdown.Add("last_modified: '$modified'")
    if (-not [string]::IsNullOrWhiteSpace($SourceUrl)) {
        $markdown.Add("source_url: '$($SourceUrl.Replace("'", "''"))'")
    }
    $markdown.Add('---')
    $markdown.Add('')
    $markdown.Add("# $title")
    $markdown.Add('')
    $markdown.Add('## 본문')
    $markdown.Add('')
    if ($bodyBlocks.Count -eq 0) {
        $markdown.Add('_텍스트 본문 없음_')
    } else {
        $markdown.Add(($bodyBlocks -join "`n`n"))
    }

    if ($ocrBlocks.Count -gt 0) {
        $markdown.Add('')
        $markdown.Add('## 이미지 OCR')
        $markdown.Add('')
        $markdown.Add(($ocrBlocks -join "`n`n---`n`n"))
    }

    if ($attachmentNames.Count -gt 0) {
        $markdown.Add('')
        $markdown.Add('## 첨부파일 이름')
        $markdown.Add('')
        foreach ($attachmentName in $attachmentNames) {
            $markdown.Add("- $attachmentName")
        }
    }

    Write-Utf8NoBom -Path $rawPath -Content ($markdown -join "`n")
    $exportedCount++
    $indexLines.Add("- [[$fileName|$title]]")

    $groupKey = Get-GraphGroupKey $title
    if (-not $grouped.Contains($groupKey)) {
        $grouped[$groupKey] = [System.Collections.Generic.List[object]]::new()
    }
    $grouped[$groupKey].Add([pscustomobject]@{
        Title = $title
        PageNumber = $pageNumber
        FileName = $fileName
        Created = $created
        Modified = $modified
        Body = ($bodyBlocks -join "`n`n")
        Ocr = ($ocrBlocks -join "`n`n---`n`n")
    })
}

Write-Utf8NoBom -Path (Join-Path $rawRoot 'INDEX.md') -Content ($indexLines -join "`n")

$groupNumber = 0
foreach ($entry in $grouped.GetEnumerator()) {
    $groupNumber++
    $groupTitle = [string]$entry.Key
    $safeGroupTitle = ConvertTo-SafeFileName $groupTitle
    $groupPath = Join-Path $corpusRoot ("{0} {1}.md" -f $groupNumber.ToString('000'), $safeGroupTitle)
    $groupMarkdown = [System.Collections.Generic.List[string]]::new()
    $groupMarkdown.Add('---')
    $groupMarkdown.Add('source_type: OneNote-derived corpus')
    $groupMarkdown.Add("section: '$($SectionName.Replace("'", "''"))'")
    $groupMarkdown.Add("source_page_count: $($entry.Value.Count)")
    $groupMarkdown.Add('---')
    $groupMarkdown.Add('')
    $groupMarkdown.Add("# $groupTitle")

    foreach ($item in $entry.Value) {
        $groupMarkdown.Add('')
        $groupMarkdown.Add("## 원문 페이지 $($item.PageNumber): $($item.Title)")
        $groupMarkdown.Add('')
        $groupMarkdown.Add("- 원문: [[../원문-pages/$($item.FileName)|$($item.Title)]]")
        $groupMarkdown.Add("- 생성: $($item.Created)")
        $groupMarkdown.Add("- 수정: $($item.Modified)")
        $groupMarkdown.Add('')
        if ([string]::IsNullOrWhiteSpace($item.Body)) {
            $groupMarkdown.Add('_텍스트 본문 없음_')
        } else {
            $groupMarkdown.Add($item.Body)
        }
        if (-not [string]::IsNullOrWhiteSpace($item.Ocr)) {
            $groupMarkdown.Add('')
            $groupMarkdown.Add('### 이미지 OCR')
            $groupMarkdown.Add('')
            $groupMarkdown.Add($item.Ocr)
        }
    }

    Write-Utf8NoBom -Path $groupPath -Content ($groupMarkdown -join "`n")
}

$manifest = [ordered]@{
    section = $SectionName
    source_url = $SourceUrl
    source_page_count = $pages.Count
    exported_page_count = $exportedCount
    sensitive_skipped_count = $sensitiveSkippedCount
    undated_skipped_count = $undatedSkippedCount
    accepted_date_title_formats = @('YYYY-MM-DD', 'YYYY.MM.DD', 'YYYY/MM/DD', 'M/D', 'YYYY년 M월 D일', 'M월 D일')
    graph_corpus_file_count = $grouped.Count
    exported_at = [DateTimeOffset]::Now.ToString('o')
}
Write-Utf8NoBom -Path (Join-Path $OutputRoot 'import-manifest.json') -Content ($manifest | ConvertTo-Json -Depth 4)

[pscustomobject]$manifest
