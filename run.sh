#!/bin/bash
# ABOUTME: Wrapper script to ensure venv is activated before running main application

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv venv"
    exit 1
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Verify we're in venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment!"
    exit 1
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"
echo ""

# Run the application
echo "🚀 Running YouTube Transcript Processor..."
echo ""
python main.py "$@"
