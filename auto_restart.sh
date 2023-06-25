#!/bin/bash

# Function to handle the Ctrl+C event
ctrl_c() {
    echo "Ctrl+C detected. Exiting..."
    exit 0
}

# Register the trap signal handler
trap ctrl_c INT

while true; do
    echo "Starting server_rabbit.py with waitress..."
    python3 server_rabbit.py

    if [ $? -eq 0 ]; then
        echo "Server_rabbit.py exited successfully."
    else
        echo "Server_rabbit.py exited with an error. Restarting..."
    fi

    echo "Press Ctrl+C to stop the script or wait for automatic restart."
    sleep 3
done