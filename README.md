# 🚀 Self-Hosted Game Server Platform

A fully automated, self-hosted multiplayer game server platform built using Docker, virtualisation, and Discord integration.

---

## 🎯 Overview

This project provides a centralised system for hosting and managing multiple game servers on demand.

Users can start and stop servers directly from Discord, while the system automatically shuts down idle servers to conserve resources.

---

## ⚡ Quick Start

```bash
git clone https://github.com/shazzi2k/game-server-platform.git
cd game-server-platform
docker compose up -d

---



## 🏗️ Architecture

- **Docker Containers**
  - Project Zomboid
  - Valheim
  - 7 Days to Die

- **Windows VM (KVM/QEMU)**
  - DCS World Server
  - Sons of the Forest

- **Discord Bot (Python)**
  - Server start/stop commands
  - Player monitoring
  - Idle shutdown automation
  - Status reporting

---

## ⚙️ Features

### 🎮 Multi-Game Support
- Multiple dedicated game servers running in containers and VM

### 🤖 Discord Automation
- Start/stop servers via commands
- Real-time player monitoring
- Automated notifications

### ⏱️ Smart Resource Management
- Auto shutdown when servers are empty
- Reduces unnecessary CPU/RAM usage

### 🌐 Networking
- Domain + port forwarding
- LAN + public access
- Secure remote access

### 💾 Persistent Storage
- Game data stored on host filesystem
- Survives restarts and updates

### 🔄 Automated Updates
- SteamCMD integration for server updates

### 📊 Monitoring & Observability
- Prometheus for metrics collection
- Grafana dashboards for real-time insights
- Track CPU, RAM, server uptime, and player activity

---

## 📁 Project Structure
game-server-platform/
├── bot/                # Discord bot
├── vm/                 # VM config + README
├── docker/             # (current game containers 👇)
│   ├── 7days2die/
│   ├── valheim/
│   └── zomboid/
├── scripts/            # host scripts
├── automation/         # Crontab
├── images/             # diagrams/screenshots
├── docs/               # rebuild
└── README.md

---

## 🧠 Key Concepts

- Containerisation (Docker)
- Virtualisation (KVM/QEMU)
- Automation (Discord bot + scripts)
- Networking (ports, routing, remote access)
- Infrastructure as Code
---

## 🧾 Requirements

- Linux host (Ubuntu recommended)
- Docker + Docker Compose
- KVM/QEMU with libvirt
- Windows VM (for DCS/SOTF)
- Discord bot token



---

## ⚠️ Notes

- Game files are not included (SteamCMD required)
- VM images are not included
- Secrets and environment variables are excluded

---

## 📌 Summary

This project demonstrates a fully automated, self-hosted game infrastructure capable of dynamically managing multiple multiplayer servers with minimal manual intervention.


## 🖼️ Screenshots

### ⚙️ Architecture-Diagram
![Commands](images/architecture-diagram.png)

### 🎮 Discord Bot Commands
![Commands](images/start-command-example.png)

### ▶️ Starting aDocker game container
![Start Command](images/starting-docker-container.png)

### ⚙️ Server Startup
![Starting Server](images/start-vmserver-example.png)

### 🟢 Server Status
![Server Online](images/server-status-example.png)

