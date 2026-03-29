#!/bin/bash

set -e

echo "🚀 Starting Game Server Platform Deployment..."

# -----------------------------
# Install dependencies
# -----------------------------
echo "📦 Installing dependencies..."

sudo apt update
sudo apt install -y \
    docker.io \
    docker-compose \
    libvirt-daemon-system \
    libvirt-clients \
    qemu-kvm \
    virtinst \
    bridge-utils

# -----------------------------
# Enable services
# -----------------------------
echo "🔧 Enabling services..."

sudo systemctl enable --now docker
sudo systemctl enable --now libvirtd

# -----------------------------
# Add user to groups
# -----------------------------
echo "👤 Adding user to groups..."

sudo usermod -aG docker $USER
sudo usermod -aG libvirt $USER

# -----------------------------
# Define VM (if not exists)
# -----------------------------
echo "🖥️ Setting up VM..."

if ! virsh dominfo windows-gaming &>/dev/null; then
    echo "Creating VM from XML..."
    virsh define vm/windows-gaming.xml
else
    echo "VM already exists, skipping..."
fi

# -----------------------------
# Start VM (optional)
# -----------------------------
echo "▶️ Starting VM..."

virsh start windows-gaming || true

# -----------------------------
# Setup bot
# -----------------------------
echo "🤖 Setting up bot..."

cd bot

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# -----------------------------
# Done
# -----------------------------
echo ""
echo "✅ Deployment complete!"
echo ""
echo "⚠️ Next steps:"
echo "- Ensure Windows VM is fully installed"
echo "- Install QEMU Guest Agent inside VM"
echo "- Create scheduled tasks (StartDCS / StartSOTF)"
echo "- Configure .env for Discord bot"
echo ""
