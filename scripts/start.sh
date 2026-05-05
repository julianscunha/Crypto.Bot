#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting API..."
uvicorn apps.api.main:app --reload
