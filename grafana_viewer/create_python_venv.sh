#!/bin/bash
APP_DIR=$(pwd)
VENV_DIR="$APP_DIR/python-venv"

echo "Creating virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing requirements..."
pip install -r "$APP_DIR/requirements.txt"

echo "Done. To activate later, run:"
echo "source $VENV_DIR/bin/activate"
