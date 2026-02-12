#!/bin/bash

# Fix existing cron job to include PATH for copilot command

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3)
LOG_DIR="${SCRIPT_DIR}/logs"

# Detect Node.js bin directory (for copilot command)
NODE_BIN_DIR=""
if command -v node &> /dev/null; then
    NODE_BIN_DIR=$(dirname $(which node))
fi

echo "=== Fixing Cron Job for GitHub Issues Checker ==="
echo ""
echo "Detected paths:"
echo "  Script directory: ${SCRIPT_DIR}"
echo "  Python: ${PYTHON_PATH}"
echo "  Node.js bin: ${NODE_BIN_DIR}"
echo ""

if [ -z "${NODE_BIN_DIR}" ]; then
    echo "⚠️  Warning: Node.js not found. Copilot command may not work."
    echo "   Please install Node.js and GitHub Copilot CLI first."
    exit 1
fi

# Build PATH for cron (include Node.js bin directory for copilot command)
CRON_PATH="${NODE_BIN_DIR}:/usr/local/bin:/usr/bin:/bin"

# New cron command with PATH and necessary environment variables
NEW_CRON_COMMAND="0 * * * * HOME=${HOME} USER=${USER} PATH=${CRON_PATH} cd ${SCRIPT_DIR} && ${PYTHON_PATH} ${SCRIPT_DIR}/check_issues.py >> ${LOG_DIR}/checker.log 2>&1"

echo "Current cron job:"
crontab -l 2>/dev/null | grep "check_issues.py" || echo "  (none found)"
echo ""

echo "New cron job will be:"
echo "  ${NEW_CRON_COMMAND}"
echo ""

read -p "Update the cron job? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Remove old entry and add new one
    (crontab -l 2>/dev/null | grep -v "check_issues.py"; echo "${NEW_CRON_COMMAND}") | crontab -
    
    echo ""
    echo "✅ Cron job updated successfully!"
    echo ""
    echo "Updated crontab:"
    crontab -l | grep "check_issues.py"
    echo ""
    echo "The script will now run every hour with proper PATH settings."
    echo "Monitor logs at: ${LOG_DIR}/checker.log"
else
    echo "Update cancelled."
    exit 0
fi
