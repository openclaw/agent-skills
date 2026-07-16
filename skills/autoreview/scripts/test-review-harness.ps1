[CmdletBinding()]
param(
    [ValidateSet('malicious', 'benign', 'prompt-injection', 'all')]
    [string] $Fixture,

    [ValidateSet('codex', 'claude', 'pi')]
    [string[]] $Engine,

    [ValidateRange(1, 2147483647)]
    [int] $Trials,

    [string] $ArtifactDir,

    [switch] $ReleaseGate,

    [Alias('h')]
    [switch] $Help
)

$ErrorActionPreference = 'Stop'

$Harness = Join-Path $PSScriptRoot 'test-review-harness.py'
$ForwardedArgs = @()

if ($Help) {
    $ForwardedArgs += '--help'
}

if ($PSBoundParameters.ContainsKey('Fixture')) {
    $ForwardedArgs += @('--fixture', $Fixture)
}

if ($PSBoundParameters.ContainsKey('Engine')) {
    foreach ($SelectedEngine in $Engine) {
        $ForwardedArgs += @('--engine', $SelectedEngine)
    }
}

if ($PSBoundParameters.ContainsKey('Trials')) {
    $ForwardedArgs += @('--trials', [string]$Trials)
}

if ($PSBoundParameters.ContainsKey('ArtifactDir')) {
    $ForwardedArgs += @('--artifact-dir', $ArtifactDir)
}

if ($ReleaseGate) {
    $ForwardedArgs += '--release-gate'
}

$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $PyLauncher) {
    & $PyLauncher.Source -3 $Harness @ForwardedArgs
    exit $LASTEXITCODE
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($null -ne $Python) {
    & $Python.Source $Harness @ForwardedArgs
    exit $LASTEXITCODE
}

Write-Error 'Python 3 is required to run test-review-harness.'
exit 127
