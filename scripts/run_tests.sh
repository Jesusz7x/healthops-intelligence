#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m py_compile api/*.py processing/*.py
