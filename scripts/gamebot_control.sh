#!/bin/bash
set -e

source /etc/environment

WEBHOOK="${DISCORD_WEBHOOK}"
SERVICE="gamebot"
ACTION=$1

send_message() {
  curl -s -H "Content-Type: application/json" \
  -d "{\"content\": \"$1\"}" \
  "$WEBHOOK" > /dev/null
}

is_running() {
  docker ps --format '{{.Names}}' | grep -q "^$SERVICE$"
}

# -----------------------------
# STOP
# -----------------------------
if [ "$ACTION" == "stop" ]; then

    if ! is_running; then
        send_message "⚠️ **GameBot is already stopped**"
        exit 0
    fi

    send_message "🛑 **GameBot is stopping (manual/maintenance) Server /commands will not work.**"

    docker stop "$SERVICE"

    sleep 3

    if ! is_running; then
        send_message "🔴 **GameBot is now offline**"
    else
        send_message "⚠️ **GameBot failed to stop properly**"
    fi

    exit 0
fi

# -----------------------------
# START
# -----------------------------
if [ "$ACTION" == "start" ]; then

    if is_running; then
        send_message "⚠️ **GameBot is already running**"
        exit 0
    fi

    send_message "🚀 **GameBot is starting (manual/maintenance) Server /commands will now work**"

    docker start "$SERVICE"

    sleep 10

    if is_running; then
        send_message "🟢 **GameBot is now online**"
    else
        send_message "⚠️ **GameBot failed to start**"
    fi

    exit 0
fi

# -----------------------------
# INVALID
# -----------------------------
echo "Usage: $0 [start|stop]"
exit 1
