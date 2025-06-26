#!/bin/bash
# Simple alert script for DB write failures
# Extend this to send email, webhook, or integrate with monitoring

ALERT_MSG="$1"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
echo "[ALERT][${TIMESTAMP}] DB Write Failure: $ALERT_MSG" >> /tmp/db_write_alerts.log

# Example: send to webhook (uncomment and set URL)
# curl -X POST -H "Content-Type: application/json" -d "{\"alert\": \"$ALERT_MSG\"}" http://your-webhook-url

# Example: send email (requires mailx)
# echo "$ALERT_MSG" | mail -s "DB Write Failure Alert" you@example.com