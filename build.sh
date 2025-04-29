#!/bin/bash
set -e

# Install system dependencies
apt-get update && apt-get install -y \
    libmupdf-dev \
    libfreetype6-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    pkg-config

# Create and activate virtual environment
python -m venv --copies /opt/venv
. /opt/venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install wheel
pip install PyMuPDF==1.22.5 --no-build-isolation
pip install -r requirements.txt
