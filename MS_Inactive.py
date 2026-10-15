from __future__ import print_function
import datetime
import html
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import requests
import msal
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# Microsoft Edge renders the HTML report to PDF (no extra libraries needed)
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# ====================================
# MICROSOFT 365 CONFIGURATION
# ====================================
# Credentials are read from environment variables (see .env.example).
TENANT_ID = os.environ.get("MS_TENANT_ID")
CLIENT_ID = os.environ.get("MS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET")

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
    print("❌ Missing MS_TENANT_ID / MS_CLIENT_ID / MS_CLIENT_SECRET (see .env.example)")
    exit(1)

# ====================================
# GOOGLE DRIVE CONFIGURATION (for upload)
# ====================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from report_theme import REPORT_CSS
GW_SERVICE_ACCOUNT_FILE = os.path.join(SCRIPT_DIR, "../gw/serviceaccount.json")  # Path to Google service account
GW_ADMIN_EMAIL = os.environ.get("GW_ADMIN_EMAIL", "")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")

# Organization label shown in the report footer
ORG_LABEL = os.environ.get("ORG_LABEL", "Your Organization")

# ====================================
# REPORT CONFIGURATION
# ====================================
REPORT_DATE = datetime.datetime.now().strftime("%m-%d-%Y")
REPORT_NAME = f"ms365_inactive_users_report_{REPORT_DATE}.pdf"
INACTIVITY_DAYS = 30

DRY_RUN = True # Set to False to actually delete/disable users

# Email prefixes to exclude from the report (case-insensitive)
# NOTE: replace these samples with your own shared/role/system accounts.
EXCLUDE_PREFIXES = [
    "admin@", "support@", "service@", "noreply@", "scan@",
    "sales@", "hr@", "marketing@", "receiving@", "accounting@",
    "teams@", "jamf@", "google",  # exclude Google-related accounts/groups
]

# Domains to exclude entirely from the report (case-insensitive)
EXCLUDE_DOMAINS = [
    "partner-domain.example",
    "another-partner.example",
]

# Specific full email addresses to exclude (case-insensitive)
EXCLUDE_EMAILS = [
    "serviceaccount@example.com",
    "automation@example.com",
]

# ====================================
# MICROSOFT AUTHENTICATION
# ====================================
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]

app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET
)

# Get access token
result = app.acquire_token_for_client(scopes=SCOPES)

if "access_token" not in result:
    print(f"❌ Microsoft authentication failed: {result.get('error_description', 'Unknown error')}")
    exit(1)

access_token = result["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

# ====================================
# GOOGLE DRIVE AUTHENTICATION
# ====================================
gw_scopes = ["https://www.googleapis.com/auth/drive.file"]
gw_credentials = service_account.Credentials.from_service_account_file(
    GW_SERVICE_ACCOUNT_FILE, scopes=gw_scopes)
gw_delegated_creds = gw_credentials.with_subject(GW_ADMIN_EMAIL)
drive = build("drive", "v3", credentials=gw_delegated_creds)

# ====================================
# FETCH ALL USERS
# ====================================
print("📊 Fetching users from Microsoft 365...")

users = []
# signInActivity requires Entra ID P1/P2 and the AuditLog.Read.All application permission.
# Graph caps the page size at 120 when signInActivity is selected.
url = "https://graph.microsoft.com/v1.0/users?$select=id,displayName,userPrincipalName,mail,createdDateTime,accountEnabled,signInActivity&$top=120"

while url:
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error fetching users: {response.status_code} - {response.text}")
        exit(1)
    
    data = response.json()
    users.extend(data.get("value", []))
    url = data.get("@odata.nextLink")

print(f"📊 Retrieved {len(users)} total users from Microsoft 365")

# ====================================
# FIND USERS TO REVIEW (based on Entra sign-in activity)
# ====================================
cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=INACTIVITY_DAYS)
cutoff_date = cutoff.date()
inactive_users = []

