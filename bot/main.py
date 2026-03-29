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

GAMES = {
    "zomboid": {
        "name": "Project Zomboid",
        "port": 16261,
        "query_ip": "192.168.0.96"
    },
    "7days2die": {
        "name": "7 Days To Die",
        "port": 26900,
        "query_ip": "192.168.0.96"
    },
    "valheim": {
        "name": "Valheim",
        "port": 2457,
        "query_ip": "192.168.0.96"
    }
}

VM_GAMES = {
    "dcs": {
        "name": "DCS World",
        "task": "StartDCS",
        "process": "DCS_server.exe",
        "check_port": 10308
    },
    "sotf": {
        "name": "Sons Of The Forest",
        "task": "StartSOTF",
        "process": "SonsOfTheForestDS.exe",
        "check_port": 27016
    }
}

VM_IDLE_LIMIT = 1800  # 30 minutes
vm_last_seen = {key: None for key in VM_GAMES}
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

    asyncio.create_task(monitor_idle())
    asyncio.create_task(monitor_vm_games())


# -----------------------------
# HELPERS
# -----------------------------

async def wait_for_vm_ready(timeout=180):

    start = datetime.datetime.utcnow()

    while (datetime.datetime.utcnow() - start).total_seconds() < timeout:

        if check_port(VM_IP, 3389):   # RDP port
            return True

        await asyncio.sleep(5)

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
    return [c.name for c in running if c.name in GAMES]

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

    if await is_vm_running():
        await interaction.followup.send(
            "⚠️ Windows VM is currently running. Stop it before starting game servers.",
            ephemeral=True
        )
        return


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

    # Host stats
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()

    host_cpu = f"{cpu}%"
    host_ram = f"{round(ram.used/(1024**3),2)}GB / {round(ram.total/(1024**3),2)}GB"

    
    # VM status
    if await is_vm_running():

        vm_games_active = False

        for key, cfg in VM_GAMES.items():
            try:
                result = subprocess.run(
                    ["nc", "-z", VM_IP, str(cfg["check_port"])],
                    capture_output=True
                )

                if result.returncode == 0:
                    vm_games_active = True
                    break

            except:
                pass

        if vm_games_active:
            vm_status = "🟢 Running (Game Active)"
        else:
            vm_status = "🟡 Running (Idle)"

    else:
        vm_status = "🔴 Stopped"

    # DCS server status
    # VM game servers

    vm_game_lines = []

    if await is_vm_running():

        process_list = await asyncio.to_thread(get_vm_process_list)

        for key, cfg in VM_GAMES.items():

            if cfg["process"].lower() in process_list.lower():
                state = "🟢 Online"
            else:
                state = "🔴 Offline"

            vm_game_lines.append(f"{cfg['name']} : {state}")

    else:

         for key, cfg in VM_GAMES.items():
             vm_game_lines.append(f"{cfg['name']} : 🔴 Offline")

    vm_games_status = "\n".join(vm_game_lines)



 
    # Docker servers
    docker_lines = []

    for key, config in GAMES.items():

        if key == "dcs":
            continue

        if is_running(key):
            state = "🟢 Running"
        else:
            state = "🔴 Stopped"

        docker_lines.append(f"{config['name']} : {state}")

    docker_status = "\n".join(docker_lines)

    active_containers = len(get_active_game_containers())

    # Build embed
    embed = discord.Embed(
        title="🖥 Server Infrastructure",
        color=0x2ecc71
    )

    embed.add_field(
        name="Host",
        value=f"CPU: **{host_cpu}**\nRAM: **{host_ram}**",
        inline=False
    )

    vm_cpu, vm_ram_used, vm_ram_total = get_vm_stats()

    vm_extra = ""

    if vm_ram_used and vm_ram_total:
        vm_extra = f"\nRAM: **{vm_ram_used}GB / {vm_ram_total}GB**"

    if vm_cpu:
        vm_extra += f"\nCPU Time: **{vm_cpu}**"

    embed.add_field(
        name="Windows VM",
        value=f"Status: **{vm_status}**{vm_extra}",
        inline=False
)

    embed.add_field(
        name="VM Game Servers",
        value=vm_games_status,
        inline=False
    )
    embed.add_field(
        name="Docker Game Servers",
        value=docker_status,
        inline=False
    )

    embed.add_field(
        name="Containers",
        value=f"Active: **{active_containers} / {MAX_RUNNING_SERVERS}**",
        inline=False
    )

    await interaction.followup.send(embed=embed)

