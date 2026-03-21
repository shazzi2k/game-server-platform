#!/bin/bash

WEBHOOK="https://discord.com/api/webhooks/1477250838006071297/ThaNqtMprPxnupVdNUPMVIa-jOqvm5qJIqpmatQdud-Afhz2vHFVimP2t8-9HApNZfgK"

curl -s -H "Content-Type: application/json" \
-d '{"content": "**SERVER IS RESTARTING - Planned Shazzi Maintenance**"}' \
$WEBHOOK > /dev/null

sleep 5
reboot
