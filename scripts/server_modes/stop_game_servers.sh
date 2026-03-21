#!/bin/bash

echo "Stopping game servers..."

cd /srv/data/stacks/zomboid && docker compose down
cd /srv/data/stacks/valheim && docker compose down
cd /srv/data/stacks/7day2die && docker compose down

echo "All game servers stopped"
