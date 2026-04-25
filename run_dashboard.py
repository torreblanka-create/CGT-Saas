#!/usr/bin/env python
import subprocess
import sys

# Run streamlit app
subprocess.run([
    sys.executable, '-m', 'streamlit', 'run', 'app.py',
    '--server.port', '8503',
    '--server.headless', 'true'
], cwd='.')
