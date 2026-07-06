$ErrorActionPreference = "Stop"

Set-Location "C:\Users\junbe\OneDrive\Documents\Applied Project"
$env:PYTHONPATH = "src;C:\Users\junbe\OneDrive\Documents\Applied Project\.codex-wrds-deps"

& "C:\Users\junbe\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  -m src.run_wrds_inventory `
  --prompt-for-credentials `
  --scan-all-tables

Write-Host ""
Write-Host "WRDS inventory command finished. You may close this window after Codex has read the reports."
