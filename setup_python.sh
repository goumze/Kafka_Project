#!/bin/bash

# Script to install Python 3.11 and set up virtual environment

echo "Installing Python 3.11..."
apt update
apt install -y python3.11 python3.11-venv python3-pip

echo "Creating virtual environment..."
python3.11 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Python environment setup complete!"
python --version