for user in users:
    email = user.get("userPrincipalName", "") or user.get("mail", "")
    
    # Skip excluded email prefixes (case-insensitive)
    if any(email.lower().startswith(prefix.lower()) for prefix in EXCLUDE_PREFIXES):
        continue
    
    # Skip excluded domains (case-insensitive)
    if any(email.lower().endswith("@" + domain.lower()) for domain in EXCLUDE_DOMAINS):
        continue
    
    # Skip specific excluded email addresses (case-insensitive)
    if email.lower() in [e.lower() for e in EXCLUDE_EMAILS]:
        continue
    
    # Skip disabled accounts (already inactive)
    if not user.get("accountEnabled", True):
        continue
    
    # Skip external/guest users
    if "#EXT#" in email:
        continue
    
    # Check creation date - skip users created within the last 30 days
    created_time = user.get("createdDateTime")
    if created_time:
        try:
            created_dt = datetime.datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            if created_dt > cutoff:
                continue
        except:
            pass
    
    # Check Entra sign-in activity: use the most recent of the interactive,
    # non-interactive and successful sign-in timestamps
    sign_in_activity = user.get("signInActivity") or {}
    sign_in_times = [
        sign_in_activity.get("lastSignInDateTime"),
        sign_in_activity.get("lastNonInteractiveSignInDateTime"),
        sign_in_activity.get("lastSuccessfulSignInDateTime"),
    ]
    sign_in_times = [t for t in sign_in_times if t]

    if sign_in_times:
        try:
            last_sign_in_dt = max(
                datetime.datetime.fromisoformat(t.replace("Z", "+00:00")) for t in sign_in_times
            )
        except ValueError:
            # A sign-in date exists but could not be read: do not treat the user as inactive
            print(f"⚠️  Could not read sign-in date for {email}, skipping")
            continue
        if last_sign_in_dt >= cutoff:
            continue  # User is active, skip
        last_activity = last_sign_in_dt.strftime("%Y-%m-%d")
    else:
        last_activity = "Never"
    
    # Add user with their sign-in activity data
    user["lastSignIn"] = last_activity
    inactive_users.append(user)

# ====================================
# PROCESS USERS & COLLECT REPORT DATA
# ====================================
if DRY_RUN:
    print(f"\n🔍 DRY RUN MODE - No users will be modified\n")
    print(f"Found {len(inactive_users)} users to review (no sign-in in {INACTIVITY_DAYS}+ days):\n")

report_data = []

for user in inactive_users:
    email = user.get("userPrincipalName", "") or user.get("mail", "N/A")
    name = user.get("displayName", "")
    created_time = user.get("createdDateTime", "Unknown")
    last_activity = user.get("lastSignIn", "Unknown")
    
    if DRY_RUN:
        print(f"  • {email} ({name}) - Last sign-in: {last_activity}")
        status = "REVIEW"
    else:
        # Delete the user
        delete_url = f"https://graph.microsoft.com/v1.0/users/{user['id']}"
        delete_response = requests.delete(delete_url, headers=headers)
        
        if delete_response.status_code == 204:
            status = "DELETED"
            print(f"✅ Deleted: {email}")
        else:
            status = f"ERROR ({delete_response.status_code})"
            print(f"❌ Failed to delete {email}: {delete_response.status_code} - {delete_response.text}")
    
    report_data.append({
        "email": email,
        "name": name,
        "creation_time": created_time,
        "last_activity": last_activity,
        "status": status
    })

# ====================================
# GENERATE HTML REPORT (in memory)
# ====================================
def format_date(date_str):
    """Format date string to readable format"""
    if date_str in (None, "Never", "Unknown", "No activity data", ""):
        return date_str if date_str else "Unknown"
    try:
        # Try ISO format first (for creation dates)
        dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except:
        try:
            # Try YYYY-MM-DD format (for sign-in dates)
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%b %d, %Y")
        except:
            return date_str

def get_status_class(status):
    """Return CSS class based on status"""
    if "REVIEW" in status:
        return "status-warning"
    elif "DELETED" in status:
        return "status-success"
    elif "ERROR" in status:
        return "status-error"
    return ""

report_date_display = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")
total_users = len(users)
inactive_count = len(inactive_users)
active_count = total_users - inactive_count

html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Microsoft 365 Inactive Users Report</title>
    <style>
{REPORT_CSS}
    </style>
