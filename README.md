# ms365-inactive-users

A Microsoft 365 inactive-user audit. It queries Entra sign-in activity through
Microsoft Graph, flags users with no recent sign-in, renders a clean PDF report,
and optionally uploads it to Google Drive.

Defaults to a dry run, so out of the box it reports and changes nothing.

## What it does

- Pulls every user from Microsoft Graph along with their sign-in activity
- Flags enabled users with no sign-in in a configurable window (default 30 days),
  using the most recent of their interactive, non-interactive, and successful
  sign-in timestamps
- Skips shared, role, and system accounts via prefix, domain, and address
  exclusion lists
- Skips guests and accounts created inside the window (too new to judge)
- Builds an HTML report and renders it to PDF with headless Edge
- Optionally uploads the PDF to a Google Drive folder

With `DRY_RUN = True` (the default) it only reports. Set it to `False` to have it
delete the flagged accounts through Graph. Leave it on `True` unless you know
exactly what you want removed.

## Requirements

- Microsoft Entra ID P1 or P2 (sign-in activity through Graph requires it)
- An Entra app registration with application permissions, admin-consented:
  `User.Read.All` and `AuditLog.Read.All` (plus `User.ReadWrite.All` only if you
  intend to run with `DRY_RUN = False`)
- Python 3.8+ with `msal`, `requests`, `google-api-python-client`, `google-auth`
- Microsoft Edge installed (used to render the PDF)
- Optional, for Drive upload: a Google service account with domain-wide
  delegation and `drive.file` scope

## Setup

Credentials and org-specific values are read from environment variables. Nothing
sensitive lives in the code.

```bash
pip install msal requests google-api-python-client google-auth

export MS_TENANT_ID="your-tenant-id"
export MS_CLIENT_ID="your-app-client-id"
export MS_CLIENT_SECRET="your-client-secret"
export ORG_LABEL="Your Organization"

# Optional, only if using Google Drive upload:
export GW_ADMIN_EMAIL="admin@yourdomain.com"
export DRIVE_FOLDER_ID="your-drive-folder-id"
```

Then edit the exclusion lists near the top of the script
(`EXCLUDE_PREFIXES`, `EXCLUDE_DOMAINS`, `EXCLUDE_EMAILS`) to match the shared and
system accounts in your tenant. The ones included are placeholder samples.

If you want Drive upload, place your service account JSON at `../gw/serviceaccount.json`
(that path is gitignored).

## Usage

```bash
python ms365_inactive_users.py
```

It prints the flagged users, writes a dated PDF, and (if configured) uploads it
to Drive.

## Safety

- Read-only by default. Deleting a user removes their mailbox after the grace
  period, so review the report before ever running with `DRY_RUN = False`.
- Sign-in activity can lag and does not capture every authentication path, so
  treat the results as candidates to review, not a kill list.
- No credentials or tenant data are committed. Everything sensitive comes from
  environment variables and gitignored files.

## License

MIT