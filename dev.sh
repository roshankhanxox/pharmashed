#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$API_PID" "$WEB_PID" 2>/dev/null
  wait "$API_PID" "$WEB_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

echo "Starting PharmaShed dev environment..."

# API on :8000 with fixtures
cd "$ROOT"
PHARMASHED_DATA=contracts/fixtures \
  uv run uvicorn pharmashed_api.main:app --reload --port 8000 &
API_PID=$!

# Web on :5173
cd "$ROOT/web"
pnpm dev &
WEB_PID=$!

echo ""
echo "  API  → http://localhost:8000/docs"
echo "  Web  → http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."

wait
