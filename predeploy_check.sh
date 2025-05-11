#!/bin/bash
# Pre-deployment validation script for dental_clinic Flask app
set -e

# Create and activate a fresh virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Lint for missing imports and syntax errors
pip install flake8
flake8 app.py app_init_db.py

# Try to run the DB init logic
python -m app_init_db

# Optionally, check main app entrypoint
python -c "from app import app"

# Clean up
deactivate
rm -rf .venv

echo "Pre-deployment validation passed."