##ACTIVE PLAYERS COMMAND##
@tree.command(name="players", description="Show current players", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(game="Game name")
@app_commands.choices(game=[
    app_commands.Choice(name="Project Zomboid", value="zomboid"),
    app_commands.Choice(name="7 Days To Die", value="7days2die"),
    app_commands.Choice(name="valheim", value="valheim"),
    app_commands.Choice(name="DCS World", value="dcs"),
    app_commands.Choice(name="Sons of the Forest", value="sotf"),
])
async def players(interaction: discord.Interaction, game: app_commands.Choice[str]):

    await interaction.response.defer()

    # 🔴 VM not running check (DCS only)
    if game.value == "dcs" and not await is_vm_running():
        await interaction.followup.send(
            "🔴 DCS server is offline (VM not running)."
        )
        return

    # VM games
    if game.value in VM_GAMES:
        config = VM_GAMES[game.value]
        query_ip = VM_IP
        port = 27016 if game.value == "sotf" else config["check_port"]
    else:
        config = GAMES[game.value]
        query_ip = config["query_ip"]
        port = config["port"]

    # 🔥 SPECIAL CASE: DCS (NO A2S)
    if game.value == "dcs":
        if check_port(VM_IP, config["check_port"]):
            await interaction.followup.send(
                f"🟢 {config['name']} is online\nPlayers: ❓ (not supported)"
            )
        else:
            await interaction.followup.send(
                f"🔴 {config['name']} is offline"
            )
        return

    # ✅ Normal A2S games
    try:
        info = await asyncio.to_thread(
            a2s.info,
            (query_ip, port),
            10.0
        )
        await interaction.followup.send(
            f"🟢 {game.name} is online\nPlayers: **{info.player_count}**"
        )

    except Exception:
        await interaction.followup.send(
            f"🔴 {game.name} is offline or not responding."
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
])
async def startvmgame(interaction: discord.Interaction, game: app_commands.Choice[str]):

    if not await require_player_or_mod_or_admin(interaction):
        return

    await interaction.response.defer()

    config = VM_GAMES[game.value]

    msg = await interaction.followup.send(f"🎮 Starting **{config['name']}**...")

    # -----------------------------
    # CHECK IF ANOTHER VM GAME IS RUNNING
    # -----------------------------

    process_list = await asyncio.to_thread(get_vm_process_list)

    for key, cfg in VM_GAMES.items():

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

        start_vm()

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
# START GAME
# -----------------------------


    await msg.edit(content=f"🎮 Launching **{config['name']}**...")
    await asyncio.sleep(20)  # give Windows a moment after boot
    await asyncio.to_thread(
        subprocess.run,
        [
            "/usr/bin/virsh",
            "qemu-agent-command",
            VM_NAME,
            f'{{"execute":"guest-exec","arguments":{{"path":"C:\\\\Windows\\\\System32\\\\schtasks.exe","arg":["/run","/tn","{config["task"]}","/I"]}}}}'
        ]
    )

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
])
async def stopvmgame(interaction: discord.Interaction, game: app_commands.Choice[str]):

    if not await require_mod_or_admin(interaction):
        return

    await interaction.response.defer()

    config = VM_GAMES[game.value]

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

