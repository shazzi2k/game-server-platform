#Author: Aaron Schorah

import os
import discord
from discord import app_commands
import docker
import asyncio
import a2s
import datetime
import telnetlib
import psutil
import subprocess
import json
import socket

COMMAND_CHANNEL_ID = 1269287780475998334
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
PLAYER_ROLE_ID = 1475832757253837003
MOD_ROLE_ID = 1475832704074514584
ADMIN_ROLE_ID = 1475832245259337819
NOTIFY_CHANNEL_ID = 1269287780475998334
VM_NAME = "windows-gaming"
VM_IP = "192.168.0.58"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

docker_client = docker.from_env()

IDLE_LIMIT = 3600
CHECK_INTERVAL = 300
MAX_RUNNING_SERVERS = 2

ALL_GAMES = {
    "zomboid": {
        "name": "Project Zomboid",
        "type": "docker",
        "query_ip": "192.168.0.96",
        "port": 16261
    },
    "7days2die": {
        "name": "7 Days To Die",
        "type": "docker",
        "query_ip": "192.168.0.96",
        "port": 26900
    },
    "valheim": {
        "name": "Valheim",
        "type": "docker",
        "query_ip": "192.168.0.96",
        "port": 2457
    },
    "arma3": {
        "name": "ARMA 3 Exile",
        "type": "vm",
        "process": "arma3server_x64.exe",
        "port": 2303,
        "task": "StartARMA3"
    },
    "sotf": {
        "name": "Sons Of The Forest",
        "type": "vm",
        "process": "SonsOfTheForestDS.exe",
        "port": 27016,
        "task": "StartSOTF"
    },
    "dcs": {
        "name": "DCS World",
        "type": "vm",
        "process": "DCS_server.exe",
        "port": 10308,
        "no_query": True,  # important
        "task": "StartDCS"
    }
}

VM_IDLE_LIMIT = 3600  # 60 minutes
vm_last_seen = {
    key: None for key, cfg in ALL_GAMES.items() if cfg["type"] == "vm"
}
vm_idle_start = None


# -----------------------------
# GLOBAL TREE CHECK
# -----------------------------

async def enforce_permissions(interaction: discord.Interaction, require_mod=False):

    # Channel restriction
    if interaction.channel_id != COMMAND_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ Commands can only be used in the command channel.",
            ephemeral=True
        )
        return False

    user_roles = {role.id for role in interaction.user.roles}

    # If command requires mod/admin
    if require_mod:
        allowed_roles = {MOD_ROLE_ID, ADMIN_ROLE_ID}
    else:
        allowed_roles = {PLAYER_ROLE_ID, MOD_ROLE_ID, ADMIN_ROLE_ID}

    if allowed_roles.isdisjoint(user_roles):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return False

    return True

async def get_player_count(game_key, config):

    # ------------------
    # DOCKER GAMES
    # ------------------
    if config["type"] == "docker":
        try:
            info = await asyncio.to_thread(
                a2s.info,
                (config["query_ip"], config["port"]),
                5.0
            )
            return info.player_count
        except:
            return 0

    # ------------------
    # VM GAMES
    # ------------------
    if config["type"] == "vm":

        # DCS (no query support)
        if config.get("no_query"):
            return 1 if check_port(VM_IP, config["port"]) else 0

        # Try A2S
        try:
            info = await asyncio.to_thread(
                a2s.info,
                (VM_IP, config["port"]),
                5.0
            )
            return info.player_count

        except:
            # fallback to process detection
            process_list = await asyncio.to_thread(get_vm_process_list)

            if config["process"].lower() in process_list:
                return 1
            return 0

async def wait_for_dcs_ready():

    await asyncio.sleep(20)

    while True:

        try:
            result = subprocess.check_output([
                "virsh",
                "qemu-agent-command",
                VM_NAME,
                '{"execute":"guest-file-open","arguments":{"path":"C:\\\\Users\\\\Administrator\\\\Saved Games\\\\DCS.dcs_serverrelease\\\\Logs\\\\dcs.log","mode":"r"}}'
            ])

        except:
            await asyncio.sleep(10)
            continue

        try:
            with open("/tmp/dcs_log_check", "r") as f:
                logs = f.read()

                if "net server started" in logs.lower():
                    channel = client.get_channel(NOTIFY_CHANNEL_ID)

                    if channel:
                        await channel.send(
                            "✈️ **DCS Server is now ready for players!**"
                        )
                    return

        except:
            pass

        await asyncio.sleep(10)


