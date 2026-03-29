# Windows VM

This project uses a Windows VM (KVM/QEMU) to host game servers that are not compatible with Linux containers.

You can extend this VM to host additional Windows-only game servers as needed.

---

## Hosted Services

* DCS World Server
* Sons of the Forest

---

## Management

The VM is controlled from the host via:

* `start_winvm.sh`
* `stop_winvm.sh`

Game servers inside the VM are started via **Windows Task Scheduler**, triggered by the Discord bot.

---

## Requirements

### 1. QEMU Guest Agent (REQUIRED)

* Must be installed inside the VM
* Service must be:

  * **Running**
  * **Startup type: Automatic**

Without this, the bot cannot:

* start game servers
* stop game servers
* query processes

---

### 2. VM Configuration (CRITICAL)

The VM **must include the guest agent channel** in its libvirt XML:

```xml
<channel type='unix'>
  <source mode='bind'/>
  <target type='virtio' name='org.qemu.guest_agent.0'/>
</channel>
```

---

### 3. Scheduled Tasks (inside Windows)

#### StartDCS

* Path:
  `F:\GameServers\DCS World Server\bin\DCS_server.exe`
* Arguments:
  `--server --norender`
* Start in:
  `F:\GameServers\DCS World Server\bin`

---

#### StartSOTF

* Path:
  `F:\GameServers\SOTF\SonsOfTheForestDS.exe`

---

### 4. Networking / Ports

Ensure the following ports are open and reachable from the host:

* DCS: `10308`
* SOTF: `27016`

Firewall rules must allow inbound traffic.

---

### 5. Bot Dependency

The Discord bot depends on:

* VM name: `windows-gaming`
* QEMU guest agent access via `virsh`
* Scheduled task names matching config:

  * `StartDCS`
  * `StartSOTF`

---

## Notes

* The VM is automatically started/stopped based on player activity
* If no active servers are detected, the VM will shut down after an idle period
* All automation relies on correct guest agent + task configuration

---

## Troubleshooting

**Error: `QEMU guest agent is not configured`**

→ Ensure:

* Guest agent is installed and running
* VM XML includes the `<channel>` config
* VM has been restarted after XML changes

---
