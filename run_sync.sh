#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

python3 sync_stats.py >> "$REPO_DIR/sync.log" 2>&1