# -----------------------------
# READY EVENT
# -----------------------------

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    guild = discord.Object(id=GUILD_ID)

    for i in range(5):
        try:
            synced = await tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands.")
            break
        except Exception as e:
            print(f"Command sync failed (attempt {i+1}):", e)
            await asyncio.sleep(10)

    print("Starting monitors...")

    asyncio.create_task(monitor_all_games())


# -----------------------------
# HELPERS
# -----------------------------

async def wait_for_vm_ready(timeout=180):

    start = datetime.datetime.utcnow()

    while (datetime.datetime.utcnow() - start).total_seconds() < timeout:

        if check_port(VM_IP, 3389):   # RDP port
            return True

        await asyncio.sleep(15)

    return False

async def is_vm_running():

    try:
        result = await asyncio.to_thread(
            subprocess.check_output,
            ["/usr/bin/virsh", "domstate", VM_NAME],
            text=True
        )

        return "running" in result.lower()

    except:
        return False



def start_vm():
    subprocess.Popen(["/usr/bin/virsh", "start", VM_NAME])

def stop_vm():
    subprocess.Popen(["/usr/bin/virsh", "shutdown", VM_NAME])

async def wait_for_vm_state(target_state, timeout=180):
    start = datetime.datetime.utcnow()

    while (datetime.datetime.utcnow() - start).total_seconds() < timeout:
        try:
            result = subprocess.check_output(
                ["/usr/bin/virsh", "domstate", VM_NAME],
                text=True
            ).lower()

            if target_state in result:
                return True
        except:
            pass

        await asyncio.sleep(5)

    return False



def get_active_game_containers():
    running = docker_client.containers.list()
    return [
        c.name for c in running
        if c.name in ALL_GAMES and ALL_GAMES[c.name]["type"] == "docker"
    ]

def is_running(container_name):
    try:
        container = docker_client.containers.get(container_name)
        return container.status == "running"
    except:
        return False

async def require_mod_or_admin(interaction):
    allowed_roles = {MOD_ROLE_ID, ADMIN_ROLE_ID}
    user_roles = {role.id for role in interaction.user.roles}

    if allowed_roles.isdisjoint(user_roles):
        await interaction.response.send_message(
            "❌ Only Game Mods or Game Admins can stop servers.",
            ephemeral=True
        )
        return False
    return True

async def require_player_or_mod_or_admin(interaction):

    allowed_roles = {PLAYER_ROLE_ID, MOD_ROLE_ID, ADMIN_ROLE_ID}
    user_roles = {role.id for role in interaction.user.roles}

    if allowed_roles.isdisjoint(user_roles):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return False

    return True

def get_vm_stats():
    try:
        result = subprocess.check_output(
            ["/usr/bin/virsh", "domstats", VM_NAME],
            text=True
        )

        cpu_time = None
        mem_used = None
        mem_total = None

        for line in result.splitlines():
            if "cpu.time=" in line:
                cpu_time = int(line.split("=")[1])
            if "balloon.current=" in line:
                mem_used = int(line.split("=")[1])
            if "balloon.maximum=" in line:
                mem_total = int(line.split("=")[1])

        if mem_used and mem_total:
            ram_used_gb = round(mem_used / 1024 / 1024, 2)
            ram_total_gb = round(mem_total / 1024 / 1024, 2)
        else:
            ram_used_gb = ram_total_gb = None

        return cpu_time, ram_used_gb, ram_total_gb

    except:
        return None, None, None




