#!/usr/bin/env bash
set -euo pipefail
# Run API server
uvicorn apps.api.main:app --reload
