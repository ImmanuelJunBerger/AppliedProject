# WRDS access setup

## Credential handling

This project reads WRDS credentials only from environment variables:

- `WRDS_USERNAME`
- `WRDS_PASSWORD`

The code does not hardcode, print, serialize, or commit credentials. The current
session credential status is: **missing WRDS_USERNAME, WRDS_PASSWORD**.

## Local setup

Install the optional connector:

```bash
python -m pip install wrds
```

Set credentials for the current PowerShell session:

```powershell
$env:WRDS_USERNAME = "your_wrds_username"
$env:WRDS_PASSWORD = "your_wrds_password"
python -m src.run_wrds_inventory --scan-all-tables
```

For persistent local configuration, copy `.env.example` to `.env` and load it
with your own shell or secret manager. `.env` and credential-style files are
ignored by git. Do not paste real credentials into source files, notebooks,
reports, command history that is shared, or issue trackers.

## Non-failing behavior

If credentials or the optional `wrds` package are unavailable, this module still
writes planning reports and marks live access as not queried. That is the
expected behavior for CI and credential-free research review.