def get_vm_process_list():

    try:
        result = subprocess.check_output([
            "/usr/bin/virsh",
            "qemu-agent-command",
            VM_NAME,
            '{"execute":"guest-exec","arguments":{"path":"C:\\\\Windows\\\\System32\\\\tasklist.exe","capture-output":true}}'
        ], text=True)

        pid = json.loads(result)["return"]["pid"]

        import time

        # 🔥 wait longer + poll properly
        for _ in range(10):
            time.sleep(1)

            status = subprocess.check_output([
                "/usr/bin/virsh",
                "qemu-agent-command",
                VM_NAME,
                f'{{"execute":"guest-exec-status","arguments":{{"pid":{pid}}}}}'
            ], text=True)

            data = json.loads(status)

            if data["return"].get("exited"):

                if data["return"].get("out-data"):
                    import base64
                    output = base64.b64decode(data["return"]["out-data"]).decode()
                    return output.lower()

                return ""

        print("VM process check timeout")

    except Exception as e:
        print("VM process check failed:", e)

    return ""

   
def check_port(ip, port, timeout=2):
    import socket
    try:
        with socket.create_connection((ip, port), timeout):
            return True
    except:
        return False

# -----------------------------
# COMMANDS
# -----------------------------


##START CONTAINER COMMAND##
@tree.command(name="start", description="Start a game server", guild=discord.Object(id=GUILD_ID))
@app_commands.choices(game=[
    app_commands.Choice(name="Project Zomboid", value="zomboid"),
    app_commands.Choice(name="7 Days To Die", value="7days2die"),
    app_commands.Choice(name="valheim", value="valheim"),
])
async def start(interaction: discord.Interaction, game: app_commands.Choice[str]):

    await interaction.response.defer(ephemeral=True)

    #temp disabled while i try a new system for tracking idle VM games
    #if await is_vm_running():
    #    await interaction.followup.send(
     #       "⚠️ Windows VM is currently running. Stop it before starting game servers.",
     #       ephemeral=True
      #  )
      #  return


    if len(get_active_game_containers()) >= MAX_RUNNING_SERVERS:
        await interaction.followup.send(
            "⚠️ Maximum active servers reached (2). Stop another server first.",
            ephemeral=True
        )
        return

    if is_running(game.value):
        await interaction.followup.send(f"{game.name} is already running.")
        return

    container = docker_client.containers.get(game.value)
    container.start()
    await interaction.followup.send(f"Starting {game.name}...")

    ready = await wait_for_server_ready(game.value)

    if ready:
        channel = client.get_channel(NOTIFY_CHANNEL_ID)
        if channel:
            await channel.send(f"🟢 **{game.name} is now online and ready.** 🟢")

##STOP CONTAINER COMMAND##
@tree.command(name="stop", description="Stop a game server", guild=discord.Object(id=GUILD_ID))
@app_commands.choices(game=[
    app_commands.Choice(name="Project Zomboid", value="zomboid"),
    app_commands.Choice(name="7 Days To Die", value="7days2die"),
    app_commands.Choice(name="valheim", value="valheim"),
])
async def stop(interaction: discord.Interaction, game: app_commands.Choice[str]):

    if not await require_mod_or_admin(interaction):
        return

    await interaction.response.defer(ephemeral=True)

    container = docker_client.containers.get(game.value)
    
    container.reload()
    if container.status != "running":
        await interaction.followup.send(f"{game.name} is already stopped.", ephemeral=True)
        return

    # stop container safely (non-blocking)
    await asyncio.to_thread(container.stop, timeout=10)

    # force kill if still running (7DTD fix)
    container.reload()
    if container.status == "running":
        await asyncio.to_thread(container.kill)

    # send messages AFTER stop completes
    channel = client.get_channel(NOTIFY_CHANNEL_ID)
    if channel:
        await channel.send(f"🛑 **{game.name} has been stopped by an admin.** 🛑")

    await interaction.followup.send(f"{game.name} stopped successfully.", ephemeral=True)


##STATUS COMMAND##
@tree.command(name="status", description="Show server infrastructure status", guild=discord.Object(id=GUILD_ID))
async def status(interaction: discord.Interaction):

    if not await require_player_or_mod_or_admin(interaction):
        return

    await interaction.response.defer()

    # -----------------------
    # LOAD JSON STATE
    # -----------------------
    try:
        with open("/srv/data/stacks/game-server-platform/server_state.json") as f:
            data = json.load(f)
    except:
        data = {}

    # -----------------------
    # HOST STATS
    # -----------------------
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()

    host_cpu = f"{cpu}%"
    host_ram = f"{round(ram.used/(1024**3),2)}GB / {round(ram.total/(1024**3),2)}GB"

    # -----------------------
