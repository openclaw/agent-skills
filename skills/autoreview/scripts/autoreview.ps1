$ErrorActionPreference = 'Stop'

$Helper = [IO.Path]::Combine($PSScriptRoot, 'autoreview')
$ForwardedArgs = $args
$Candidates = @(
    @{ Name = 'py'; Arguments = @('-3') },
    @{ Name = 'python3'; Arguments = @() },
    @{ Name = 'python'; Arguments = @() }
)

foreach ($Candidate in $Candidates) {
    # Missing executable names must not trigger unrelated module discovery.
    $Command = $null
    foreach ($Application in $ExecutionContext.InvokeCommand.GetCommands(
        $Candidate.Name, [System.Management.Automation.CommandTypes]::Application, $false
    )) {
        $Command = $Application
        break
    }
    if ($null -eq $Command) {
        continue
    }

    $LauncherArgs = $Candidate.Arguments
    try {
        & $Command.Source @LauncherArgs -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' *> $null
    }
    catch {
        continue
    }
    if ($LASTEXITCODE -ne 0) {
        continue
    }

    & $Command.Source @LauncherArgs $Helper @ForwardedArgs
    exit $LASTEXITCODE
}

[Console]::Error.WriteLine('Python 3.10 or newer is required to run autoreview.')
exit 127
