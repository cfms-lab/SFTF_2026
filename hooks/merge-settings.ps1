<#
  merge-settings.ps1
  소스 settings.json 의 hooks 설정을 대상 settings.json 에 병합한다.
  - 대상의 기존 최상위 키와 다른 훅 이벤트는 그대로 보존
  - 소스에 있는 이벤트(PostToolUse/Stop/Notification/SessionStart)는 갱신(덮어씀)
  - 명령 문자열의 %USERPROFILE% 는 실제 절대경로로 치환
  - 기존 대상 파일은 .bak 으로 백업, BOM 없는 UTF-8 로 저장
#>
param(
  [Parameter(Mandatory = $true)][string]$SrcSettings,
  [Parameter(Mandatory = $true)][string]$DestSettings
)
$ErrorActionPreference = 'Stop'

function Resolve-Vars($node) {
  if ($node -is [string]) {
    return $node.Replace('%USERPROFILE%', $env:USERPROFILE)
  }
  elseif ($node -is [System.Management.Automation.PSCustomObject]) {
    foreach ($p in $node.PSObject.Properties) {
      $p.Value = Resolve-Vars $p.Value
    }
    return $node
  }
  elseif (($node -is [System.Collections.IEnumerable]) -and ($node -isnot [string])) {
    $arr = @()
    foreach ($i in $node) { $arr += , (Resolve-Vars $i) }
    return , $arr
  }
  else {
    return $node
  }
}

# 1) 소스 로드 + 경로 변수 해석
$src = (Get-Content -LiteralPath $SrcSettings -Raw) | ConvertFrom-Json
$src = Resolve-Vars $src

# 2) 대상 로드 (없으면 빈 객체), 있으면 백업
if (Test-Path -LiteralPath $DestSettings) {
  Copy-Item -LiteralPath $DestSettings -Destination "$DestSettings.bak" -Force
  Write-Host "  backup -> $DestSettings.bak"
  $dst = (Get-Content -LiteralPath $DestSettings -Raw) | ConvertFrom-Json
}
else {
  $dst = [PSCustomObject]@{}
}

# 3) hooks 키 보장
if (-not ($dst.PSObject.Properties.Name -contains 'hooks')) {
  $dst | Add-Member -NotePropertyName 'hooks' -NotePropertyValue ([PSCustomObject]@{})
}

# 4) 이벤트별 병합
foreach ($evt in $src.hooks.PSObject.Properties) {
  if ($dst.hooks.PSObject.Properties.Name -contains $evt.Name) {
    $dst.hooks.$($evt.Name) = $evt.Value
    Write-Host "  update event: $($evt.Name)"
  }
  else {
    $dst.hooks | Add-Member -NotePropertyName $evt.Name -NotePropertyValue $evt.Value
    Write-Host "  add event:    $($evt.Name)"
  }
}

# 5) 저장 (디렉터리 보장 + BOM 없는 UTF-8)
$dir = Split-Path -Parent $DestSettings
if (-not (Test-Path -LiteralPath $dir)) {
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$json = $dst | ConvertTo-Json -Depth 20
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($DestSettings, $json, $enc)

Write-Host "  settings.json updated -> $DestSettings"
