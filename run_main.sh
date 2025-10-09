#!/bin/bash

# --- Configuration ---
PI_SSH_USER="pi"
PI_SSH_HOST="192.168.0.86" # This is the IP of your Raspberry Pi
REPO_PATH="/home/pi/robot-project"
SERVER_HOST="192.168.0.203" # The IP your server listens on
SERVER_PORT=12345

# --- Main Script ---

echo "🤖 Starting the server in the background..."
# Start the server, listening on all interfaces
python3 server.py &
SERVER_PID=$!

# Use a 'trap' to make sure the server is killed even if the script is interrupted (e.g., with Ctrl+C)
trap "echo 'Cleaning up...'; kill $SERVER_PID 2>/dev/null" EXIT

echo "Waiting for server to be ready on port $SERVER_PORT..."
# More reliable way to wait for the server than a fixed 'sleep'
while ! nc -z $SERVER_HOST $SERVER_PORT; do
  sleep 0.5 # wait half a second before checking again
done
echo "Server is ready!"

echo "Running client on the Raspberry Pi via SSH..."

# In your run_main.sh script, replace the ssh line with this:
ssh $PI_SSH_USER@$PI_SSH_HOST "cd $REPO_PATH && . /home/pi/venv/bin/activate && python3 client.py"

# The trap will automatically kill the server when the script exits.
echo "Script finished."


