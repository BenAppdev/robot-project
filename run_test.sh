#!/bin/bash

PI_SSH_USER="pi"
PI_SSH_HOST="192.168.0.86"
REPO_PATH="/home/pi/robot-project"

python3 server.py &
SERVER_PID=$!
sleep 2
ssh $PI_SSH_USER@$PI_SSH_HOST "cd $REPO_PATH && source venv/bin/activate && cd robot-project && python3 client.py"
kill $SERVER_PID 2>/dev/null || true
