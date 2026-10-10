#!/bin/zsh

set -eu

CONFIG_FILE="${HOME}/.config/class8/airtag-collector.env"
if [[ ! -r "${CONFIG_FILE}" ]]; then
  print -u2 "ERROR: collector configuration is missing: ${CONFIG_FILE}"
  exit 1
fi

set -a
source "${CONFIG_FILE}"
set +a

exec /Users/automation/shared/webapp-venv/bin/python \
  /Users/automation/repos/nixonai/scripts/airtag_chassis_collector.py
