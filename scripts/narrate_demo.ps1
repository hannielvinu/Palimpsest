param(
    [Parameter(Mandatory)][string]$NarrationPath,
    [Parameter(Mandatory)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$chapters = Get-Content -LiteralPath $NarrationPath -Raw -Encoding UTF8 | ConvertFrom-Json
$voice = New-Object -ComObject SAPI.SpVoice
$selectedVoice = $voice.GetVoices() | Where-Object { $_.GetDescription() -like '*Hazel*' } | Select-Object -First 1
if ($selectedVoice) { $voice.Voice = $selectedVoice }
$voice.Rate = 2
for ($index = 0; $index -lt $chapters.Count; $index++) {
    $stream = New-Object -ComObject SAPI.SpFileStream
    $path = Join-Path $OutputDirectory ('voice-{0:00}.wav' -f $index)
    $stream.Open($path, 3, $false)
    try {
        $voice.AudioOutputStream = $stream
        [void]$voice.Speak($chapters[$index], 0)
    } finally {
        $stream.Close()
    }
}
