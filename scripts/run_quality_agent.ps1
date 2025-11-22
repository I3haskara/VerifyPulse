#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run the Agentic AI Quality Coach against the VerifyPulse API
.PARAMETER ApiUrl
    Base URL of the API to test (default: http://127.0.0.1:8000)
.PARAMETER CommitHash
    Git commit hash or build identifier
.PARAMETER Output
    Path to the HTML report output
#>

param(
    [string]$ApiUrl = "http://127.0.0.1:8000",
    [string]$CommitHash = "local-dev"
)

$ErrorActionPreference = "Stop"

Write-Host "[Quality Agent] Starting test run..." -ForegroundColor Cyan
Write-Host "  API URL: $ApiUrl" -ForegroundColor Gray
Write-Host "  Commit:  $CommitHash" -ForegroundColor Gray
Write-Host ""

# Activate virtual environment and run
Set-Location "$PSScriptRoot\..\src"

& "..\\.venv\Scripts\python.exe" -m quality_agent.agent_runner `
    --api-url $ApiUrl `
    --commit-hash $CommitHash

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ All tests passed!" -ForegroundColor Green
} elseif ($exitCode -eq 1) {
    Write-Host ""
    Write-Host "❌ Tests failed. Check the diagnostic report in reports/ folder." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "⚠️  Unexpected error (exit code: $exitCode)" -ForegroundColor Red
}

exit $exitCode
