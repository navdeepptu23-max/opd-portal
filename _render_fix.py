"""One-time script to create a new Render PostgreSQL database and update DATABASE_URL."""
import urllib.request
import json
import time
import sys

API_KEY = "rnd_bICKkwAC4B8nCXZZzeD0R2KkvqVk"
SERVICE_ID = "srv-d72evm5m5p6s73d0f0jg"  # opd-portal
OWNER_ID = "tea-d6vrmasr85hc739s76bg"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

def api(method, path, data=None):
    url = f"https://api.render.com/v1{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode()) if resp.status != 204 else {}
    except urllib.error.HTTPError as e:
        print(f"ERROR {e.code}: {e.read().decode()}")
        sys.exit(1)

# Step 1: Create new PostgreSQL database
print("Creating new PostgreSQL database 'opd-db-2026'...")
db_result = api("POST", "/postgres", {
    "databaseName": "opdportal",
    "databaseUser": "opduser",
    "name": "opd-db-2026",
    "ownerId": OWNER_ID,
    "plan": "free",
    "region": "oregon",
    "version": "16",
})
db_id = db_result.get("id", "")
print(f"Database created: id={db_id}")
print(f"Status: {db_result.get('status', 'unknown')}")

# Step 2: Wait for database to be available
print("Waiting for database to become available...")
for i in range(30):
    time.sleep(5)
    info = api("GET", f"/postgres/{db_id}")
    status = info.get("status", "unknown")
    print(f"  [{i*5}s] Status: {status}")
    if status == "available":
        break
else:
    print("Database still not available after 150s. Check Render dashboard.")
    sys.exit(1)

# Step 3: Get connection info
print("Getting connection details...")
conn_info = api("GET", f"/postgres/{db_id}/connection-info")
internal_url = conn_info.get("internalConnectionString", "")
external_url = conn_info.get("externalConnectionString", "")
print(f"Internal URL: {internal_url[:30]}..." if internal_url else "No internal URL yet")

if not internal_url:
    print("Using external URL as fallback...")
    internal_url = external_url

if not internal_url:
    print("ERROR: No connection string available. Check Render dashboard.")
    sys.exit(1)

# Step 4: Update DATABASE_URL on the web service
print(f"Updating DATABASE_URL on service {SERVICE_ID}...")
# First get existing env vars
env_vars = api("GET", f"/services/{SERVICE_ID}/env-vars")
# Check if DATABASE_URL exists
db_url_exists = any(ev.get("key") == "DATABASE_URL" for ev in env_vars)

if db_url_exists:
    # Update existing
    api("PUT", f"/services/{SERVICE_ID}/env-vars", [
        {"key": "DATABASE_URL", "value": internal_url}
    ])
else:
    # Create new
    api("PUT", f"/services/{SERVICE_ID}/env-vars", [
        {"key": "DATABASE_URL", "value": internal_url}
    ])

print("DATABASE_URL updated!")

# Step 5: Trigger a deploy
print("Triggering deploy...")
deploy = api("POST", f"/services/{SERVICE_ID}/deploys", {"clearCache": "do_not_clear"})
deploy_id = deploy.get("id", "unknown")
print(f"Deploy triggered: {deploy_id}")
print("\nDone! The service will redeploy with the new database.")
print(f"Database: opd-db-2026 ({db_id})")
print(f"Service: opd-portal ({SERVICE_ID})")
