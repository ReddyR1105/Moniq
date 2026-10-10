param([ValidateSet('presentation','walkthrough')][string]$Mode = 'presentation')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$recordingRoot = Join-Path $projectRoot ".runtime\final-recording\$Mode"
$timeline = Get-Content -LiteralPath (Join-Path $recordingRoot 'timeline.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($timeline.fast) { throw 'Preflight footage cannot be published as a final video.' }
Add-Type -AssemblyName System.Speech
$taskSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $taskSynth.SelectVoice('Microsoft Zira Desktop')
    $taskSynth.Rate = 2
    for ($index = 0; $index -lt $timeline.scenes.Count; $index++) {
        $audioPath = Join-Path $recordingRoot ('narration-{0:D2}.wav' -f $index)
        $taskSynth.SetOutputToWaveFile($audioPath)
        $taskSynth.Speak($timeline.scenes[$index].text)
        $taskSynth.SetOutputToNull()
    }
} finally { $taskSynth.Dispose() }
Write-Output "Local narration generated for $Mode."