async def monitor_vm_games():

    global vm_idle_start

    await client.wait_until_ready()

    while not client.is_closed():

        if not await is_vm_running():
            await asyncio.sleep(60)
            continue


        # -----------------------------
        # CHECK PLAYER ACTIVITY
        # -----------------------------


        for game_key, config in VM_GAMES.items():

            server_running = check_port(VM_IP, config["check_port"])

            if not server_running:
                vm_last_seen[game_key] = None
                continue

            if game_key == "dcs":

                # DCS has no A2S → treat as active if port is open
                players = 1 if check_port(VM_IP, config["check_port"]) else 0

            else:
                try:
                    info = await asyncio.to_thread(
                        a2s.info,
                        (VM_IP, config["check_port"]),
                        5.0
                    )
                    players = info.player_count

                except:
                    players = 0

            now = datetime.datetime.utcnow()

            if players > 0:
 
                vm_last_seen[game_key] = now

            else:

                if vm_last_seen[game_key] is None:
                   vm_last_seen[game_key] = now

                idle = (now - vm_last_seen[game_key]).total_seconds()

                if idle >= IDLE_LIMIT:

                    channel = client.get_channel(NOTIFY_CHANNEL_ID)

                    if channel:
                        await channel.send(
                            f"🛑 **{config['name']} stopped automatically**\n"
                            f"No players for 60 minutes. Absolute losers.."
                        )

                    await asyncio.to_thread(
                        subprocess.run,
                        [
                            "/usr/bin/virsh",
                            "qemu-agent-command",
                            VM_NAME,
                            f'{{"execute":"guest-exec","arguments":{{"path":"C:\\\\Windows\\\\System32\\\\taskkill.exe","arg":["/F","/IM","{config["process"]}"]}}}}'
                        ]
                    )

                    vm_last_seen[game_key] = None           


        # -----------------------------
        # VM SHUTDOWN CHECK
        # -----------------------------

        dcs_running = check_port(VM_IP, 10308)
        sotf_running = check_port(VM_IP, 27016)

        any_vm_game_running = dcs_running or sotf_running


        if any_vm_game_running:
            vm_idle_start = None

        else:

            if vm_idle_start is None:
                vm_idle_start = datetime.datetime.utcnow()

            idle = (datetime.datetime.utcnow() - vm_idle_start).total_seconds()

            if idle >= VM_IDLE_LIMIT:

                channel = client.get_channel(NOTIFY_CHANNEL_ID)

                if channel:
                    await channel.send(
                        "🛑 Windows VM shutting down (no active VM game servers)"
                    )

                stop_vm()
                vm_idle_start = None


        await asyncio.sleep(60)
       

async def wait_for_server_ready(game_key, timeout=180):
    start_time = datetime.datetime.utcnow()
    config = GAMES[game_key]

    while (datetime.datetime.utcnow() - start_time).total_seconds() < timeout:
        try:
            await asyncio.to_thread(
                a2s.info,
                (config["query_ip"], config["port"]),
                5.0
            )
            return True
        except Exception:
            await asyncio.sleep(5)

    return False


async def monitor_idle():
    await client.wait_until_ready()
    print("Idle monitor started", flush=True)

    last_seen = {key: None for key in GAMES}

    while not client.is_closed():

        for game_key, config in GAMES.items():

            try:
                container = docker_client.containers.get(game_key)

                if container.status != "running":
                    last_seen[game_key] = None
                    continue

                try:
                    info = await asyncio.to_thread(
                        a2s.info,
                        (config["query_ip"], config["port"]),
                        5.0
                    )
                    players = info.player_count

                except:
                    players = 0
                print(f"[IDLE CHECK] {config['name']} players={players}")
                now = datetime.datetime.utcnow()

                if players > 0:
                    last_seen[game_key] = now

                else:

                    if last_seen[game_key] is None:
                        last_seen[game_key] = now

                    idle_time = (now - last_seen[game_key]).total_seconds()
                    print(f"[IDLE TIMER] {config['name']} idle={idle_time}")

                    if idle_time >= IDLE_LIMIT:

                        container.stop()

                        channel = client.get_channel(NOTIFY_CHANNEL_ID)

                        if channel:
                            await channel.send(
                                f"🛑 **{config['name']} stopped automatically** 🛑\n"
                                f"No players were online for 60 minutes. Absolute losers.."
                            )

                        last_seen[game_key] = None

            except Exception as e:
                print(f"Idle monitor error for {game_key}: {e}")

        await asyncio.sleep(CHECK_INTERVAL)



# -----------------------------

client.run(TOKEN)
