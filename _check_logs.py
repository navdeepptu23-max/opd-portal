import urllib.request, json, sys, os, time, secrets

API_KEY = "rnd_bICKkwAC4B8nCXZZzeD0R2KkvqVk"
SERVICE_ID = "srv-d72evm5m5p6s73d0f0jg"
OWNER_ID = "tea-d6vrmasr85hc739s76bg"
OLD_DB_ID = "dpg-d70kpnvfte5s73fnh4ng-a"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_status.txt")

def log(msg):
    with open(OUT, "a") as f:
        f.write(msg + "\n")

def api(method, path, data=None):
    url = f"https://api.render.com/v1{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }, method=method)
    try:
        resp = urllib.request.urlopen(req)
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        msg = f"HTTP {e.code}: {e.read().decode()}"
        log(f"ERROR: {msg}")
        return {"error": msg}

# Clear output
with open(OUT, "w") as f:
    f.write("")

# Step 1: Delete old Singapore database
log("Step 1: Deleting Singapore database...")
result = api("DELETE", f"/postgres/{OLD_DB_ID}")
if "error" in result:
    log(f"Delete failed: {result['error']}")
else:
    log("Old database deleted.")

# Wait for deletion to propagate
time.sleep(5)

# Step 2: Create new Oregon database 
log("Step 2: Creating new Oregon database...")
db_result = api("POST", "/postgres", {
    "databaseName": "opdportal",
    "databaseUser": "opduser",
    "name": "opd-db-oregon",
    "ownerId": OWNER_ID,
    "plan": "free",
    "region": "oregon",
    "version": "16",
})
if "error" in db_result:
    log(f"Create failed: {db_result['error']}")
    sys.exit(1)

db_id = db_result.get("id", "")
log(f"Database created: {db_id}")

# Step 3: Wait for database to be available
log("Step 3: Waiting for database...")
for i in range(30):
    time.sleep(5)
    info = api("GET", f"/postgres/{db_id}")
    status = info.get("status", "unknown")
    log(f"  [{(i+1)*5}s] {status}")
    if status == "available":
        break
    if "error" in info:
        break

# Step 4: Get connection string
log("Step 4: Getting connection string...")
conn = api("GET", f"/postgres/{db_id}/connection-info")
internal_url = conn.get("internalConnectionString", "")
external_url = conn.get("externalConnectionString", "")
# Use internal since both are now in Oregon
db_url = internal_url or external_url
log(f"Connection URL: {db_url[:50]}...")

if not db_url:
    log("ERROR: No connection string!")
    sys.exit(1)

# Step 5: Update env vars (all of them)
log("Step 5: Updating environment variables...")
all_vars = [
    {"key": "DATABASE_URL", "value": db_url},
    {"key": "PYTHON_VERSION", "value": "3.11.0"},
    {"key": "SECRET_KEY", "value": secrets.token_hex(32)},
]
api("PUT", f"/services/{SERVICE_ID}/env-vars", all_vars)
log("Env vars updated.")

# Step 6: Trigger deploy
log("Step 6: Triggering deploy...")
deploy = api("POST", f"/services/{SERVICE_ID}/deploys", {"clearCache": "do_not_clear"})
deploy_id = deploy.get("id", "unknown")
log(f"Deploy triggered: {deploy_id}")

# Step 7: Wait for deploy
log("Step 7: Waiting for deploy...")
for i in range(24):
    time.sleep(15)
    d = api("GET", f"/services/{SERVICE_ID}/deploys/{deploy_id}")
    ds = d.get("status", "unknown")
    log(f"  [{(i+1)*15}s] {ds}")
    if ds == "live":
        log("DEPLOY IS LIVE!")
        break
    if ds in ("deactivated", "build_failed", "update_failed", "canceled"):
        log(f"DEPLOY FAILED: {ds}")
        break
else:
    log("Still deploying after 6 min. Check Render dashboard.")

log("DONE.")

# Check latest events
print("\n--- Latest events ---", flush=True)
req2 = urllib.request.Request(
    f"https://api.render.com/v1/services/{SERVICE_ID}/events?limit=3",
    headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
)
resp2 = urllib.request.urlopen(req2)
data2 = json.loads(resp2.read().decode())
for entry in data2:
    ev = entry.get("event", entry)
    t = ev.get("type", "unknown")
    details = ev.get("details", {})
    status = details.get("deployStatus", details.get("buildStatus", ""))
    print(f"  {t}: {status}", flush=True)
