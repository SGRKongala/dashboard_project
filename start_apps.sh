#!/bin/sh
export PORT=${PORT:-8080}
python3 app_metrics.py &
export PORT=8052
python3 app_corruption.py