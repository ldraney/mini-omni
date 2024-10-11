#!/bin/bash

# Exit on any error
set -e

# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg
if ! command_exists ffmpeg; then
	    echo "Installing FFmpeg..."
	        sudo apt-get update
		    sudo apt-get install -y ffmpeg
fi

# Set PYTHONPATH
export PYTHONPATH=./

# Start the server
echo "Starting the Mini-Omni server..."
python3 server.py --ip '0.0.0.0' --port 60808
