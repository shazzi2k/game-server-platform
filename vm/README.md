# Windows VM

This project uses a Windows VM (KVM/QEMU) to host game servers that are not compatible with Linux containers.

## Hosted Services
- DCS World Server
- Sons of the Forest

## Management
Controlled via shell scripts:
- start_winvm.sh
- stop_winvm.sh

The VM is integrated into the automation system and can be started/stopped based on demand.
