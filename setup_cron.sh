#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3)
LOG_DIR="${SCRIPT_DIR}/logs"

echo "=== GitHub Issues Checker - Cron Setup ==="
echo ""

if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    echo "Error: .env file not found. Please create it from .env.example"
    exit 1
fi

mkdir -p "${LOG_DIR}"

echo "Script directory: ${SCRIPT_DIR}"
echo "Python path: ${PYTHON_PATH}"
echo "Log directory: ${LOG_DIR}"
echo ""

CRON_COMMAND="0 * * * * cd ${SCRIPT_DIR} && ${PYTHON_PATH} ${SCRIPT_DIR}/check_issues.py >> ${LOG_DIR}/checker.log 2>&1"

echo "The following cron job will be added (runs every hour):"
echo "${CRON_COMMAND}"
echo ""

read -p "Do you want to add this cron job? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    (crontab -l 2>/dev/null | grep -v "check_issues.py"; echo "${CRON_COMMAND}") | crontab -
    
    echo ""
    echo "✅ Cron job added successfully!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep "check_issues.py"
    echo ""
    echo "To view all cron jobs: crontab -l"
    echo "To edit cron jobs: crontab -e"
    echo "To remove this cron job: crontab -e (and delete the line)"
    echo ""
    echo "Logs will be written to: ${LOG_DIR}/checker.log"
else
    echo "Cron setup cancelled."
    exit 0
fi
