#!/bin/bash

# Get the directory of the script
SCRIPT_DIR=$(dirname "$0")

# Set the project root directory (one level up from the script directory)
PROJECT_ROOT="$SCRIPT_DIR/.."

# Set the src directory
SRC_DIR="$PROJECT_ROOT/src"

# Set the PYTHONPATH to include the src directory
export PYTHONPATH="$SRC_DIR"

# Navigate to the flask directory
cd "$SRC_DIR" || exit

# Load environment variables from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo ".env file not found in $SRC_DIR"
  exit 1
fi

# Run the Flask app
python3 app.py
