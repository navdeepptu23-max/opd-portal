"""WSGI config template for PythonAnywhere.

Copy this content into your PythonAnywhere WSGI file and update PROJECT_PATH
if your clone location is different.
"""

import os
import sys

# Change this if your repository is in a different location.
PROJECT_PATH = '/home/YOUR_USERNAME/opdipdreports/portal'

if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

# Optional: make environment explicit for production.
os.environ.setdefault('FLASK_ENV', 'production')

from app import app as application  # noqa: E402
