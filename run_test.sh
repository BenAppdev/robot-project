#!/bin/bash

PI_SSH_USER="pi"
PI_SSH_HOST="192.168.0.86"
REPO_PATH="/home/pi/robot-project"
PI_PASSWORD="102355"  # Replace with Pi's actual password

python3 server.py &
SERVER_PID=$!
sleep 2
sshpass -p "$PI_PASSWORD" ssh $PI_SSH_USER@$PI_SSH_HOST "cd $REPO_PATH && source venv/bin/activate && python3 client.py"
kill $SERVER_PID 2>/dev/null || true
