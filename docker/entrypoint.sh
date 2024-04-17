#!/bin/bash

if [ -z "$SCRIPT_NAME" ]; then
    echo "Invalid parameter SCRIPT_NAME. Please input 'backup' or 'restore'."
    exit 
else
  if [ "$SCRIPT_NAME" = "backup" ]; then
    python3 backup.py
  else
    while true; do
      sleep 3600
    done
  fi
fi
