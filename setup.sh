#!/bin/bash
# Exit on error
set -e

# Install Python 3.11.6 if not already installed
pyenv install -s 3.11.6
pyenv global 3.11.6

# Verify Python version
python --version

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -m flask db upgrade
