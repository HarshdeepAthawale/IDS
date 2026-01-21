#!/usr/bin/env pwsh
# PowerShell script to resume MongoDB import
# Usage: .\resume_import.ps1

Write-Host "Resuming MongoDB Import..." -ForegroundColor Green
Write-Host ""

python scripts/import_cicids2018.py `
    --input-file data/cicids2018_preprocessed.json `
    --batch-size 20000 `
    --labeled-by cicids2018 `
    --resume

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Import failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Import completed successfully!" -ForegroundColor Green