# VM STATUS
# -----------------------
    vm_is_running = await is_vm_running()

    if vm_is_running:
        vm_status = "🟢 Running"
        process_list = await asyncio.to_thread(get_vm_process_list)
    else:
        vm_status = "🔴 Stopped"
        process_list = ""

    # -----------------------
    # VM GAMES (REAL CHECK)
    # -----------------------
    vm_lines = []

    for key, config in ALL_GAMES.items():
        if config["type"] != "vm":
            continue

        # VM itself is off → everything offline
        if not vm_is_running:
            vm_lines.append(f"{config['name']} : 🔴 (0 players)")
            continue

        # 🔥 CRITICAL: check if THIS game process is running
        is_running_vm_game = config["process"].lower() in process_list

        if not is_running_vm_game:
            vm_lines.append(f"{config['name']} : 🔴 (0 players)")
            continue

        # Game is running → now check players
        players = await get_player_count(key, config)

        if players > 0:
            icon = "🟢"
        else:
            icon = "🟡"

        vm_lines.append(f"{config['name']} : {icon} ({players} players)")

    vm_status_text = "\n".join(vm_lines) or "No data"

    # -----------------------
    # DOCKER GAMES
    # -----------------------
    docker_lines = []

    for key, config in ALL_GAMES.items():
        if config["type"] != "docker":
            continue

        players = await get_player_count(key, config)

        if players > 0:
            icon = "🟢"
        else:
            icon = "🔴"

        docker_lines.append(f"{config['name']} : {icon} ({players} players)")

    docker_status_text = "\n".join(docker_lines) or "No data"

    # -----------------------
    # CONTAINERS
    # -----------------------
    active_containers = len(get_active_game_containers())

    # -----------------------
    # EMBED
    # -----------------------
    embed = discord.Embed(
        title="🖥 Server Infrastructure",
        color=0x2ecc71
    )

    embed.add_field(
        name="Host",
        value=f"CPU: **{host_cpu}**\nRAM: **{host_ram}**",
        inline=False
    )

    embed.add_field(
        name="Windows VM",
        value=f"Status: **{vm_status}**",
        inline=False
    )

    embed.add_field(
        name="VM Game Servers",
        value=vm_status_text,
        inline=False
    )

    embed.add_field(
        name="Docker Game Servers",
        value=docker_status_text,
        inline=False
    )

    embed.add_field(
        name="Containers",
        value=f"Active: **{active_containers} / {MAX_RUNNING_SERVERS}**",
        inline=False
    )

    await interaction.followup.send(embed=embed)

