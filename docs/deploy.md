# 🚀 Deployment Guide

This document explains how to deploy the Game Server Platform on a fresh host.

---

## ⚡ Quick Deploy

Run:

```bash
./scripts/deploy.sh
```

This will:

* Install required packages (Docker, libvirt, QEMU)
* Enable required services
* Configure user permissions
* Define the Windows VM (if not already present)
* Set up the Discord bot environment

---

## 📦 What the Script Does

### 🖥️ System Setup

* Installs:

  * Docker
  * libvirt / QEMU
  * virtualization tools

### 🖥️ VM Setup

* Defines the VM using:

  * `vm/windows-gaming.xml`
* Starts the VM (if possible)

### 🤖 Bot Setup

* Creates Python virtual environment
* Installs dependencies from `requirements.txt`

---

## ⚠️ Manual Steps Required

The following steps **must be completed manually**:

---

### 1. Install Windows in the VM

* Attach Windows ISO
* Complete installation inside the VM

---

### 2. Install QEMU Guest Agent (CRITICAL)

Inside the VM:

* Install guest agent from VirtIO ISO
* Set service:

  * Startup: **Automatic**
  * Status: **Running**

Verify from host:

```bash
virsh qemu-agent-command windows-gaming '{"execute":"guest-ping"}'
```

---

### 3. Create Scheduled Tasks

Inside Windows Task Scheduler:

#### StartDCS

* Runs DCS server

#### StartSOTF

* Runs Sons of the Forest server

⚠️ These must match exactly:

* Task names
* Executables
* Arguments

(See `/vm/README.md` for full configuration)

---

### 4. Configure Bot Environment

Create `.env` inside `/bot/`:

```env
DISCORD_TOKEN=your_token_here
GUILD_ID=your_guild_id
```

---

### 5. Start the Bot

```bash
cd bot
source venv/bin/activate
python3 main.py
```

---

## ⚠️ VM XML Notes (UUID & MAC Address)

The provided VM XML (`vm/windows-gaming.xml`) contains:

* A **UUID**
* A **MAC address**

These must be **unique per host**.

---

### ❗ Potential Issues

If reused without changes:

* Network conflicts (duplicate MAC)
* Incorrect IP assignment
* VM definition errors
* Bot failing to communicate with VM

---

### ✅ Recommended Approach

Before defining the VM, edit:

```xml
<uuid>...</uuid>
<mac address="..."/>
```

---

### 🔧 Generate New Values

**UUID:**

```bash
uuidgen
```

**MAC address (example format):**

```bash
52:54:00:xx:xx:xx
```

Example:

```
52:54:00:ab:cd:ef
```

---

### 💡 Alternative (Advanced)

You can remove the `<uuid>` line entirely and let libvirt generate one automatically.

---

## 🧪 Verification

After deployment, check:

### VM Status

```bash
virsh list --all
```

### Guest Agent

```bash
virsh qemu-agent-command windows-gaming '{"execute":"guest-ping"}'
```

### Bot

* Responds in Discord
* Can start/stop servers

---

## 🏁 Summary

The deploy script prepares:

* Host system
* VM definition
* Bot environment

You must still manually configure:

* Windows installation
* Guest agent
* Scheduled tasks
* Bot `.env`

Once completed, the system becomes fully automated via Discord.
