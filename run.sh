#!/usr/bin/env bash
cd "$(dirname "$0")/backend" && python3 -m uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8000
