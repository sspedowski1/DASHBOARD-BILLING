#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
python3 "$DIR/src/run_all.py"
