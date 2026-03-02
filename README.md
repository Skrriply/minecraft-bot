# ⛏️ Minecraft Discord Bot

A Discord bot built with [Python](https://www.python.org/) and [disnake](https://disnake.dev/) that helps you to protect your self-hosted Minecraft server from data corruption caused by sudden power losses and adds several useful features.

## ✨ Features

- ⚡ **Automated power management.** Continually scrapes and monitors DTEK power outage schedules in the background.
- 🛑 **Graceful shutdown.** Safely stops the Minecraft server and initiates a shutdown command to the Proxmox host 10 minutes before the outage.
- 🎮 **Pterodactyl integration.** Start, stop, restart, kill, and send remote console commands to your Minecraft server directly from Discord.
- 📊 **Server status.** Real-time CPU, RAM, disk usage, server state, and upcoming DTEK power schedules.

## ⚙️ Prerequisites

1. Proxmox VE host with API access enabled.
   - Ensure your server's motherboard BIOS has **"Restore on AC Power Loss"** (or similar) set to **"Power On"** so the host boots automatically when power restores.
2. Pterodactyl Panel with a generated Client API key.
3. Discord bot application with the necessary intents.

## 🚀 Installation & Setup

### 1. Clone the repository:

```bash
git clone https://github.com/Skrriply/minecraft-bot.git
cd minecraft-bot
```

### 2. Install dependencies:

It's recommended to use [uv](https://docs.astral.sh/uv/).

```bash
python -m pip install uv
uv sync
```

### 3. Configure Environment Variables:

Create a copy of the `.env.example` file in the root directory and rename it to `.env`, then fill in your credentials.

### 4. Run the Bot:

```bash
python -m uv run ./src/bot/main.py
```

## 📜 Discord Slash Commands

| Command       | Description                                                       | Permissions              |
| ------------- | ----------------------------------------------------------------- | ------------------------ |
| /start        | 🚀 Sends a start signal to the Minecraft server.                  | Everyone (with cooldown) |
| /status       | 📊 Displays current Minecraft server resources and DTEK schedule. | Everyone                 |
| /power        | 🔌 Sends a power action (start, stop, restart, kill).             | Bot owner only           |
| /power        | 🛠️ Sends a command directly to the Minecraft console.             | Bot owner only           |

## ⚖️ License

Distributed under the [GPL-3.0 License](https://github.com/Skrriply/minecraft-bot/blob/main/LICENSE).
