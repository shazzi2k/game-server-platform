import time
import json
import datetime
import a2s
import socket
import requests
import os
from mcrcon import MCRcon
import subprocess

# -----------------------
# CONFIG
# -----------------------

STATE_FILE = "/srv/data/stacks/game-server-platform/server_state.json"
VM_IP = "192.168.0.58"
IDLE_LIMIT = 3600  # 1 hour

GAMES = {
    "zomboid": {"ip": "192.168.0.96"},
    "7days2die": {"ip": "192.168.0.96", "port": 26900},
    "valheim": {"ip": "192.168.0.96", "port": 2457}
}

VM_GAMES = ["arma3", "sons", "dcs"]

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/XXXX"

# -----------------------
# STATE
# -----------------------

state = {
    "games": {},
    "vm_games": {},
    "vm": {"idle": 0}
}

last_seen = {}
vm_last_seen = {}
vm_idle_start = None
shutdown_triggered = {}

# -----------------------
# HELPERS
# -----------------------

def send_discord(msg):
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg})
    except:
        pass


def check_port(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.sendto(b"\xFF\xFF\xFF\xFFTSource Engine Query\x00", (ip, port))
        sock.recvfrom(4096)
        return True
    except:
        return False


def is_zomboid_online():
    try:
        with socket.create_connection(("192.168.0.96", 16261), 2):
            return True
    except:
        return False


def get_arma_players():
    try:
        info = a2s.info((VM_IP, 2302), 5.0)
        return info.player_count
    except:
        return 0


def get_players(ip, port):
    try:
        info = a2s.info((ip, port), 5.0)
        return info.player_count
    except:
        return 0


def get_zomboid_players():
    try:
        result = subprocess.run(
            ["docker", "exec", "zomboid", "cat", "/root/Zomboid/server-console.txt"],
            capture_output=True,
            text=True
        )

        data = result.stdout.lower()
        active_guids = set()

        for line in data.splitlines():
            if "guid=" not in line:
                continue

            try:
                guid = line.split("guid=")[1].split()[0]
            except:
                continue

            if "fully-connected" in line:
                active_guids.add(guid)

            elif '[disconnect]' in line and 'receive-disconnect' in line:
                active_guids.discard(guid)

        return len(active_guids)

    except:
        return 0


def shutdown_zomboid():
    try:
        with MCRcon("192.168.0.96", "shaz123", port=27015) as mcr:
            mcr.command("save")
            mcr.command("quit")
    except:
        pass


def is_vm_up():
    try:
        with socket.create_connection((VM_IP, 3389), 2):
            return True
    except:
        return False


def write_state():
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# -----------------------
# MAIN LOOP
# -----------------------

while True:

    now = datetime.datetime.now(datetime.UTC)

    # =======================
    # DOCKER GAMES
    # =======================

    for game, cfg in GAMES.items():

        if game == "zomboid":
            online = is_zomboid_online()
        else:
            online = check_port(cfg["ip"], cfg["port"])

        if not online:
            state["games"][game] = {
                "players": 0,
                "idle": 0,
                "status": "offline"
            }
            last_seen[game] = None
            continue

        # player count
        players = get_zomboid_players() if game == "zomboid" else get_players(cfg["ip"], cfg["port"])

        # activity tracking
        if last_seen.get(game) is None:
            last_seen[game] = now

        if players > 0:
            last_seen[game] = now

        idle = (now - last_seen[game]).total_seconds()

        # shutdown
        if game == "zomboid":
            if idle > IDLE_LIMIT and not shutdown_triggered.get(game):
                send_discord("Zomboid shutting down due to inactivity")
                shutdown_zomboid()
                shutdown_triggered[game] = True
            elif idle <= IDLE_LIMIT:
                shutdown_triggered[game] = False

        state["games"][game] = {
            "players": players,
            "idle": idle,
            "status": "active" if players > 0 else "idle"
        }

    # =======================
    # VM GAMES (FIXED LOOP)
    # =======================

    try:
        vm_data = requests.get(f"http://{VM_IP}:6000/status", timeout=2).json()
    except:
        vm_data = {}

    any_vm_running = False

    for game in VM_GAMES:

        game_info = vm_data.get(game, {})
        running = game_info.get("running", False)

        players = get_arma_players() if game == "arma3" else game_info.get("players", 0)

        if not running:
            vm_last_seen[game] = None
            state["vm_games"][game] = {
                "players": 0,
                "idle": 0,
                "status": "offline"
            }
            continue

        any_vm_running = True

        # tracking
        if vm_last_seen.get(game) is None:
            vm_last_seen[game] = now

        if players > 0:
            vm_last_seen[game] = now

        idle = (now - vm_last_seen[game]).total_seconds()

        # arma shutdown
        if game == "arma3":
            if idle > IDLE_LIMIT and not shutdown_triggered.get(game):
                send_discord("🛑 Arma 3 shutting down due to inactivity")

                os.system(
                    "/usr/bin/virsh qemu-agent-command windows-gaming "
                    "'{\"execute\":\"guest-exec\",\"arguments\":"
                    "{\"path\":\"C:\\\\Windows\\\\System32\\\\taskkill.exe\","
                    "\"arg\":[\"/F\",\"/IM\",\"arma3server_x64.exe\"]}}'"
                )

                shutdown_triggered[game] = True

            elif idle <= IDLE_LIMIT:
                shutdown_triggered[game] = False

        state["vm_games"][game] = {
            "players": players,
            "idle": idle,
            "status": "active" if players > 0 else "idle"
        }

    # =======================
    # VM IDLE
    # =======================

    vm_running = is_vm_up()

    if not vm_running:
        vm_idle_start = None
        state["vm"]["idle"] = 0

    else:
        if any(state["vm_games"].get(g, {}).get("players", 0) > 0 for g in VM_GAMES):
            vm_idle_start = now
            state["vm"]["idle"] = 0
        else:
            if vm_idle_start is None:
                vm_idle_start = now

            state["vm"]["idle"] = (now - vm_idle_start).total_seconds()

    # VM shutdown
    if state["vm"]["idle"] > IDLE_LIMIT:
        send_discord("🛑 Windows VM shutting down due to inactivity")
        os.system("/usr/bin/virsh shutdown windows-gaming")
        vm_idle_start = None

    write_state()
    time.sleep(5)