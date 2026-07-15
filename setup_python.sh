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

echo ""
echo "Starting Docker containers for Kafka cluster..."
docker-compose up -d

echo "Waiting for Kafka brokers to be ready..."
sleep 15

echo "Kafka cluster is starting up. Brokers should be available shortly."
echo "Kafka UI will be available at: http://localhost:8080"
echo ""
echo "Setup complete!"
