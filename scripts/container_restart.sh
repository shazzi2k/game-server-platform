#!/bin/bash

WEBHOOK="https://discord.com/api/webhooks/1477250838006071297/ThaNqtMprPxnupVdNUPMVIa-jOqvm5qJIqpmatQdud-Afhz2vHFVimP2t8-9HApNZfgK"
SERVICE=$1
LOCKFILE="/tmp/${SERVICE}_restart.lock"

if [ -f "$LOCKFILE" ]; then
    echo "Restart already in progress for $SERVICE"
    exit 1
fi

touch "$LOCKFILE"

send_message() {
curl -s -H "Content-Type: application/json" \
-d "{\"content\": \"$1\"}" \
"$WEBHOOK" > /dev/null
}

send_message "**Container ${SERVICE^^} is restarting (planned)**"

docker stop -t 180 "$SERVICE"
sleep 5
docker start "$SERVICE"

sleep 20

if docker ps --format '{{.Names}}' | grep -q "^$SERVICE$"; then
    send_message "**Container ${SERVICE^^} is now online**"
else
    send_message "⚠️ **CH SHIT! Container ${SERVICE^^} failed to start! Someone call Shazzi.**"
fi

rm -f "$LOCKFILE"