## ACTIVE PLAYERS COMMAND ##
@tree.command(name="players", description="Show current players", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(game="Game name")
@app_commands.choices(game=[
    app_commands.Choice(name="Project Zomboid", value="zomboid"),
    app_commands.Choice(name="7 Days To Die", value="7days2die"),
    app_commands.Choice(name="valheim", value="valheim"),
    app_commands.Choice(name="DCS World", value="dcs"),
    app_commands.Choice(name="Sons of the Forest", value="sotf"),
    app_commands.Choice(name="ARMA 3 Exile", value="arma3"),
])
async def players(interaction: discord.Interaction, game: app_commands.Choice[str]):

    await interaction.response.defer()

    config = ALL_GAMES[game.value]

    # VM not running check
    if config["type"] == "vm" and not await is_vm_running():
        await interaction.followup.send(
            f"🔴 {config['name']} is offline (VM not running)."
        )
        return

    players = await get_player_count(game.value, config)

    if players > 0:
        await interaction.followup.send(
            f"🟢 {config['name']} is online\nPlayers: **{players}**"
        )
    else:
        await interaction.followup.send(
            f"🟡 {config['name']} is running\nPlayers: 0"
        )

##STOP WINVM COMMAND##
@tree.command(name="stopvm", description="Stop Windows VM", guild=discord.Object(id=GUILD_ID))
async def stopvm(interaction: discord.Interaction):

    if not await require_mod_or_admin(interaction):
        return

    await interaction.response.defer()

    if not await is_vm_running():
        await interaction.followup.send("Windows VM is already stopped.")
        return

    msg = await interaction.followup.send("🛑 Shutting down Windows VM...")

    stop_vm()

    stopped = await wait_for_vm_state("shut off")

    if stopped:
        await msg.edit(content="🔴 Windows VM is now OFFLINE.")
    else:
        await msg.edit(content="⚠️ VM shutdown timeout. Check the host.")

##START A WINVM GAME##
@tree.command(name="startvmgame", description="Start a VM hosted game", guild=discord.Object(id=GUILD_ID))
@app_commands.choices(game=[
    app_commands.Choice(name="DCS World", value="dcs"),
    app_commands.Choice(name="Sons of the Forest", value="sotf"),
    app_commands.Choice(name="ARMA 3 Exile", value="arma3"),
])
async def startvmgame(interaction: discord.Interaction, game: app_commands.Choice[str]):

    if not await require_player_or_mod_or_admin(interaction):
        return

    await interaction.response.defer()

    config = ALL_GAMES[game.value]

    msg = await interaction.followup.send(f"🎮 Starting **{config['name']}**...")

    # -----------------------------
    # CHECK IF ANOTHER VM GAME IS RUNNING
    # -----------------------------

    process_list = await asyncio.to_thread(get_vm_process_list)

    for key, cfg in ALL_GAMES.items():
        if cfg["type"] != "vm":
         continue

        if cfg["process"].lower() in process_list:

            await msg.edit(
                content=f"⚠️ **{cfg['name']}** is already running. Stop it first."
            )
            return


 # -----------------------------
# START VM IF NEEDED
# -----------------------------

    if not await is_vm_running():

        await msg.edit(content="🖥 Starting Windows VM...")

        await asyncio.to_thread(start_vm)

        ready = await wait_for_vm_state("running")

        if not ready:
            await msg.edit(content="⚠️ VM failed to start.")
            return

        await msg.edit(content="⏳ Waiting for Windows services...")

        vm_ready = await wait_for_vm_ready()

        if not vm_ready:
            await msg.edit(content="⚠️ Windows did not become ready.")
            return


    # -----------------------------
    # NOW CHECK IF A VM GAME IS RUNNING
    # -----------------------------

    process_list = await asyncio.to_thread(get_vm_process_list)

    for key, cfg in ALL_GAMES.items():

        if cfg["type"] != "vm":
            continue

        if cfg["process"].lower() in process_list:
            await msg.edit(
                content=f"⚠️ **{cfg['name']}** is already running. Stop it first."
            )
            return

# -----------------------------
# START GAME
# -----------------------------


    await msg.edit(content=f"🎮 Launching **{config['name']}**...")
    await asyncio.sleep(20)  # give Windows a moment after boot
    result = await asyncio.to_thread(
        subprocess.check_output,
        [
            "/usr/bin/virsh",
            "qemu-agent-command",
            VM_NAME,
            f'{{"execute":"guest-exec","arguments":{{"path":"C:\\\\Windows\\\\System32\\\\schtasks.exe","arg":["/run","/tn","{config["task"]}","/I"],"capture-output":true}}}}'
        ],
        text=True
    )

    print("QEMU EXEC RESULT:", result)

    # 👇 NOW ALSO CHECK EXEC STATUS (THIS IS CRITICAL)
    pid = json.loads(result)["return"]["pid"]

    import time
    for _ in range(10):
        await asyncio.sleep(1)

        status = await asyncio.to_thread(
            subprocess.check_output,
            [
                "/usr/bin/virsh",
                "qemu-agent-command",
                VM_NAME,
                f'{{"execute":"guest-exec-status","arguments":{{"pid":{pid}}}}}'
            ],
            text=True
        )

        data = json.loads(status)

        if data["return"].get("exited"):
            if data["return"].get("out-data"):
                import base64
                output = base64.b64decode(data["return"]["out-data"]).decode()
                print("SCHTASKS OUTPUT:", output)

            if data["return"].get("err-data"):
                import base64
                err = base64.b64decode(data["return"]["err-data"]).decode()
                print("SCHTASKS ERROR:", err)

            break

    # wait for game server to respond
    await msg.edit(content="⏳ Waiting for game server to start...")

    ready = True
    for _ in range(90):

        try:
            info = await asyncio.to_thread(
                a2s.info,
                (VM_IP, config["check_port"]),
                5.0
            )

            await msg.edit(
                content=f"🟢 **{config['name']} server is now online!**\nPlayers: **{info.player_count}**"
            )

            break

        except:
            await asyncio.sleep(5)

    else:
        await msg.edit(content="⚠️ Game server did not respond in time.")


##STOP WINVM GAME COMMAND##
@tree.command(name="stopvmgame", description="Stop a VM hosted game", guild=discord.Object(id=GUILD_ID))
@app_commands.choices(game=[
    app_commands.Choice(name="DCS World", value="dcs"),
    app_commands.Choice(name="Sons Of The Forest", value="sotf"),
    app_commands.Choice(name="ARMA 3 Exile", value="arma3"),
])
async def stopvmgame(interaction: discord.Interaction, game: app_commands.Choice[str]):

    if not await require_mod_or_admin(interaction):
        return

    await interaction.response.defer()

    config = ALL_GAMES[game.value]

    msg = await interaction.followup.send(f"🛑 Stopping **{config['name']}**...")

    await asyncio.to_thread(
        subprocess.run,
        [
            "/usr/bin/virsh",
            "qemu-agent-command",
            VM_NAME,
            f'{{"execute":"guest-exec","arguments":{{"path":"C:\\\\Windows\\\\System32\\\\taskkill.exe","arg":["/F","/IM","{config["process"]}"]}}}}'
        ]
    )

    await msg.edit(content=f"🛑 **{config['name']} stopped.**")


##SERVERSTATS COMMAND (obsolete)##
@tree.command(
    name="serverstats",
    description="Show host CPU and RAM usage",
    guild=discord.Object(id=GUILD_ID)
)
async def serverstats(interaction: discord.Interaction):

    # Restrict to Mod/Admin only
    allowed_roles = {MOD_ROLE_ID, ADMIN_ROLE_ID}
    user_roles = {role.id for role in interaction.user.roles}

    if allowed_roles.isdisjoint(user_roles):
        await interaction.response.send_message(
            "❌ Only Game Mods or Game Admins can view host stats.",
            ephemeral=True
        )
        return

    import psutil

    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    uptime_seconds = int(datetime.datetime.now().timestamp() - psutil.boot_time())
    uptime_str = str(datetime.timedelta(seconds=uptime_seconds))

    await interaction.response.send_message(
        f"🖥 **Host Server Stats**\n"
        f"CPU Usage: **{cpu}%**\n"
        f"RAM Usage: **{ram.percent}%** "
        f"({round(ram.used/(1024**3),2)}GB / {round(ram.total/(1024**3),2)}GB)\n"
        f"Uptime: **{uptime_str}**"
    )

##TIDY CHANNEL MESSAGES##
@tree.command(name="clearcommands", description="Clear bot messages from command channel", guild=discord.Object(id=GUILD_ID))
async def clearcommands(interaction: discord.Interaction):

    if not await require_mod_or_admin(interaction):
        return

    await interaction.response.defer(ephemeral=True)

    channel = interaction.channel
    deleted = 0

    async for message in channel.history(limit=200):

        # delete messages from ANY bot
        if message.author.bot:
            try:
                await message.delete()
                deleted += 1
            except:
                pass

    await interaction.followup.send(
        f"🧹 Deleted **{deleted} bot messages** from the command channel.",
        ephemeral=True
    )

##START WINVM COMMAND##
@tree.command(
    name="startvm",
    description="Start the game VM",
    guild=discord.Object(id=GUILD_ID)
)
async def startvm(interaction: discord.Interaction):

    await interaction.response.defer()

    if await is_vm_running():
        await interaction.followup.send("🟢 VM is already running.")
        return

    await interaction.followup.send("🚀 Starting VM...")

    await asyncio.to_thread(start_vm)

    await interaction.followup.send("🟢 VM start command sent.")



# -----------------------------
# IDLE MONITOR
# -----------------------------

async def monitor_all_games():

    await client.wait_until_ready()

    last_seen = {key: None for key in ALL_GAMES}
    vm_idle_start = None

    while not client.is_closed():

        any_vm_active = False

        # ------------------
        # GET VM PROCESS LIST ONCE
        # ------------------
        process_list = ""
        if await is_vm_running():
            process_list = await asyncio.to_thread(get_vm_process_list)

        # ------------------
        # MAIN LOOP
        # ------------------
        for key, config in ALL_GAMES.items():

            now = datetime.datetime.utcnow()

            # ------------------
            # CHECK IF GAME IS RUNNING
            # ------------------
            is_active = False

            if config["type"] == "docker":
                is_active = is_running(key)

            elif config["type"] == "vm":
                is_active = config["process"].lower() in process_list

            # ------------------
            # SKIP IF NOT RUNNING
            # ------------------
            if not is_active:
                last_seen[key] = None
                continue

            # ------------------
            # GET PLAYER COUNT
            # ------------------
            players = await get_player_count(key, config)

            # ------------------
            # ACTIVE PLAYERS
            # ------------------
            if players > 0:
                last_seen[key] = now

                if config["type"] == "vm":
                    any_vm_active = True

            # ------------------
            # IDLE LOGIC
            # ------------------
            else:

                if last_seen[key] is None:
                    last_seen[key] = now

                idle = (now - last_seen[key]).total_seconds()

                if idle >= IDLE_LIMIT:

                    print(f"[AUTO STOP] {config['name']} idle for {idle}s")

                    # STOP DOCKER
                    if config["type"] == "docker":
                        try:
                            container = docker_client.containers.get(key)
                            await asyncio.to_thread(container.stop, timeout=60)
                        except Exception as e:
                            print(f"Failed to stop container {key}: {e}")

                    # STOP VM GAME
                    elif config["type"] == "vm":
                        await asyncio.to_thread(
                            subprocess.run,
                            [
                                "/usr/bin/virsh",
                                "qemu-agent-command",
                                VM_NAME,
                                f'{{"execute":"guest-exec","arguments":{{"path":"C:\\\\Windows\\\\System32\\\\taskkill.exe","arg":["/F","/IM","{config["process"]}"]}}}}'
                            ]
                        )

                    # DISCORD MESSAGE (FIXED)
                    try:
                        channel = await client.fetch_channel(NOTIFY_CHANNEL_ID)
                        await channel.send(
                            f"🛑 **{config['name']} stopped automatically (idle 60 minutes)**"
                        )
                    except Exception as e:
                        print(f"Discord send failed: {e}")

                    last_seen[key] = None

        # ------------------
        # VM SHUTDOWN (OUTSIDE LOOP)
        # ------------------
        if await is_vm_running():

            if any_vm_active:
                vm_idle_start = None
            else:
                if vm_idle_start is None:
                    vm_idle_start = datetime.datetime.utcnow()

                idle = (datetime.datetime.utcnow() - vm_idle_start).total_seconds()

                if idle >= IDLE_LIMIT:

                    try:
                        channel = await client.fetch_channel(NOTIFY_CHANNEL_ID)
                        await channel.send(
                            "🛑 Windows VM shutting down (no active games 60 minutes)...losers"
                        )
                    except Exception as e:
                        print(f"Discord send failed: {e}")

                    stop_vm()
                    vm_idle_start = None

        await asyncio.sleep(60)


       

async def wait_for_server_ready(game_key, timeout=180):
    start_time = datetime.datetime.utcnow()
    config = ALL_GAMES[game_key]

    while (datetime.datetime.utcnow() - start_time).total_seconds() < timeout:
        try:
            if config["type"] == "docker":
                await asyncio.to_thread(
                    a2s.info,
                    (config["query_ip"], config["port"]),
                    5.0
                )
            else:
                await asyncio.to_thread(
                    a2s.info,
                    (VM_IP, config["port"]),
                    5.0
                )
            return True
        except:
            await asyncio.sleep(5)

    return False






# -----------------------------

client.run(TOKEN)