</head>
<body>
    <div class="container">
        <header class="masthead">
            <div class="header-top">
                <div class="title-block">
                    <p class="kicker">Microsoft 365</p>
                    <h1>Inactive Users Report</h1>
                    <p class="subtitle">Generated on {report_date_display}</p>
                </div>
                <div class="mode-badge {"dry-run" if DRY_RUN else "live"}">
                    {"Dry Run Mode" if DRY_RUN else "Live Execution"}
                </div>
            </div>
        </header>
        <div class="report-body">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Users</div>
                    <div class="stat-value">{total_users}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Inactive ({INACTIVITY_DAYS}+ days)</div>
                    <div class="stat-value inactive">{inactive_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Users</div>
                    <div class="stat-value active">{active_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">{"To Review" if DRY_RUN else "Deleted"}</div>
                    <div class="stat-value">{inactive_count}</div>
                </div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Email</th>
                            <th>Name</th>
                            <th>Created</th>
                            <th>Last Sign-In</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
'''

# Add table rows
for row in report_data:
    escaped_email = html.escape(row["email"])
    escaped_name = html.escape(row["name"]) if row["name"] else "—"
    formatted_created = format_date(row["creation_time"])
    formatted_last_activity = format_date(row["last_activity"])
    status_class = get_status_class(row["status"])
    status_text = "Needs Review" if row["status"] == "REVIEW" else row["status"].title()
    
    html_content += f'''                    <tr>
                        <td><span class="email">{escaped_email}</span></td>
                        <td><span class="name">{escaped_name}</span></td>
                        <td><span class="date">{formatted_created}</span></td>
                        <td><span class="date">{formatted_last_activity}</span></td>
                        <td><span class="status {status_class}">{status_text}</span></td>
                    </tr>
'''

html_content += f'''                </tbody>
            </table>
        </div>
        <footer>
            <p>Microsoft 365 Inactive User Audit • {html.escape(ORG_LABEL)}</p>
        </footer>
        </div>
    </div>
</body>
</html>
'''

# ====================================
# GENERATE PDF REPORT (in memory)
# ====================================
edge_exe = next((p for p in EDGE_PATHS if os.path.exists(p)), None)
if not edge_exe:
    print("❌ Microsoft Edge not found - cannot generate the PDF report")
    exit(1)

with tempfile.TemporaryDirectory() as tmp_dir:
    html_path = pathlib.Path(tmp_dir) / "report.html"
    pdf_path = pathlib.Path(tmp_dir) / "report.pdf"
    html_path.write_text(html_content, encoding="utf-8")

    subprocess.run(
        [
            edge_exe,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--user-data-dir={os.path.join(tmp_dir, 'edge-profile')}",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ],
        check=True,
        timeout=120,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if not pdf_path.exists():
        print("❌ Edge did not produce a PDF report")
        exit(1)

    pdf_buffer = io.BytesIO(pdf_path.read_bytes())

# ====================================
# DONE - PRINT SUMMARY
# ====================================
if DRY_RUN:
    print(f"\n📑 PDF Report: {REPORT_NAME}")
    print(f"ℹ️  This report shows users with no sign-in in the last {INACTIVITY_DAYS} days")
else:
    print(f"\n✅ Done!")
    print(f"📑 PDF Report: {REPORT_NAME}")

# ====================================
# UPLOAD TO GOOGLE DRIVE
# ====================================
def upload_to_drive(file_name, file_buffer, mime_type):
    """Upload a file buffer to Google Drive folder"""
    file_metadata = {
        "name": file_name,
        "parents": [DRIVE_FOLDER_ID]
    }
    media = MediaIoBaseUpload(file_buffer, mimetype=mime_type, resumable=True)
    
    # Check if file already exists and delete it
    results = drive.files().list(
        q=f"name='{file_name}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false",
        fields="files(id)"
    ).execute()
    
    for file in results.get("files", []):
        drive.files().delete(fileId=file["id"]).execute()
    
    # Upload new file
    uploaded = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()
    
    return uploaded.get("webViewLink")

print(f"\n☁️  Uploading PDF report to Google Drive...")

pdf_link = None

try:
    pdf_link = upload_to_drive(REPORT_NAME, pdf_buffer, "application/pdf")
    print(f"✅ PDF uploaded: {pdf_link}")
except HttpError as e:
    print(f"❌ Drive upload failed: {e}")