#!/bin/bash

# Function to handle the Ctrl+C event
ctrl_c() {
    echo "Ctrl+C detected. Exiting..."
    exit 0
}

# Register the trap signal handler
trap ctrl_c INT

while true; do
    echo "Starting image_process.py..."
    python3 image_process.py

    if [ $? -eq 0 ]; then
        echo "image_process.py exited successfully."
    else
        echo "image_process.py exited with an error. Restarting..."
    fi

    echo "Press Ctrl+C to stop the script or wait for automatic restart."
    sleep 3
done