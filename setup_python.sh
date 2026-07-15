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
echo "Setting up frontend dependencies..."
echo "Installing Node.js and npm..."
apt install -y nodejs npm

echo "Navigating to frontend directory..."
cd streamsocial/frontend

echo "Initializing npm project..."
npm init -y

echo "Installing React and frontend dependencies..."
npm install react@18.3.1 react-dom@18.3.1 react-scripts@5.0.1 axios@1.7.2 recharts@2.12.7

echo "Frontend dependencies installed successfully!"
npm --version

echo "Returning to project root..."
cd ../../

echo ""
echo "Starting Docker containers for Kafka cluster..."
docker-compose up -d

echo "Waiting for Kafka brokers to be ready..."
sleep 15

echo "Kafka cluster is starting up. Brokers should be available shortly."
echo "Kafka UI will be available at: http://localhost:8080"
echo ""
echo "Setup complete!"
