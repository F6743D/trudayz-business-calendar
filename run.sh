#!/usr/bin/env bash

# 1. Source the isolated configuration variables
if [ -f ~/business-day-calendar/.env ]; then
    source ~/business-day-calendar/.env
    echo "[System] Isolated environment variables successfully injected."
else
    echo "[Warning] No .env configuration file found."
fi

# 2. Automatically kill lingering background processes on your port
pkill -9 -f server.py
sleep 1

# 3. Start the application server natively
python3 ~/business-day-calendar/server.py
