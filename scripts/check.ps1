param(
    [ValidateSet("Quick", "Full")]
    [string]$Mode = "Full",
    [ValidateRange(1, 8)]
    [int]$Workers = 2,
    [string]$LogDirectory = ""
)

$ErrorActionPreference = "Stop"
try {
    $arguments = @("$PSScriptRoot/run_validation.py", "--mode", $Mode, "--workers", $Workers)
    if ($LogDirectory) {
        $arguments += @("--log-directory", $LogDirectory)
    }
    python @arguments
    exit $LASTEXITCODE
} catch {
    Write-Error $_
    exit 1
}
