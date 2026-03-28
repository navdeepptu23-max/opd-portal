import urllib.request, json, time

API_KEY = "rnd_bICKkwAC4B8nCXZZzeD0R2KkvqVk"
SERVICE_ID = "srv-d72evm5m5p6s73d0f0jg"
DEPLOY_ID = "dep-d741b0euk2gs739tjbg0"

for i in range(12):
    time.sleep(15)
    req = urllib.request.Request(
        f"https://api.render.com/v1/services/{SERVICE_ID}/deploys/{DEPLOY_ID}",
        headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    )
    resp = urllib.request.urlopen(req)
    d = json.loads(resp.read().decode())
    status = d.get("status", "unknown")
    print(f"[{(i+1)*15}s] Deploy status: {status}")
    if status == "live":
        print("Deploy is LIVE!")
        break
    elif status in ("deactivated", "build_failed", "update_failed", "canceled"):
        print(f"Deploy FAILED: {status}")
        break
else:
    print("Still deploying... check Render dashboard.")
