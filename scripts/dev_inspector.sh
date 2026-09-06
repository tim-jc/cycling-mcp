#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f .env ]]; then
    echo "Missing $PROJECT_ROOT/.env" >&2
    exit 1
fi

set -a
source .env
set +a

exec npx @modelcontextprotocol/inspector \
    -e CYCLING_MCP_DB_HOST="$CYCLING_MCP_DB_HOST" \
    -e CYCLING_MCP_DB_PORT="$CYCLING_MCP_DB_PORT" \
    -e CYCLING_MCP_DB_USER="$CYCLING_MCP_DB_USER" \
    -e CYCLING_MCP_DB_PASSWORD="$CYCLING_MCP_DB_PASSWORD" \
    python server.py