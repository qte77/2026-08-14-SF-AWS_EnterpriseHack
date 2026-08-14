#!/usr/bin/env bash
# Restart Ledgerline with a clean ledger. Kept as a script so `pkill -f` cannot
# match the invoking shell's own command line.
set -u
cd "$(dirname "$0")/.."
LOG="${1:-/tmp/ledgerline-uvicorn.log}"

pkill -f "ledgerline.app:app" >/dev/null 2>&1
sleep 1
rm -f ledgerline.db

# 0.0.0.0 so a forwarded port (devcontainer, Codespaces, SSH tunnel) reaches it.
PYTHONPATH=src setsid nohup .venv/bin/python -m uvicorn ledgerline.app:app \
  --host 0.0.0.0 --port 8000 >"$LOG" 2>&1 &
sleep 4
tail -3 "$LOG"

echo
echo "  Ledgerline   http://localhost:8000/"
echo "  Audit trail  http://localhost:8000/ui/audit-trail.html"
echo "  Seed it      uv run python scripts/e2e.py"
