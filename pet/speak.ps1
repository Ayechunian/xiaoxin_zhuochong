param(
    [Parameter(Mandatory = $true)][string]$Text,
    [ValidateRange(-10, 10)][int]$Rate = 2,
    [ValidateRange(-10, 10)][int]$Pitch = 5,
    [ValidateRange(0, 100)][int]$Volume = 90
)
$ErrorActionPreference = 'Stop'
$speaker = New-Object -ComObject SAPI.SpVoice
$preferred = $null
foreach ($token in $speaker.GetVoices()) {
    if ($token.GetDescription() -like '*Huihui*') {
        $preferred = $token
        break
    }
}
if ($null -ne $preferred) {
    $speaker.Voice = $preferred
}
$speaker.Rate = $Rate
$speaker.Volume = $Volume
$safeText = [System.Security.SecurityElement]::Escape($Text)
$ssml = "<pitch absmiddle='$Pitch'>$safeText</pitch>"
[void]$speaker.Speak($ssml, 8)
