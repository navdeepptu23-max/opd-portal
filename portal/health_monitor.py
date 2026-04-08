import requests
import time

HEALTH_URL = 'http://localhost:5000/health'  # Change to deployed URL if needed
CHECK_INTERVAL = 60  # seconds


def check_health():
    try:
        resp = requests.get(HEALTH_URL, timeout=5)
        if resp.status_code == 200 and resp.json().get('status') == 'healthy':
            return 'healthy'
        else:
            return 'unhealthy'
    except Exception as e:
        return 'unreachable'


def main():
    while True:
        status = check_health()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Health status: {status}")
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
