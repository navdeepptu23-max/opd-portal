# PythonAnywhere Deployment (Free Plan)

This project is ready to deploy on PythonAnywhere.

## Why PythonAnywhere

- Best free fit for Flask apps.
- No card required.
- Simple web UI deployment.

## 1) Create account

- Sign up at https://www.pythonanywhere.com (free plan).

## 2) Open a Bash console and clone project

```bash
git clone https://github.com/YOUR_USERNAME/opdipdreports.git
cd opdipdreports/portal
```

Alternative (one-command bootstrap):

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/opdipdreports/main/portal/pythonanywhere_bootstrap.sh -o ~/pythonanywhere_bootstrap.sh
bash ~/pythonanywhere_bootstrap.sh https://github.com/YOUR_USERNAME/opdipdreports.git
```

This script clones/pulls the repo, creates virtualenv, and installs requirements.

## 3) Create virtual environment and install dependencies

```bash
python3.11 -m venv ~/.venvs/opdportal
source ~/.venvs/opdportal/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Configure environment variables

In PythonAnywhere Web tab, set these environment variables:

- `SECRET_KEY` = a long random string
- `DATABASE_URL` = your database connection string

If you do not provide `DATABASE_URL`, app falls back to SQLite (`portal.db`).

## 5) Create web app

- Go to Web tab.
- Click Add a new web app.
- Choose Manual configuration.
- Choose Python 3.11.

Set:

- Source code: `/home/YOUR_USERNAME/opdipdreports/portal`
- Working directory: `/home/YOUR_USERNAME/opdipdreports/portal`
- Virtualenv: `/home/YOUR_USERNAME/.venvs/opdportal`

## 6) Configure WSGI file

In Web tab, open WSGI configuration file and replace content with:

```python
import os
import sys

PROJECT_PATH = '/home/YOUR_USERNAME/opdipdreports/portal'
if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

os.environ.setdefault('FLASK_ENV', 'production')

from app import app as application
```

You can copy from `portal/pythonanywhere_wsgi.py` and only change username/path.

## 7) Reload app

- Click Reload in Web tab.
- Open your app URL: `https://YOUR_USERNAME.pythonanywhere.com`

## 8) Health check

Open:

- `/health`

Expected response:

```json
{"status": "healthy"}
```

## Update deployment after code changes

```bash
cd ~/opdipdreports
git pull
source ~/.venvs/opdportal/bin/activate
pip install -r portal/requirements.txt
```

Then click Reload in Web tab.
