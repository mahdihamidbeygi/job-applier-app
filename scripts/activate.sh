#!/bin/bash

if [ -d "venv" ]; then
    echo "🔌 Activating virtual environment..."
    echo ""
    echo "Run this command to activate the environment:"
    echo "  source venv/bin/activate"
    echo ""
    echo "Note: You cannot source a script that's executed with ./"
    echo "You must use: source scripts/activate.sh"
else
    echo "❌ No virtual environment found!"
    echo "Run ./scripts/init_codespace.sh first"
fi